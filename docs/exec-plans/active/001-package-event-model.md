# 001 Package And Event Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the Python package skeleton and canonical event model for the local Personal Memory Service.

**Architecture:** This task establishes pure domain models only. `phone_mem/personal_memory_service/events.py` owns canonical event value objects and validation, while `phone_mem/personal_memory_service/constructor.py` turns structured candidate dictionaries into validated events without depending on SQLite, retrieval, permissions, context assembly, model runtimes, or mobile platform code.

**Tech Stack:** Python 3.13 standard library, `dataclasses`, `enum`, `datetime`, `uuid`, and `unittest`.

Status: active
Type: execution

---

## Goal

Create the initial Python package structure and canonical event model needed by the local Personal Memory Service.

This subplan belongs to Stage 1: the Python reference implementation. It must not introduce mobile runtime, OS integration, SQLite persistence, permission enforcement, retrieval ranking, context assembly, cloud sync, or model-provider dependencies.

## Scope

- Add the minimum `phone_mem/` package skeleton needed for MVP event construction.
- Define canonical event, source, privacy, quality, lineage, lifecycle, selector, and audit-related value models.
- Keep event construction independent from persistence and model runtimes.
- Add deterministic validation for required event fields, enum fields, privacy policy pairing, quality bounds, and lifecycle state transitions.
- Add unit tests for valid events, invalid required fields, privacy policy classification, lineage defaults, lifecycle state transitions, and constructor normalization.

## Design Inputs

- [Personal Memory Service](../../design-docs/personal-memory-service.md)
- [Memory Lifecycle And Data Flow](../../design-docs/memory-lifecycle-and-data-flow.md)
- [Data](../../DATA.md)
- [Backend](../../BACKEND.md)

## Out Of Scope

- SQLite persistence.
- Permission grant enforcement.
- Memory view projection.
- Retrieval ranking.
- Context assembly.
- Cloud or model runtime adapters.
- Production encryption.
- Mobile runtime code.

## File Structure

- Create `phone_mem/__init__.py`: package marker and public package version.
- Create `phone_mem/personal_memory_service/__init__.py`: exports event models and constructor entrypoint for Stage 1.
- Create `phone_mem/personal_memory_service/events.py`: domain enums, immutable value models, canonical `MemoryEvent`, selectors, validation errors, serialization helpers, and lifecycle transition helper.
- Create `phone_mem/personal_memory_service/constructor.py`: `MemoryCandidate`, `MemoryConstructor`, and deterministic normalization/classification hooks.
- Create `tests/test_event_models.py`: focused unit tests for domain model behavior.
- Create `tests/test_memory_constructor.py`: focused unit tests for candidate-to-event normalization.
- Modify `docs/exec-plans/active/001-package-event-model.md`: mark implementation checkboxes as work is completed during execution.

No other production files should be touched during 001 unless a test exposes a naming mismatch with the canonical docs.

## Steps

### Task 1: Package Skeleton

**Files:**
- Create: `phone_mem/__init__.py`
- Create: `phone_mem/personal_memory_service/__init__.py`
- Test: `tests/test_event_models.py`

- [x] **Step 1: Write the failing package import test**

Add `tests/test_event_models.py` with this initial content:

```python
from __future__ import annotations

import unittest


class PackageImportTest(unittest.TestCase):
    def test_personal_memory_service_package_imports(self) -> None:
        import phone_mem
        import phone_mem.personal_memory_service as service_package

        self.assertEqual(phone_mem.__version__, "0.1.0")
        self.assertTrue(hasattr(service_package, "__all__"))


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run the focused test to verify it fails**

Run:

```bash
uv run python -m unittest tests.test_event_models.PackageImportTest
```

Expected: `ModuleNotFoundError: No module named 'phone_mem'`.

- [x] **Step 3: Create the package markers**

Create `phone_mem/__init__.py`:

```python
from __future__ import annotations

__version__ = "0.1.0"
```

Create `phone_mem/personal_memory_service/__init__.py`:

```python
from __future__ import annotations

