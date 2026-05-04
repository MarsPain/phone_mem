from __future__ import annotations

from typing import Any

from phone_mem.context.assembler import ContextBundle
from phone_mem.personal_memory_service.events import AuditOperation, AuditRecord, LifecycleState
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore


class MemoryServiceMetrics:
    def __init__(self, store: SQLiteMemoryStore) -> None:
        self._store = store
        self._latest_context_bundle: ContextBundle | None = None

    def record_context_bundle(self, bundle: ContextBundle) -> None:
        self._latest_context_bundle = bundle

    def snapshot(self) -> dict[str, dict[str, Any]]:
        audit_records = self._store.query_audit_records()
        return {
            "retrieval": {
                "read_audit_records": self._count_operations(audit_records, AuditOperation.READ),
            },
            "permission": {
                "denied_audit_records": sum(1 for record in audit_records if record.outcome == "denied"),
            },
            "audit": {
                "write_audit_records": self._count_operations(audit_records, AuditOperation.WRITE),
                "total_records": len(audit_records),
            },
            "deletion": {
                "tombstone_count": len(self._store.list_tombstones()),
                "deleted_event_count": len(
                    self._store.query_events(lifecycle_deleted_selector())
                ),
            },
            "context": self._context_metrics(audit_records),
        }

    def _count_operations(
        self,
        audit_records: list[AuditRecord],
        operation: AuditOperation,
    ) -> int:
        return sum(1 for record in audit_records if record.operation == operation)

    def _context_metrics(self, audit_records: list[AuditRecord]) -> dict[str, int | None]:
        if self._latest_context_bundle is None:
            return {
                "context_build_audit_records": self._count_operations(
                    audit_records,
                    AuditOperation.CONTEXT_BUILD,
                ),
                "latest_budget_used_tokens": None,
                "latest_budget_limit_tokens": None,
            }
        return {
            "context_build_audit_records": self._count_operations(
                audit_records,
                AuditOperation.CONTEXT_BUILD,
            ),
            "latest_budget_used_tokens": self._latest_context_bundle.token_budget.used_tokens,
            "latest_budget_limit_tokens": (
                self._latest_context_bundle.token_budget.available_memory_tokens
            ),
        }


def lifecycle_deleted_selector() -> object:
    from phone_mem.personal_memory_service.events import MemorySelector

    return MemorySelector(lifecycle_states=[LifecycleState.DELETED])
