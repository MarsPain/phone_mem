from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class MemoryEventValidationError(ValueError):
    """Raised when a canonical memory event violates required invariants."""


class EventType(StrEnum):
    USER_UTTERANCE = "user_utterance"
    APP_ACTION = "app_action"
    VISUAL_SCENE = "visual_scene"
    SENSOR_SNAPSHOT = "sensor_snapshot"
    DERIVED_SUMMARY = "derived_summary"
    PROCEDURAL_SKILL = "procedural_skill"


class MemoryLayer(StrEnum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class Actor(StrEnum):
    USER = "user"
    AGENT = "agent"
    APP = "app"
    CLOUD_CONSOLIDATOR = "cloud_consolidator"


class Modality(StrEnum):
    TEXT = "text"
    APP_EVENT = "app_event"
    VISUAL = "visual"
    SENSOR = "sensor"


class Attribution(StrEnum):
    USER_STATED = "user_stated"
    AGENT_INFERRED = "agent_inferred"
    APP_SYNCED = "app_synced"
    DERIVED = "derived"


class PrivacyLevel(StrEnum):
    SENSITIVE = "sensitive"
    PERSONAL = "personal"
    PUBLIC = "public"


class ProcessingPolicy(StrEnum):
    DEVICE_ONLY = "device_only"
    CLIENT_ENCRYPTED_SYNC = "client_encrypted_sync"
    PRIVATE_COMPUTE = "private_compute"
    CLOUD_INDEXABLE = "cloud_indexable"


class LifecycleState(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DELETED = "deleted"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class ValidTime:
    start: datetime
    end: datetime | None = None

    def __post_init__(self) -> None:
        if self.end is not None and self.end < self.start:
            raise MemoryEventValidationError("valid_time.end cannot be earlier than start")

    def to_dict(self) -> dict[str, str | None]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end is not None else None,
        }


@dataclass(frozen=True)
class EventSource:
    app: str
    actor: Actor
    modality: list[Modality]
    attribution: Attribution

    def __post_init__(self) -> None:
        if not self.app.strip():
            raise MemoryEventValidationError("source.app is required")
        if not self.modality:
            raise MemoryEventValidationError("source.modality must contain at least one value")

    def to_dict(self) -> dict[str, Any]:
        return {
            "app": self.app,
            "actor": self.actor.value,
            "modality": [item.value for item in self.modality],
            "attribution": self.attribution.value,
        }


@dataclass(frozen=True)
class Privacy:
    level: PrivacyLevel
    allowed_scopes: list[str] = field(default_factory=list)
    processing_policy: ProcessingPolicy = ProcessingPolicy.DEVICE_ONLY

    def __post_init__(self) -> None:
        if self.level == PrivacyLevel.SENSITIVE and self.processing_policy != ProcessingPolicy.DEVICE_ONLY:
            raise MemoryEventValidationError("sensitive memory must use device_only processing")
        if self.level == PrivacyLevel.PUBLIC and self.processing_policy == ProcessingPolicy.PRIVATE_COMPUTE:
            raise MemoryEventValidationError("public memory cannot require private_compute processing")

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "allowed_scopes": list(self.allowed_scopes),
            "processing_policy": self.processing_policy.value,
        }


@dataclass(frozen=True)
class Quality:
    confidence: float
    importance: float
    freshness_half_life_days: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise MemoryEventValidationError("quality.confidence must be between 0 and 1")
        if not 0.0 <= self.importance <= 1.0:
            raise MemoryEventValidationError("quality.importance must be between 0 and 1")
        if self.freshness_half_life_days <= 0:
            raise MemoryEventValidationError("quality.freshness_half_life_days must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "importance": self.importance,
            "freshness_half_life_days": self.freshness_half_life_days,
        }


@dataclass(frozen=True)
class Lineage:
    parents: list[str] = field(default_factory=list)
    derived_from: list[str] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "parents": list(self.parents),
            "derived_from": list(self.derived_from),
            "supersedes": list(self.supersedes),
        }


@dataclass(frozen=True)
class Lifecycle:
    state: LifecycleState = LifecycleState.ACTIVE
    deleted_at: datetime | None = None
    delete_reason: str | None = None

    def __post_init__(self) -> None:
        if self.state == LifecycleState.DELETED and self.deleted_at is None:
            raise MemoryEventValidationError("deleted lifecycle requires deleted_at")
        if self.state != LifecycleState.DELETED and self.deleted_at is not None:
            raise MemoryEventValidationError("deleted_at is only valid for deleted lifecycle state")
        if self.state != LifecycleState.DELETED and self.delete_reason is not None:
            raise MemoryEventValidationError("delete_reason is only valid for deleted lifecycle state")

    def mark_deleted(self, *, deleted_at: datetime, reason: str) -> Lifecycle:
        if not reason.strip():
            raise MemoryEventValidationError("delete reason is required")
        return Lifecycle(
            state=LifecycleState.DELETED,
            deleted_at=deleted_at,
            delete_reason=reason,
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "state": self.state.value,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at is not None else None,
            "delete_reason": self.delete_reason,
        }


@dataclass(frozen=True)
class MemoryEvent:
    event_id: str
    created_at: datetime
    valid_time: ValidTime
    event_type: EventType
    memory_layer: MemoryLayer
    semantic_description: str
    entities: list[str]
    relations: list[dict[str, Any]]
    source: EventSource
    privacy: Privacy
    quality: Quality
    lineage: Lineage
    lifecycle: Lifecycle

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise MemoryEventValidationError("event_id is required")
        if not self.semantic_description.strip():
            raise MemoryEventValidationError("semantic_description is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "created_at": self.created_at.isoformat(),
            "valid_time": self.valid_time.to_dict(),
            "event_type": self.event_type.value,
            "memory_layer": self.memory_layer.value,
            "semantic_description": self.semantic_description,
            "entities": list(self.entities),
            "relations": list(self.relations),
            "source": self.source.to_dict(),
            "privacy": self.privacy.to_dict(),
            "quality": self.quality.to_dict(),
            "lineage": self.lineage.to_dict(),
            "lifecycle": self.lifecycle.to_dict(),
        }
