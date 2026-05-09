from __future__ import annotations

from collections import Counter
from typing import Any

from phone_mem.context.assembler import ContextBundle
from phone_mem.context.token_counter import ConservativeTokenCounter
from phone_mem.personal_memory_service.events import (
    AuditOperation,
    AuditRecord,
    LifecycleState,
    MemoryEvent,
    MemoryLayer,
    MemorySelector,
)
from phone_mem.personal_memory_service.maintenance import MemoryMaintenance
from phone_mem.personal_memory_service.retrieval import RetrievalResult
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore


class MemoryServiceMetrics:
    def __init__(self, store: SQLiteMemoryStore) -> None:
        self._store = store
        self._latest_context_bundle: ContextBundle | None = None
        self._latest_retrieval_results: list[RetrievalResult] = []
        self._total_hits_observed = 0
        self._token_counter = ConservativeTokenCounter()

    def record_retrieval_results(self, results: list[RetrievalResult]) -> None:
        self._latest_retrieval_results = list(results)
        self._total_hits_observed += len(results)

    def record_context_bundle(self, bundle: ContextBundle) -> None:
        self._latest_context_bundle = bundle

    def snapshot(self) -> dict[str, dict[str, Any]]:
        audit_records = self._store.query_audit_records()
        events = self._store.query_events()
        return {
            "retrieval": self._retrieval_metrics(audit_records),
            "permission": {
                "denied_audit_records": sum(1 for record in audit_records if record.outcome == "denied"),
            },
            "audit": self._audit_metrics(audit_records, events),
            "deletion": self._deletion_metrics(),
            "context": self._context_metrics(audit_records),
            "capture": self._capture_metrics(events),
            "reflection": self._reflection_metrics(events),
        }

    def _count_operations(
        self,
        audit_records: list[AuditRecord],
        operation: AuditOperation,
    ) -> int:
        return sum(1 for record in audit_records if record.operation == operation)

    def _retrieval_metrics(self, audit_records: list[AuditRecord]) -> dict[str, Any]:
        return {
            "read_audit_records": self._count_operations(audit_records, AuditOperation.READ),
            "latest_hit_count": len(self._latest_retrieval_results),
            "total_hits_observed": self._total_hits_observed,
            "latest_score_component_distribution": self._score_component_distribution(
                self._latest_retrieval_results
            ),
        }

    def _context_metrics(self, audit_records: list[AuditRecord]) -> dict[str, Any]:
        context_build_audit_records = self._count_operations(
            audit_records,
            AuditOperation.CONTEXT_BUILD,
        )
        if self._latest_context_bundle is None:
            return {
                "context_build_audit_records": context_build_audit_records,
                "latest_budget_used_tokens": None,
                "latest_budget_limit_tokens": None,
                "latest_snippet_count": 0,
                "latest_capsule_count": 0,
                "latest_capsule_used_tokens": 0,
                "latest_capsule_budget_tokens": 0,
                "latest_omitted_memory_reasons": {},
                "latest_raw_retrieval_tokens": 0,
                "latest_compression_ratio": None,
                "latest_relation_path_count": 0,
            }
        bundle = self._latest_context_bundle
        raw_retrieval_tokens = self._raw_retrieval_tokens()
        used_tokens = bundle.token_budget.used_tokens
        return {
            "context_build_audit_records": context_build_audit_records,
            "latest_budget_used_tokens": used_tokens,
            "latest_budget_limit_tokens": bundle.token_budget.available_memory_tokens,
            "latest_snippet_count": len(bundle.snippets),
            "latest_capsule_count": len(bundle.hot_memory_capsules),
            "latest_capsule_used_tokens": self._capsule_budget_metadata("used_tokens"),
            "latest_capsule_budget_tokens": self._capsule_budget_metadata("budget_tokens"),
            "latest_omitted_memory_reasons": dict(
                Counter(item["reason"] for item in bundle.omitted_memory)
            ),
            "latest_raw_retrieval_tokens": raw_retrieval_tokens,
            "latest_compression_ratio": self._compression_ratio(used_tokens, raw_retrieval_tokens),
            "latest_relation_path_count": len(bundle.relation_paths),
        }

    def _deletion_metrics(self) -> dict[str, Any]:
        tombstones = self._store.list_tombstones()
        deleted_events = self._store.query_events(lifecycle_deleted_selector())
        deleted_event_ids = {event.event_id for event in deleted_events}
        tombstone_event_ids = {tombstone.event_id for tombstone in tombstones}
        propagated_count = len(tombstone_event_ids.intersection(deleted_event_ids))
        return {
            "tombstone_count": len(tombstones),
            "deleted_event_count": len(deleted_events),
            "propagation_coverage": self._coverage(propagated_count, len(tombstone_event_ids)),
        }

    def _audit_metrics(
        self,
        audit_records: list[AuditRecord],
        events: list[MemoryEvent],
    ) -> dict[str, Any]:
        operations_without_audit = self._operations_without_audit(audit_records, events)
        expected_operations = len(events) + len(self._store.list_tombstones())
        audited_expected_operations = max(expected_operations - operations_without_audit, 0)
        return {
            "write_audit_records": self._count_operations(audit_records, AuditOperation.WRITE),
            "total_records": len(audit_records),
            "operations_without_audit": operations_without_audit,
            "audit_completeness": self._coverage(
                audited_expected_operations,
                expected_operations,
            ),
        }

    def _capture_metrics(self, events: list[MemoryEvent]) -> dict[str, Any]:
        triggers: Counter[str] = Counter()
        captured_event_ids: set[str] = set()
        for event in events:
            for relation in event.relations:
                if relation.get("type") != "capture_trigger":
                    continue
                captured_event_ids.add(event.event_id)
                triggers[str(relation.get("value", ""))] += 1
        return {
            "captured_event_count": len(captured_event_ids),
            "captured_events_by_trigger": dict(sorted(triggers.items())),
        }

    def _reflection_metrics(self, events: list[MemoryEvent]) -> dict[str, Any]:
        open_proposals = MemoryMaintenance(self._store).reflect().proposals
        accepted_count = sum(1 for event in events if self._is_accepted_reflection(event))
        return {
            "open_proposal_count": len(open_proposals),
            "accepted_count": accepted_count,
            "acceptance_rate": self._acceptance_rate(accepted_count, len(open_proposals)),
        }

    def _score_component_distribution(
        self,
        results: list[RetrievalResult],
    ) -> dict[str, dict[str, float | int]]:
        values_by_component: dict[str, list[float]] = {}
        for result in results:
            components = result.explanation.get("score_components")
            if not isinstance(components, dict):
                continue
            for component, value in components.items():
                values_by_component.setdefault(component, []).append(float(value))
        return {
            component: {
                "count": len(values),
                "min": round(min(values), 6),
                "max": round(max(values), 6),
                "avg": round(sum(values) / len(values), 6),
            }
            for component, values in sorted(values_by_component.items())
            if values
        }

    def _raw_retrieval_tokens(self) -> int:
        return sum(
            self._token_counter.count(result.snippet.text)
            for result in self._latest_retrieval_results
        )

    def _capsule_budget_metadata(self, key: str) -> int:
        if self._latest_context_bundle is None:
            return 0
        capsule_budget = self._latest_context_bundle.safety_metadata.get("capsule_budget", {})
        if not isinstance(capsule_budget, dict):
            return 0
        return int(capsule_budget.get(key, 0))

    def _compression_ratio(self, used_tokens: int, raw_tokens: int) -> float | None:
        if raw_tokens <= 0:
            return None
        return round(used_tokens / raw_tokens, 6)

    def _coverage(self, covered: int, total: int) -> float:
        if total == 0:
            return 1.0
        return round(covered / total, 6)

    def _operations_without_audit(
        self,
        audit_records: list[AuditRecord],
        events: list[MemoryEvent],
    ) -> int:
        written_event_ids = {
            event_id
            for record in audit_records
            if record.operation == AuditOperation.WRITE and record.outcome == "allowed"
            for event_id in record.affected_event_ids
        }
        deleted_event_ids = {
            event_id
            for record in audit_records
            if record.operation == AuditOperation.DELETE and record.outcome == "allowed"
            for event_id in record.affected_event_ids
        }
        missing_writes = sum(1 for event in events if event.event_id not in written_event_ids)
        missing_deletes = sum(
            1
            for tombstone in self._store.list_tombstones()
            if tombstone.event_id not in deleted_event_ids
        )
        return missing_writes + missing_deletes

    def _is_accepted_reflection(self, event: MemoryEvent) -> bool:
        if event.lifecycle.state != LifecycleState.ACTIVE:
            return False
        if event.memory_layer not in {MemoryLayer.SEMANTIC, MemoryLayer.PROCEDURAL}:
            return False
        return any(
            relation.get("type") == "review_policy"
            and str(relation.get("value", "")).lower() == "accepted"
            for relation in event.relations
        )

    def _acceptance_rate(self, accepted_count: int, open_proposal_count: int) -> float | None:
        if accepted_count == 0:
            return None
        return self._coverage(accepted_count, accepted_count + open_proposal_count)


def lifecycle_deleted_selector() -> object:
    return MemorySelector(lifecycle_states=[LifecycleState.DELETED])
