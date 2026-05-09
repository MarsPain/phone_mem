from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from phone_mem.agent_runtime.tools import MemoryToolRegistry
from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.events import Actor, Attribution, MemoryLayer, Modality


@dataclass(frozen=True)
class SessionCaptureInput:
    trigger: str
    transcript_summary: str | None = None
    user_message: str | None = None
    assistant_text: str | None = None
    user_correction: str | None = None
    tool_observations: list[str] = field(default_factory=list)
    task_state: dict[str, Any] = field(default_factory=dict)
    entities: list[str] = field(default_factory=list)
    memory_layer: MemoryLayer = MemoryLayer.EPISODIC
    confidence: float = 0.72
    review_policy: str | None = None


class SessionCapture:
    def __init__(self) -> None:
        self._seen_fingerprints: set[tuple[str, tuple[str, ...]]] = set()

    def flush(self, capture_input: SessionCaptureInput, *, tools: MemoryToolRegistry) -> list[str]:
        captured_event_ids: list[str] = []
        for candidate in self.propose(capture_input, source_app=tools.source_app):
            fingerprint = self._fingerprint(candidate)
            if fingerprint in self._seen_fingerprints:
                continue
            result = tools.record_candidate(candidate)
            self._seen_fingerprints.add(fingerprint)
            captured_event_ids.append(result["event_id"])
        return captured_event_ids

    def propose(
        self,
        capture_input: SessionCaptureInput,
        *,
        source_app: str,
    ) -> list[MemoryCandidate]:
        correction = capture_input.user_correction or self._correction_from_message(
            capture_input.user_message
        )
        triggers = self._capture_triggers(capture_input.trigger, correction=correction)
        candidates: list[MemoryCandidate] = []

        if correction:
            candidates.append(
                MemoryCandidate(
                    semantic_description=self._correction_description(correction),
                    source_app=source_app,
                    actor=Actor.USER,
                    modality=[Modality.TEXT],
                    attribution=Attribution.USER_STATED,
                    entities=list(capture_input.entities),
                    memory_layer=MemoryLayer.EPISODIC,
                    confidence=max(capture_input.confidence, 0.82),
                    capture_triggers=triggers,
                    review_policy=capture_input.review_policy,
                )
            )

        summary = self._session_summary(capture_input)
        if summary:
            candidates.append(
                MemoryCandidate(
                    semantic_description=summary,
                    source_app=source_app,
                    actor=Actor.AGENT,
                    modality=[Modality.TEXT],
                    attribution=Attribution.AGENT_INFERRED,
                    entities=list(capture_input.entities),
                    memory_layer=capture_input.memory_layer,
                    confidence=capture_input.confidence,
                    capture_triggers=triggers,
                    review_policy=capture_input.review_policy,
                )
            )

        return candidates

    def _capture_triggers(self, trigger: str, *, correction: str | None) -> list[str]:
        triggers = [trigger]
        if correction is not None:
            triggers.append("user_correction")
        return self._normalize_strings(triggers)

    def _session_summary(self, capture_input: SessionCaptureInput) -> str | None:
        parts: list[str] = []
        transcript_summary = self._clean(capture_input.transcript_summary)
        if transcript_summary:
            parts.append(f"Session summary: {transcript_summary}")
        for observation in capture_input.tool_observations:
            clean_observation = self._clean(observation)
            if clean_observation:
                parts.append(f"Tool observation: {clean_observation}")
        task_state = self._task_state_text(capture_input.task_state)
        if task_state:
            parts.append(f"Task state: {task_state}")
        if not parts:
            return None
        return " ".join(parts)

    def _task_state_text(self, task_state: dict[str, Any]) -> str | None:
        items: list[str] = []
        for key, value in sorted(task_state.items()):
            clean_key = self._clean(str(key))
            clean_value = self._clean(str(value))
            if clean_key and clean_value:
                items.append(f"{clean_key}={clean_value}")
        if not items:
            return None
        return "; ".join(items)

    def _correction_from_message(self, user_message: str | None) -> str | None:
        message = self._clean(user_message)
        if message is None:
            return None
        lower = message.lower()
        for prefix in ("actually,", "correction:", "to correct,", "update:"):
            if lower.startswith(prefix):
                return message[len(prefix) :].strip()
        return None

    def _correction_description(self, correction: str) -> str:
        clean_correction = correction.strip()
        lower = clean_correction.lower()
        if lower.startswith("user "):
            return self._sentence(clean_correction)
        if lower.startswith("i prefer "):
            return self._sentence("User prefers " + clean_correction[9:])
        if lower.startswith("i like "):
            return self._sentence("User likes " + clean_correction[7:])
        return self._sentence(f"User correction: {clean_correction}")

    def _fingerprint(self, candidate: MemoryCandidate) -> tuple[str, tuple[str, ...]]:
        return (
            " ".join(candidate.semantic_description.lower().split()),
            tuple(sorted(candidate.entities)),
        )

    def _normalize_strings(self, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            stripped = value.strip()
            if stripped and stripped not in normalized:
                normalized.append(stripped)
        return normalized

    def _clean(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if not cleaned:
            return None
        return cleaned

    def _sentence(self, value: str) -> str:
        stripped = value.strip()
        if stripped.endswith((".", "!", "?")):
            return stripped
        return stripped + "."
