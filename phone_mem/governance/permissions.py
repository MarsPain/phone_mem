from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from phone_mem.governance.models import PermissionDecision, PermissionGrant, PermissionScope
from phone_mem.personal_memory_service.events import (
    AuditOperation,
    MemoryEvent,
)


class PermissionService:
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

    def grant(self, caller: str, scope: PermissionScope, duration_seconds: int) -> PermissionGrant:
        granted_at = self._clock()
        grant = PermissionGrant(
            grant_id=self._id_factory(),
            caller=caller,
            scope=scope,
            granted_at=granted_at,
            expires_at=granted_at + timedelta(seconds=duration_seconds),
        )
        self._store.insert_permission_grant(grant)
        return grant

    def revoke(self, grant_id: str) -> None:
        for grant in self._store.list_permission_grants():
            if grant.grant_id == grant_id:
                self._store.update_permission_grant(replace(grant, revoked_at=self._clock()))
                return

    def can_access(
        self,
        caller: str,
        operation: AuditOperation,
        event: MemoryEvent,
        *,
        at: datetime | None = None,
    ) -> PermissionDecision:
        checked_at = at or self._clock()
        for grant in self._permission_grants_for_check(caller, operation, checked_at):
            if not grant.is_active(checked_at):
                continue
            if self._matches(grant.scope, operation, event):
                return PermissionDecision(allowed=True, grant_id=grant.grant_id)
        return PermissionDecision(allowed=False, reason="no active grant matched")

    def _permission_grants_for_check(
        self,
        caller: str,
        operation: AuditOperation,
        checked_at: datetime,
    ) -> list[PermissionGrant]:
        active_grants = getattr(self._store, "list_active_permission_grants", None)
        if active_grants is not None:
            return active_grants(caller, operation, at=checked_at)
        return self._store.list_permission_grants(caller=caller)

    def _matches(
        self,
        scope: PermissionScope,
        operation: AuditOperation,
        event: MemoryEvent,
    ) -> bool:
        if scope.operations and operation not in scope.operations:
            return False
        if scope.memory_layers and event.memory_layer not in scope.memory_layers:
            return False
        if scope.privacy_levels and event.privacy.level not in scope.privacy_levels:
            return False
        if scope.apps and event.source.app not in scope.apps:
            return False
        if scope.entities and not set(scope.entities).intersection(event.entities):
            return False
        if scope.time_start is not None and event.valid_time.start < scope.time_start:
            return False
        if scope.time_end is not None and event.valid_time.start > scope.time_end:
            return False
        if scope.processing_policies and event.privacy.processing_policy not in scope.processing_policies:
            return False
        return True
