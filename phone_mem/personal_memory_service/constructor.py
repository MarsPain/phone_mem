from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    EventSource,
    EventType,
    Lifecycle,
    Lineage,
    MemoryEvent,
    MemoryEventValidationError,
    MemoryLayer,
    Modality,
    Privacy,
    PrivacyLevel,
    ProcessingPolicy,
    Quality,
    ValidTime,
)


@dataclass(frozen=True)
class MemoryCandidate:
    semantic_description: str
    source_app: str
    actor: Actor
    modality: list[Modality]
    attribution: Attribution
    event_type: EventType | None = None
    memory_layer: MemoryLayer | None = None
    entities: list[str] = field(default_factory=list)
    relations: list[dict[str, object]] = field(default_factory=list)
    privacy_level: PrivacyLevel | None = None
    allowed_scopes: list[str] = field(default_factory=list)
    confidence: float = 0.9
    importance: float = 0.5
    freshness_half_life_days: int = 30
    valid_at: datetime | None = None
    lineage: Lineage = field(default_factory=Lineage)
    capture_triggers: list[str] = field(default_factory=list)
    review_policy: str | None = None


class MemoryConstructor:
    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def construct(self, candidate: MemoryCandidate) -> MemoryEvent:
        description = candidate.semantic_description.strip()
        if not description:
            raise MemoryEventValidationError("semantic_description is required")
        if not candidate.source_app.strip():
            raise MemoryEventValidationError("source_app is required")

        created_at = self._clock()
        valid_at = candidate.valid_at or created_at
        privacy_level = candidate.privacy_level or self._default_privacy_level(candidate)

        return MemoryEvent(
            event_id=self._id_factory(),
            created_at=created_at,
            valid_time=ValidTime(start=valid_at),
            event_type=candidate.event_type or self._default_event_type(candidate),
            memory_layer=self._memory_layer(candidate),
            semantic_description=description,
            entities=self._normalize_strings(candidate.entities),
            relations=self._relations(candidate),
            source=EventSource(
                app=candidate.source_app.strip(),
                actor=candidate.actor,
                modality=list(candidate.modality),
                attribution=candidate.attribution,
            ),
            privacy=Privacy(
                level=privacy_level,
                allowed_scopes=self._allowed_scopes(candidate, privacy_level),
                processing_policy=self._default_processing_policy(privacy_level),
            ),
            quality=Quality(
                confidence=candidate.confidence,
                importance=candidate.importance,
                freshness_half_life_days=candidate.freshness_half_life_days,
            ),
            lineage=candidate.lineage,
            lifecycle=Lifecycle(),
        )

    def _default_event_type(self, candidate: MemoryCandidate) -> EventType:
        if Modality.APP_EVENT in candidate.modality:
            return EventType.APP_ACTION
        return EventType.USER_UTTERANCE

    def _default_memory_layer(self, candidate: MemoryCandidate) -> MemoryLayer:
        if candidate.attribution == Attribution.DERIVED:
            return MemoryLayer.SEMANTIC
        return MemoryLayer.EPISODIC

    def _memory_layer(self, candidate: MemoryCandidate) -> MemoryLayer:
        requested = candidate.memory_layer or self._default_memory_layer(candidate)
        if not candidate.capture_triggers:
            return requested
        if requested not in {MemoryLayer.SEMANTIC, MemoryLayer.PROCEDURAL}:
            return requested
        if candidate.review_policy and candidate.confidence >= 0.9:
            return requested
        return MemoryLayer.EPISODIC

    def _default_privacy_level(self, candidate: MemoryCandidate) -> PrivacyLevel:
        if candidate.attribution == Attribution.APP_SYNCED:
            return PrivacyLevel.PERSONAL
        return PrivacyLevel.PERSONAL

    def _default_processing_policy(self, privacy_level: PrivacyLevel) -> ProcessingPolicy:
        if privacy_level == PrivacyLevel.SENSITIVE:
            return ProcessingPolicy.DEVICE_ONLY
        if privacy_level == PrivacyLevel.PUBLIC:
            return ProcessingPolicy.CLOUD_INDEXABLE
        return ProcessingPolicy.CLIENT_ENCRYPTED_SYNC

    def _allowed_scopes(self, candidate: MemoryCandidate, privacy_level: PrivacyLevel) -> list[str]:
        scopes = self._normalize_strings(candidate.allowed_scopes)
        if scopes:
            return scopes
        if privacy_level == PrivacyLevel.SENSITIVE:
            return [candidate.source_app.strip()]
        return [candidate.source_app.strip()]

    def _normalize_strings(self, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            stripped = value.strip()
            if stripped and stripped not in normalized:
                normalized.append(stripped)
        return normalized

    def _relations(self, candidate: MemoryCandidate) -> list[dict[str, object]]:
        relations = list(candidate.relations)
        for trigger in self._normalize_strings(candidate.capture_triggers):
            relation = {"type": "capture_trigger", "value": trigger}
            if relation not in relations:
                relations.append(relation)
        if candidate.review_policy is not None:
            review_policy = candidate.review_policy.strip()
            if review_policy:
                relation = {"type": "review_policy", "value": review_policy}
                if relation not in relations:
                    relations.append(relation)
        return relations