__all__: list[str] = []
```

- [x] **Step 4: Run the focused test to verify it passes**

Run:

```bash
uv run python -m unittest tests.test_event_models.PackageImportTest
```

Expected: `OK`.

- [x] **Step 5: Commit the package skeleton**

Run:

```bash
git add phone_mem/__init__.py phone_mem/personal_memory_service/__init__.py tests/test_event_models.py docs/exec-plans/active/001-package-event-model.md
git commit -m "feat: add phone_mem package skeleton"
```

### Task 2: Canonical Event Value Models

**Files:**
- Modify: `phone_mem/personal_memory_service/__init__.py`
- Create: `phone_mem/personal_memory_service/events.py`
- Modify: `tests/test_event_models.py`

- [x] **Step 1: Extend tests for valid canonical events**

Replace `tests/test_event_models.py` with:

```python
from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    EventSource,
    EventType,
    Lifecycle,
    LifecycleState,
    Lineage,
    MemoryEvent,
    MemoryLayer,
    Modality,
    Privacy,
    PrivacyLevel,
    ProcessingPolicy,
    Quality,
    ValidTime,
)


class PackageImportTest(unittest.TestCase):
    def test_personal_memory_service_package_imports(self) -> None:
        import phone_mem
        import phone_mem.personal_memory_service as service_package

        self.assertEqual(phone_mem.__version__, "0.1.0")
        self.assertIn("MemoryEvent", service_package.__all__)


class MemoryEventModelTest(unittest.TestCase):
    def test_valid_user_stated_event_serializes_to_canonical_dict(self) -> None:
        created_at = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        event = MemoryEvent(
            event_id="event-1",
            created_at=created_at,
            valid_time=ValidTime(start=created_at),
            event_type=EventType.USER_UTTERANCE,
            memory_layer=MemoryLayer.EPISODIC,
            semantic_description="User prefers morning planning sessions.",
            entities=["user"],
            relations=[],
            source=EventSource(
                app="system_assistant",
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=Attribution.USER_STATED,
            ),
            privacy=Privacy(
                level=PrivacyLevel.PERSONAL,
                allowed_scopes=["system_assistant"],
                processing_policy=ProcessingPolicy.CLIENT_ENCRYPTED_SYNC,
            ),
            quality=Quality(confidence=0.95, importance=0.7, freshness_half_life_days=30),
            lineage=Lineage(),
            lifecycle=Lifecycle(),
        )

        data = event.to_dict()

        self.assertEqual(data["event_id"], "event-1")
        self.assertEqual(data["created_at"], "2026-05-01T09:00:00+00:00")
        self.assertEqual(data["event_type"], "user_utterance")
        self.assertEqual(data["memory_layer"], "episodic")
        self.assertEqual(data["source"]["actor"], "user")
        self.assertEqual(data["privacy"]["level"], "personal")
        self.assertEqual(data["quality"]["confidence"], 0.95)
        self.assertEqual(data["lineage"]["parents"], [])
        self.assertEqual(data["lifecycle"]["state"], "active")


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run python -m unittest tests.test_event_models
```

Expected: import failure for `phone_mem.personal_memory_service.events`.

- [x] **Step 3: Implement enums, value objects, and serialization**

Create `phone_mem/personal_memory_service/events.py`:

```python
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
```

Update `phone_mem/personal_memory_service/__init__.py`:

```python
from __future__ import annotations

from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    EventSource,
    EventType,
    Lifecycle,
    LifecycleState,
    Lineage,
    MemoryEvent,
    MemoryEventValidationError,
    MemoryLayer,
    Modality,
    Privacy,
    PrivacyLevel,
    ProcessingPolicy,
    Quality,
    ValidTime,
)

