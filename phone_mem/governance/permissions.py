from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from phone_mem.personal_memory_service.events import (
    AuditOperation,
    MemoryEvent,
    MemoryLayer,
    PrivacyLevel,
    ProcessingPolicy,
)


@dataclass(frozen=True)
class PermissionScope:
    operations: list[AuditOperation] = field(default_factory=list)
    memory_layers: list[MemoryLayer] = field(default_factory=list)
    privacy_levels: list[PrivacyLevel] = field(default_factory=list)
    apps: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    time_start: datetime | None = None
    time_end: datetime | None = None
    processing_policies: list[ProcessingPolicy] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.operations:
            data["operations"] = [item.value for item in self.operations]
        if self.memory_layers:
            data["memory_layers"] = [item.value for item in self.memory_layers]
        if self.privacy_levels:
            data["privacy_levels"] = [item.value for item in self.privacy_levels]
        if self.apps:
            data["apps"] = list(self.apps)
        if self.entities:
            data["entities"] = list(self.entities)
        if self.time_start is not None:
            data["time_start"] = self.time_start.isoformat()
        if self.time_end is not None:
            data["time_end"] = self.time_end.isoformat()
        if self.processing_policies:
            data["processing_policies"] = [item.value for item in self.processing_policies]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PermissionScope:
        return cls(
            operations=[AuditOperation(item) for item in data.get("operations", [])],
            memory_layers=[MemoryLayer(item) for item in data.get("memory_layers", [])],
            privacy_levels=[PrivacyLevel(item) for item in data.get("privacy_levels", [])],
            apps=list(data.get("apps", [])),
            entities=list(data.get("entities", [])),
            time_start=(
                datetime.fromisoformat(data["time_start"])
                if data.get("time_start") is not None
                else None
            ),
            time_end=(
                datetime.fromisoformat(data["time_end"])
                if data.get("time_end") is not None
                else None
            ),
            processing_policies=[
                ProcessingPolicy(item) for item in data.get("processing_policies", [])
            ],
        )


@dataclass(frozen=True)
class PermissionGrant:
    grant_id: str
    caller: str
    scope: PermissionScope
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None

    def is_active(self, at: datetime) -> bool:
        return self.revoked_at is None and self.granted_at <= at <= self.expires_at


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str | None = None
    grant_id: str | None = None


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
        for grant in self._store.list_permission_grants(caller=caller):
            if not grant.is_active(checked_at):
                continue
            if self._matches(grant.scope, operation, event):
                return PermissionDecision(allowed=True, grant_id=grant.grant_id)
        return PermissionDecision(allowed=False, reason="no active grant matched")

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
