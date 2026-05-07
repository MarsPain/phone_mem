from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from phone_mem.personal_memory_service.events import (
    AuditOperation,
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