__all__ = [
    "Actor",
    "Attribution",
    "EventSource",
    "EventType",
    "Lifecycle",
    "LifecycleState",
    "Lineage",
    "MemoryEvent",
    "MemoryEventValidationError",
    "MemoryLayer",
    "Modality",
    "Privacy",
    "PrivacyLevel",
    "ProcessingPolicy",
    "Quality",
    "ValidTime",
]
```

- [x] **Step 4: Run focused tests to verify they pass**

Run:

```bash
uv run python -m unittest tests.test_event_models
```

Expected: `OK`.

- [x] **Step 5: Commit canonical event value models**

Run:

```bash
git add phone_mem/personal_memory_service/__init__.py phone_mem/personal_memory_service/events.py tests/test_event_models.py docs/exec-plans/active/001-package-event-model.md
git commit -m "feat: add canonical memory event models"
```

### Task 3: Event Validation And Lifecycle Transitions

**Files:**
- Modify: `phone_mem/personal_memory_service/events.py`
- Modify: `tests/test_event_models.py`

- [x] **Step 1: Add tests for invalid fields and lifecycle transitions**

Append these tests inside `MemoryEventModelTest` in `tests/test_event_models.py`:

```python
    def test_blank_event_id_is_rejected(self) -> None:
        created_at = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)

        with self.assertRaisesRegex(Exception, "event_id is required"):
            MemoryEvent(
                event_id=" ",
                created_at=created_at,
                valid_time=ValidTime(start=created_at),
                event_type=EventType.USER_UTTERANCE,
                memory_layer=MemoryLayer.EPISODIC,
                semantic_description="User prefers morning planning sessions.",
                entities=[],
                relations=[],
                source=EventSource(
                    app="system_assistant",
                    actor=Actor.USER,
                    modality=[Modality.TEXT],
                    attribution=Attribution.USER_STATED,
                ),
                privacy=Privacy(level=PrivacyLevel.PERSONAL),
                quality=Quality(confidence=0.95, importance=0.7, freshness_half_life_days=30),
                lineage=Lineage(),
                lifecycle=Lifecycle(),
            )

    def test_sensitive_memory_cannot_leave_device_by_default(self) -> None:
        with self.assertRaisesRegex(Exception, "sensitive memory must use device_only processing"):
            Privacy(
                level=PrivacyLevel.SENSITIVE,
                processing_policy=ProcessingPolicy.CLIENT_ENCRYPTED_SYNC,
            )

    def test_quality_scores_are_bounded(self) -> None:
        with self.assertRaisesRegex(Exception, "quality.confidence must be between 0 and 1"):
            Quality(confidence=1.1, importance=0.5, freshness_half_life_days=30)

        with self.assertRaisesRegex(Exception, "quality.importance must be between 0 and 1"):
            Quality(confidence=0.9, importance=-0.1, freshness_half_life_days=30)

    def test_mark_deleted_requires_reason_and_timestamp(self) -> None:
        deleted_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
        lifecycle = Lifecycle().mark_deleted(deleted_at=deleted_at, reason="user requested deletion")

        self.assertEqual(lifecycle.state, LifecycleState.DELETED)
        self.assertEqual(lifecycle.deleted_at, deleted_at)
        self.assertEqual(lifecycle.delete_reason, "user requested deletion")

    def test_deleted_lifecycle_requires_deleted_at(self) -> None:
        with self.assertRaisesRegex(Exception, "deleted lifecycle requires deleted_at"):
            Lifecycle(state=LifecycleState.DELETED, delete_reason="missing timestamp")
```

- [x] **Step 2: Run focused tests to verify they fail**

Run:

```bash
uv run python -m unittest tests.test_event_models
```

Expected: failure with `AttributeError: 'Lifecycle' object has no attribute 'mark_deleted'`.

- [x] **Step 3: Implement lifecycle transition helper**

Add this method to the `Lifecycle` class in `phone_mem/personal_memory_service/events.py`:

```python
    def mark_deleted(self, *, deleted_at: datetime, reason: str) -> Lifecycle:
        if not reason.strip():
            raise MemoryEventValidationError("delete reason is required")
        return Lifecycle(
            state=LifecycleState.DELETED,
            deleted_at=deleted_at,
            delete_reason=reason,
        )
