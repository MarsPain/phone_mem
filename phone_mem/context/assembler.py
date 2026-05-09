from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phone_mem.context.budgets import ContextBudget
from phone_mem.context.capsules import HotMemoryCapsule, HotMemoryCapsuleBuilder
from phone_mem.context.token_counter import ConservativeTokenCounter, TokenCounter
from phone_mem.governance.audit import AuditLog
from phone_mem.personal_memory_service.events import AuditOperation
from phone_mem.personal_memory_service.retrieval import MemorySnippet, RetrievalResult


@dataclass(frozen=True)
class ContextTokenBudget:
    max_tokens: int
    safety_reserve_tokens: int
    output_reserve_tokens: int
    tool_reserve_tokens: int
    available_memory_tokens: int
    used_tokens: int


@dataclass(frozen=True)
class ContextBundle:
    task: dict[str, Any]
    snippets: list[MemorySnippet]
    hot_memory_capsules: list[HotMemoryCapsule]
    evidence_event_ids: list[str]
    token_budget: ContextTokenBudget
    omitted_memory: list[dict[str, str]]
    safety_metadata: dict[str, Any]


class ContextAssembler:
    def __init__(
        self,
        audit_log: AuditLog | None = None,
        token_counter: TokenCounter | None = None,
    ) -> None:
        self._audit_log = audit_log
        self._token_counter = token_counter or ConservativeTokenCounter()

    def build_context(
        self,
        retrieval_results: list[RetrievalResult],
        *,
        task: dict[str, Any],
        budget: ContextBudget,
        caller: str,
    ) -> ContextBundle:
        selected: list[MemorySnippet] = []
        omitted: list[dict[str, str]] = []
        used_tokens = 0

        for result in retrieval_results:
            snippet_tokens = self._estimate_tokens(result.snippet)
            if used_tokens + snippet_tokens > budget.available_memory_tokens:
                omitted.append({"event_id": result.event_id, "reason": "budget_exhausted"})
                continue
            selected.append(result.snippet)
            used_tokens += snippet_tokens

        capsule_result = HotMemoryCapsuleBuilder(self._token_counter).build(
            selected,
            omitted_memory=omitted,
            available_memory_tokens=budget.available_memory_tokens,
        )
        evidence_event_ids = self._evidence_event_ids(selected)
        bundle = ContextBundle(
            task=dict(task),
            snippets=selected,
            hot_memory_capsules=capsule_result.capsules,
            evidence_event_ids=evidence_event_ids,
            token_budget=ContextTokenBudget(
                max_tokens=budget.max_tokens,
                safety_reserve_tokens=budget.safety_reserve_tokens,
                output_reserve_tokens=budget.output_reserve_tokens,
                tool_reserve_tokens=budget.tool_reserve_tokens,
                available_memory_tokens=budget.available_memory_tokens,
                used_tokens=used_tokens,
            ),
            omitted_memory=omitted,
            safety_metadata={
                "memory_is_data_not_instruction": True,
                "runtime_neutral": True,
                "capsule_budget": {
                    "separate_from_snippets": True,
                    "budget_tokens": capsule_result.budget_tokens,
                    "used_tokens": capsule_result.used_tokens,
                    "omitted_capsules": capsule_result.omitted_capsules,
                },
            },
        )
        self._record_audit(caller, task, evidence_event_ids, budget)
        return bundle

    def _estimate_tokens(self, snippet: MemorySnippet) -> int:
        return self._token_counter.count(snippet.text)

    def _evidence_event_ids(self, snippets: list[MemorySnippet]) -> list[str]:
        event_ids: list[str] = []
        for snippet in snippets:
            for event_id in snippet.evidence_event_ids:
                if event_id not in event_ids:
                    event_ids.append(event_id)
        return event_ids

    def _record_audit(
        self,
        caller: str,
        task: dict[str, Any],
        evidence_event_ids: list[str],
        budget: ContextBudget,
    ) -> None:
        if self._audit_log is None:
            return
        self._audit_log.record(
            caller=caller,
            operation=AuditOperation.CONTEXT_BUILD,
            scope={
                "task": dict(task),
                "budget": {
                    "max_tokens": budget.max_tokens,
                    "available_memory_tokens": budget.available_memory_tokens,
                },
            },
            affected_event_ids=evidence_event_ids,
            outcome="allowed",
        )
