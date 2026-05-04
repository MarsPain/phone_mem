from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from phone_mem.personal_memory_service.events import AuditOperation


@dataclass(frozen=True)
class ServiceErrorContext:
    operation: AuditOperation
    caller: str
    affected_event_ids: list[str] = field(default_factory=list)
    event_id: str | None = None
    selector: dict[str, Any] | None = None
    denial_reason: str | None = None


class MemoryPermissionDenied(PermissionError):
    def __init__(
        self,
        *,
        operation: AuditOperation,
        caller: str,
        denial_reason: str | None,
        affected_event_ids: list[str] | None = None,
        selector: dict[str, Any] | None = None,
    ) -> None:
        reason = denial_reason or "permission denied"
        self.context = ServiceErrorContext(
            operation=operation,
            caller=caller,
            affected_event_ids=list(affected_event_ids or []),
            selector=selector,
            denial_reason=reason,
        )
        self.message = f"{operation.value} denied for {caller}: {reason}"
        super().__init__(self.message)

    @property
    def operation(self) -> AuditOperation:
        return self.context.operation

    @property
    def caller(self) -> str:
        return self.context.caller

    @property
    def affected_event_ids(self) -> list[str]:
        return list(self.context.affected_event_ids)

    @property
    def selector(self) -> dict[str, Any] | None:
        return self.context.selector

    @property
    def denial_reason(self) -> str:
        assert self.context.denial_reason is not None
        return self.context.denial_reason


class MemoryEventNotFound(KeyError):
    def __init__(
        self,
        *,
        operation: AuditOperation,
        caller: str,
        event_id: str,
    ) -> None:
        self.context = ServiceErrorContext(
            operation=operation,
            caller=caller,
            affected_event_ids=[event_id],
            event_id=event_id,
            denial_reason="memory event not found",
        )
        self.message = f"{operation.value} failed for {caller}: memory event not found"
        super().__init__(event_id)

    @property
    def operation(self) -> AuditOperation:
        return self.context.operation

    @property
    def caller(self) -> str:
        return self.context.caller

    @property
    def affected_event_ids(self) -> list[str]:
        return list(self.context.affected_event_ids)

    @property
    def event_id(self) -> str:
        assert self.context.event_id is not None
        return self.context.event_id

    @property
    def denial_reason(self) -> str:
        assert self.context.denial_reason is not None
        return self.context.denial_reason

    def __str__(self) -> str:
        return self.message