```

- [x] **Step 4: Run focused tests to verify they pass**

Run:

```bash
uv run python -m unittest tests.test_event_models
```

Expected: `OK`.

- [x] **Step 5: Commit validation and lifecycle helpers**

Run:

```bash
git add phone_mem/personal_memory_service/events.py tests/test_event_models.py docs/exec-plans/active/001-package-event-model.md
git commit -m "feat: validate memory event invariants"
```

### Task 4: Selectors And Audit-Related Value Models

**Files:**
- Modify: `phone_mem/personal_memory_service/__init__.py`
- Modify: `phone_mem/personal_memory_service/events.py`
- Modify: `tests/test_event_models.py`

- [x] **Step 1: Add tests for selectors and audit records**

Append these imports to the import list in `tests/test_event_models.py`:

```python
    AuditOperation,
    AuditRecord,
    MemorySelector,
```

Append these tests inside `MemoryEventModelTest`:

```python
    def test_memory_selector_serializes_only_selected_filters(self) -> None:
        selector = MemorySelector(
            event_ids=["event-1"],
            app="system_assistant",
            entities=["user"],
            memory_layers=[MemoryLayer.EPISODIC],
            privacy_levels=[PrivacyLevel.PERSONAL],
            lifecycle_states=[LifecycleState.ACTIVE],
        )

        data = selector.to_dict()

        self.assertEqual(data["event_ids"], ["event-1"])
        self.assertEqual(data["app"], "system_assistant")
        self.assertEqual(data["entities"], ["user"])
        self.assertEqual(data["memory_layers"], ["episodic"])
        self.assertEqual(data["privacy_levels"], ["personal"])
        self.assertEqual(data["lifecycle_states"], ["active"])
        self.assertNotIn("time_start", data)

    def test_audit_record_preserves_operation_and_affected_events(self) -> None:
        occurred_at = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
        audit = AuditRecord(
            operation_id="audit-1",
            caller="system_assistant",
            operation=AuditOperation.WRITE,
            scope={"app": "system_assistant"},
            affected_event_ids=["event-1"],
            occurred_at=occurred_at,
            outcome="allowed",
            denial_reason=None,
        )

        data = audit.to_dict()

        self.assertEqual(data["operation"], "write")
        self.assertEqual(data["affected_event_ids"], ["event-1"])
        self.assertEqual(data["occurred_at"], "2026-05-01T10:00:00+00:00")
        self.assertEqual(data["outcome"], "allowed")
```

- [x] **Step 2: Run focused tests to verify they fail**

Run:

```bash
uv run python -m unittest tests.test_event_models
```

Expected: import failure for `AuditOperation`, `AuditRecord`, or `MemorySelector`.

- [x] **Step 3: Implement selector and audit value models**

Add these definitions to `phone_mem/personal_memory_service/events.py`:

```python
class AuditOperation(StrEnum):
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    GRANT = "grant"
    REVOKE = "revoke"
    PROJECTION = "projection"
    CONTEXT_BUILD = "context_build"


@dataclass(frozen=True)
class MemorySelector:
    event_ids: list[str] = field(default_factory=list)
    app: str | None = None
    entities: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    memory_layers: list[MemoryLayer] = field(default_factory=list)
    privacy_levels: list[PrivacyLevel] = field(default_factory=list)
    lifecycle_states: list[LifecycleState] = field(default_factory=list)
    time_start: datetime | None = None
    time_end: datetime | None = None

    def __post_init__(self) -> None:
        if self.time_start is not None and self.time_end is not None and self.time_end < self.time_start:
            raise MemoryEventValidationError("selector.time_end cannot be earlier than time_start")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.event_ids:
            data["event_ids"] = list(self.event_ids)
        if self.app is not None:
            data["app"] = self.app
        if self.entities:
            data["entities"] = list(self.entities)
        if self.topics:
            data["topics"] = list(self.topics)
        if self.memory_layers:
            data["memory_layers"] = [item.value for item in self.memory_layers]
        if self.privacy_levels:
            data["privacy_levels"] = [item.value for item in self.privacy_levels]
        if self.lifecycle_states:
            data["lifecycle_states"] = [item.value for item in self.lifecycle_states]
        if self.time_start is not None:
            data["time_start"] = self.time_start.isoformat()
        if self.time_end is not None:
            data["time_end"] = self.time_end.isoformat()
        return data


