from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from phone_mem.governance.permissions import PermissionService
from phone_mem.personal_memory_service.events import AuditOperation, MemoryEvent


@dataclass(frozen=True)
class MemoryView:
    events: list[MemoryEvent]
    denied_event_ids: dict[str, str]


class MemoryViewProjector:
    def __init__(self, permission_service: PermissionService) -> None:
        self._permission_service = permission_service

    def project(
        self,
        caller: str,
        operation: AuditOperation,
        events: list[MemoryEvent],
        *,
        at: datetime | None = None,
    ) -> MemoryView:
        allowed_events: list[MemoryEvent] = []
        denied_event_ids: dict[str, str] = {}
        for event in events:
            decision = self._permission_service.can_access(caller, operation, event, at=at)
            if decision.allowed:
                allowed_events.append(event)
                continue
            denied_event_ids[event.event_id] = decision.reason or "access denied"
        return MemoryView(events=allowed_events, denied_event_ids=denied_event_ids)
