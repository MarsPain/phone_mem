from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from phone_mem.personal_memory_service.events import AuditOperation, AuditRecord


@dataclass(frozen=True)
class AuditSelector:
    caller: str | None = None
    operations: list[AuditOperation] = field(default_factory=list)


class AuditLog:
    def __init__(
        self,
        store: object,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._store = store
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def record(
        self,
        caller: str,
        operation: AuditOperation,
        scope: dict[str, object],
        affected_event_ids: list[str],
        outcome: str,
        denial_reason: str | None = None,
    ) -> AuditRecord:
        record = AuditRecord(
            operation_id=self._id_factory(),
            caller=caller,
            operation=operation,
            scope=scope,
            affected_event_ids=affected_event_ids,
            occurred_at=self._clock(),
            outcome=outcome,
            denial_reason=denial_reason,
        )
        self._store.insert_audit_record(record)
        return record

    def query(self, selector: AuditSelector | None = None) -> list[AuditRecord]:
        return self._store.query_audit_records(selector)