@dataclass(frozen=True)
class AuditRecord:
    operation_id: str
    caller: str
    operation: AuditOperation
    scope: dict[str, Any]
    affected_event_ids: list[str]
    occurred_at: datetime
    outcome: str
    denial_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.operation_id.strip():
            raise MemoryEventValidationError("operation_id is required")
        if not self.caller.strip():
            raise MemoryEventValidationError("audit caller is required")
        if self.outcome not in {"allowed", "denied"}:
            raise MemoryEventValidationError("audit outcome must be allowed or denied")
        if self.outcome == "denied" and not self.denial_reason:
            raise MemoryEventValidationError("denied audit records require denial_reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "caller": self.caller,
            "operation": self.operation.value,
            "scope": dict(self.scope),
            "affected_event_ids": list(self.affected_event_ids),
            "occurred_at": self.occurred_at.isoformat(),
            "outcome": self.outcome,
            "denial_reason": self.denial_reason,
        }
```

Update `phone_mem/personal_memory_service/__init__.py` imports and `__all__` to include:

```python
    AuditOperation,
    AuditRecord,
    MemorySelector,
```

- [x] **Step 4: Run focused tests to verify they pass**

Run:

```bash
uv run python -m unittest tests.test_event_models
```

Expected: `OK`.

- [x] **Step 5: Commit selector and audit value models**

Run:

```bash
git add phone_mem/personal_memory_service/__init__.py phone_mem/personal_memory_service/events.py tests/test_event_models.py docs/exec-plans/active/001-package-event-model.md
git commit -m "feat: add memory selector and audit models"
```

### Task 5: Memory Constructor

**Files:**
- Modify: `phone_mem/personal_memory_service/__init__.py`
- Create: `phone_mem/personal_memory_service/constructor.py`
- Create: `tests/test_memory_constructor.py`

- [x] **Step 1: Write constructor tests**

Create `tests/test_memory_constructor.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.personal_memory_service.constructor import MemoryCandidate, MemoryConstructor
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    EventType,
    LifecycleState,
    MemoryLayer,
    Modality,
    PrivacyLevel,
    ProcessingPolicy,
)


