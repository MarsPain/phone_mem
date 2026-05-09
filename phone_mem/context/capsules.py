from __future__ import annotations

from dataclasses import dataclass, field

from phone_mem.context.token_counter import TokenCounter
from phone_mem.personal_memory_service.retrieval import MemorySnippet


@dataclass(frozen=True)
class HotMemoryCapsule:
    category: str
    text: str
    evidence_event_ids: list[str]
    confidence: float
    attribution: str
    lifecycle_state: str = "active"
    omitted_memory: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class CapsuleBuildResult:
    capsules: list[HotMemoryCapsule]
    used_tokens: int
    budget_tokens: int
    omitted_capsules: list[dict[str, str]]


class HotMemoryCapsuleBuilder:
    def __init__(self, token_counter: TokenCounter, *, max_capsule_tokens: int = 64) -> None:
        self._token_counter = token_counter
        self._max_capsule_tokens = max_capsule_tokens

    def build(
        self,
        snippets: list[MemorySnippet],
        *,
        omitted_memory: list[dict[str, str]],
        available_memory_tokens: int,
    ) -> CapsuleBuildResult:
        budget_tokens = self._capsule_budget(available_memory_tokens)
        capsules: list[HotMemoryCapsule] = []
        omitted_capsules: list[dict[str, str]] = []
        used_tokens = 0

        for snippet in snippets:
            capsule = self._capsule_for_snippet(snippet, omitted_memory=omitted_memory)
            capsule_tokens = self._token_counter.count(f"capsule:{capsule.text}")
            if used_tokens + capsule_tokens > budget_tokens:
                omitted_capsules.append(
                    {"event_id": snippet.event_id, "reason": "capsule_budget_exhausted"}
                )
                continue
            capsules.append(capsule)
            used_tokens += capsule_tokens

        return CapsuleBuildResult(
            capsules=capsules,
            used_tokens=used_tokens,
            budget_tokens=budget_tokens,
            omitted_capsules=omitted_capsules,
        )

    def _capsule_budget(self, available_memory_tokens: int) -> int:
        return max(1, min(self._max_capsule_tokens, available_memory_tokens))

    def _capsule_for_snippet(
        self,
        snippet: MemorySnippet,
        *,
        omitted_memory: list[dict[str, str]],
    ) -> HotMemoryCapsule:
        category = self._category(snippet)
        return HotMemoryCapsule(
            category=category,
            text=self._capsule_text(category, snippet),
            evidence_event_ids=list(snippet.evidence_event_ids),
            confidence=snippet.confidence,
            attribution=snippet.attribution,
            lifecycle_state="active",
            omitted_memory=list(omitted_memory),
        )

    def _category(self, snippet: MemorySnippet) -> str:
        text = snippet.text.lower()
        if snippet.memory_layer == "procedural":
            return "procedural_candidate"
        if "decided" in text or "decision" in text:
            return "recent_decision"
        if "must" in text or "constraint" in text or "require" in text:
            return "active_constraint"
        if snippet.attribution == "user_stated" and snippet.confidence >= 0.9:
            return "stable_user_confirmed_fact"
        return "recent_memory"

    def _capsule_text(self, category: str, snippet: MemorySnippet) -> str:
        if category == "stable_user_confirmed_fact":
            return "Fact."
        if category == "recent_decision":
            return "Decision."
        if category == "procedural_candidate":
            return "Procedure."
        if category == "active_constraint":
            return "Constraint."
        return "Memory."