class MemoryConstructorTest(unittest.TestCase):
    def test_constructs_user_stated_text_memory(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        constructor = MemoryConstructor(clock=lambda: now, id_factory=lambda: "event-1")
        candidate = MemoryCandidate(
            semantic_description="  User prefers morning planning sessions.  ",
            source_app="system_assistant",
            actor=Actor.USER,
            modality=[Modality.TEXT],
            attribution=Attribution.USER_STATED,
            entities=["user", "planning"],
        )

        event = constructor.construct(candidate)

        self.assertEqual(event.event_id, "event-1")
        self.assertEqual(event.created_at, now)
        self.assertEqual(event.valid_time.start, now)
        self.assertEqual(event.event_type, EventType.USER_UTTERANCE)
        self.assertEqual(event.memory_layer, MemoryLayer.EPISODIC)
        self.assertEqual(event.semantic_description, "User prefers morning planning sessions.")
        self.assertEqual(event.privacy.level, PrivacyLevel.PERSONAL)
        self.assertEqual(event.privacy.processing_policy, ProcessingPolicy.CLIENT_ENCRYPTED_SYNC)
        self.assertEqual(event.lifecycle.state, LifecycleState.ACTIVE)

    def test_constructs_sensitive_memory_as_device_only(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        constructor = MemoryConstructor(clock=lambda: now, id_factory=lambda: "event-2")
        candidate = MemoryCandidate(
            semantic_description="User shared private health context.",
            source_app="system_assistant",
            actor=Actor.USER,
            modality=[Modality.TEXT],
            attribution=Attribution.USER_STATED,
            privacy_level=PrivacyLevel.SENSITIVE,
        )

        event = constructor.construct(candidate)

        self.assertEqual(event.privacy.level, PrivacyLevel.SENSITIVE)
        self.assertEqual(event.privacy.processing_policy, ProcessingPolicy.DEVICE_ONLY)

    def test_blank_candidate_description_is_rejected(self) -> None:
        constructor = MemoryConstructor(clock=lambda: datetime(2026, 5, 1, 9, 0, tzinfo=UTC))
        candidate = MemoryCandidate(
            semantic_description=" ",
            source_app="system_assistant",
            actor=Actor.USER,
            modality=[Modality.TEXT],
            attribution=Attribution.USER_STATED,
        )

        with self.assertRaisesRegex(ValueError, "semantic_description is required"):
            constructor.construct(candidate)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run constructor tests to verify they fail**

Run:

```bash
uv run python -m unittest tests.test_memory_constructor
```

Expected: import failure for `phone_mem.personal_memory_service.constructor`.

- [x] **Step 3: Implement deterministic constructor**

Create `phone_mem/personal_memory_service/constructor.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    EventSource,
    EventType,
    Lifecycle,
    Lineage,
    MemoryEvent,
    MemoryEventValidationError,
    MemoryLayer,
    Modality,
    Privacy,
    PrivacyLevel,
    ProcessingPolicy,
    Quality,
    ValidTime,
)


@dataclass(frozen=True)
class MemoryCandidate:
    semantic_description: str
    source_app: str
    actor: Actor
    modality: list[Modality]
    attribution: Attribution
    event_type: EventType | None = None
    memory_layer: MemoryLayer | None = None
    entities: list[str] = field(default_factory=list)
    relations: list[dict[str, object]] = field(default_factory=list)
    privacy_level: PrivacyLevel | None = None
    allowed_scopes: list[str] = field(default_factory=list)
    confidence: float = 0.9
    importance: float = 0.5
    freshness_half_life_days: int = 30
    valid_at: datetime | None = None
    lineage: Lineage = field(default_factory=Lineage)


class MemoryConstructor:
    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def construct(self, candidate: MemoryCandidate) -> MemoryEvent:
        description = candidate.semantic_description.strip()
        if not description:
            raise MemoryEventValidationError("semantic_description is required")
        if not candidate.source_app.strip():
            raise MemoryEventValidationError("source_app is required")

        created_at = self._clock()
        valid_at = candidate.valid_at or created_at
        privacy_level = candidate.privacy_level or self._default_privacy_level(candidate)

        return MemoryEvent(
            event_id=self._id_factory(),
            created_at=created_at,
            valid_time=ValidTime(start=valid_at),
            event_type=candidate.event_type or self._default_event_type(candidate),
            memory_layer=candidate.memory_layer or self._default_memory_layer(candidate),
            semantic_description=description,
            entities=self._normalize_strings(candidate.entities),
            relations=list(candidate.relations),
            source=EventSource(
                app=candidate.source_app.strip(),
                actor=candidate.actor,
                modality=list(candidate.modality),
                attribution=candidate.attribution,
            ),
            privacy=Privacy(
                level=privacy_level,
                allowed_scopes=self._allowed_scopes(candidate, privacy_level),
                processing_policy=self._default_processing_policy(privacy_level),
            ),
            quality=Quality(
                confidence=candidate.confidence,
                importance=candidate.importance,
                freshness_half_life_days=candidate.freshness_half_life_days,
            ),
            lineage=candidate.lineage,
            lifecycle=Lifecycle(),
        )

    def _default_event_type(self, candidate: MemoryCandidate) -> EventType:
        if Modality.APP_EVENT in candidate.modality:
            return EventType.APP_ACTION
        return EventType.USER_UTTERANCE

    def _default_memory_layer(self, candidate: MemoryCandidate) -> MemoryLayer:
        if candidate.attribution == Attribution.DERIVED:
            return MemoryLayer.SEMANTIC
        return MemoryLayer.EPISODIC

    def _default_privacy_level(self, candidate: MemoryCandidate) -> PrivacyLevel:
        if candidate.attribution == Attribution.APP_SYNCED:
            return PrivacyLevel.PERSONAL
        return PrivacyLevel.PERSONAL

    def _default_processing_policy(self, privacy_level: PrivacyLevel) -> ProcessingPolicy:
        if privacy_level == PrivacyLevel.SENSITIVE:
            return ProcessingPolicy.DEVICE_ONLY
        if privacy_level == PrivacyLevel.PUBLIC:
            return ProcessingPolicy.CLOUD_INDEXABLE
        return ProcessingPolicy.CLIENT_ENCRYPTED_SYNC

    def _allowed_scopes(self, candidate: MemoryCandidate, privacy_level: PrivacyLevel) -> list[str]:
        scopes = self._normalize_strings(candidate.allowed_scopes)
        if scopes:
            return scopes
        if privacy_level == PrivacyLevel.SENSITIVE:
            return [candidate.source_app.strip()]
        return [candidate.source_app.strip()]

    def _normalize_strings(self, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            stripped = value.strip()
            if stripped and stripped not in normalized:
                normalized.append(stripped)
        return normalized
```

Update `phone_mem/personal_memory_service/__init__.py` imports and `__all__` to include:

```python
from phone_mem.personal_memory_service.constructor import MemoryCandidate, MemoryConstructor
```

and:

```python
    "MemoryCandidate",
    "MemoryConstructor",
```

- [x] **Step 4: Run constructor tests to verify they pass**

Run:

```bash
uv run python -m unittest tests.test_memory_constructor
```

Expected: `OK`.

- [x] **Step 5: Run event model tests to catch export regressions**

Run:

```bash
uv run python -m unittest tests.test_event_models
```

Expected: `OK`.

- [x] **Step 6: Commit memory constructor**

Run:

```bash
git add phone_mem/personal_memory_service/__init__.py phone_mem/personal_memory_service/constructor.py tests/test_memory_constructor.py docs/exec-plans/active/001-package-event-model.md
git commit -m "feat: add deterministic memory constructor"
```

### Task 6: Full Stage 001 Verification

**Files:**
- Modify: `docs/exec-plans/active/001-package-event-model.md`

- [ ] **Step 1: Run the full unit test suite**

Run:

```bash
uv run python -m unittest discover -s tests
```

Expected: all tests pass, including `tests.test_docs_validation`, `tests.test_event_models`, and `tests.test_memory_constructor`.

- [ ] **Step 2: Run documentation validation**

Run:

```bash
uv run python scripts/validate_docs.py
```

Expected: `Documentation validation passed.`

- [ ] **Step 3: Review implementation against Stage 001 acceptance**

Confirm these outcomes before closing 001:

- `MemoryEvent.to_dict()` preserves event ID, created time, valid time, event type, memory layer, source attribution, privacy policy, quality metadata, lineage, and lifecycle state.
- Invalid event input fails with `MemoryEventValidationError` and a concrete message.
- Sensitive memory cannot use non-device-only processing.
- Event construction has no import from `sqlite3`, retrieval, context assembly, runtime adapters, or model providers.
- `main.py` remains a placeholder.

- [ ] **Step 4: Commit final plan checkbox updates**

Run:

```bash
git add docs/exec-plans/active/001-package-event-model.md
git commit -m "docs: track package event model execution"
```

## Validation

- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`

## Acceptance

- A canonical memory event can be created from structured input.
- Invalid event input fails with a clear error.
- Event models preserve event IDs, source attribution, privacy policy, quality metadata, lineage, and lifecycle state.
- Constructor code has no dependency on SQLite, retrieval, context assembly, model runtimes, cloud sync, or mobile platform APIs.
- Sensitive memory defaults to device-only processing.
- Constructor normalization trims user-facing text and deduplicates entity/scope strings.
- Selectors and audit-related value models exist for later storage, governance, and retrieval plans.

## Self-Review

- Spec coverage: The plan covers the package skeleton, canonical event model, constructor normalization hooks, validation behavior, lifecycle state transition helper, selectors, audit-related value models, and tests required by the Stage 001 scope.
- Placeholder scan: The plan contains no unresolved placeholders or unspecified implementation steps.
- Type consistency: The same names are used across tests and implementation snippets: `MemoryEvent`, `MemoryCandidate`, `MemoryConstructor`, `MemorySelector`, `AuditRecord`, `Lifecycle.mark_deleted`, and `MemoryEventValidationError`.
