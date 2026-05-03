# 002 Storage Audit And Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist canonical memory events in local SQLite and enforce the first permission, memory view, tombstone, and audit invariants.

**Architecture:** Storage remains an infrastructure adapter under `personal_memory_service/storage.py`; governance policy remains separate under `governance/permissions.py`, `governance/views.py`, and `governance/audit.py`. Reads for later retrieval must go through permission projection before any ranking layer exists, so this plan proves authorized event selection without implementing retrieval scoring.

**Tech Stack:** Python 3.13 standard library, `sqlite3`, `json`, `dataclasses`, `datetime`, `uuid`, and `unittest`.

Status: active
Type: execution

---

## Goal

Persist local memory events in SQLite and enforce the first permission, memory view, tombstone, and audit invariants.

This subplan belongs to Stage 1: the Python reference implementation. SQLite is used to prove local service behavior, not to define the final mobile runtime storage boundary.

## Scope

- SQLite schema for canonical events, entities, event-entity links, permissions, tombstones, and audit records.
- Repository/storage interface for event create, read, lifecycle update, selector query, tombstone write, permission persistence, and audit persistence.
- Grant and revoke operations for scoped permissions.
- Memory view projection before retrieval.
- Audit writer for reads, writes, permission changes, corrections, deletes, and denied decisions.
- Deterministic unit tests using in-memory SQLite.

## Design Inputs

- [Personal Memory Service](../../design-docs/personal-memory-service.md)
- [Governance, Permissions, And Audit](../../design-docs/governance-permissions-audit.md)
- [Memory Lifecycle And Data Flow](../../design-docs/memory-lifecycle-and-data-flow.md)
- [Security](../../SECURITY.md)

## Out Of Scope

- Full retrieval ranking.
- Context bundle construction.
- Cloud sync.
- Graph or vector stores.
- Production encryption.
- Runtime adapters and SDK facade.
- Deduplication and contradiction detection; those remain lifecycle/service work for 004 unless needed by tests here.

## File Structure

- Create `phone_mem/personal_memory_service/storage.py`: SQLite schema bootstrap, event JSON persistence, event rehydration, selector queries, lifecycle updates, tombstones, grants, and audit rows.
- Create `phone_mem/governance/__init__.py`: governance package exports.
- Create `phone_mem/governance/permissions.py`: `PermissionGrant`, `PermissionScope`, `PermissionDecision`, and `PermissionService`.
- Create `phone_mem/governance/views.py`: `MemoryViewProjector` that filters events through permission decisions before retrieval.
- Create `phone_mem/governance/audit.py`: `AuditLog` wrapper that writes and queries `AuditRecord` values through storage.
- Modify `phone_mem/personal_memory_service/__init__.py`: export `SQLiteMemoryStore` only if doing so does not create import cycles.
- Create `tests/test_storage.py`: schema, event persistence, selector query, lifecycle, and tombstone tests.
- Create `tests/test_governance.py`: permission grant/revoke/expiry, memory view, and audit tests.
- Modify `docs/exec-plans/active/002-storage-audit-governance.md`: mark checkboxes as steps are completed.

## Public API Target

The implementation should expose these stable names:

```python
class SQLiteMemoryStore:
    @classmethod
    def connect(cls, path: str = ":memory:") -> "SQLiteMemoryStore": pass
    def initialize_schema(self) -> None: pass
    def insert_event(self, event: MemoryEvent) -> None: pass
    def get_event(self, event_id: str) -> MemoryEvent | None: pass
    def query_events(self, selector: MemorySelector | None = None) -> list[MemoryEvent]: pass
    def update_lifecycle(self, event_id: str, lifecycle: Lifecycle) -> None: pass
    def write_tombstone(self, tombstone: TombstoneRecord) -> None: pass
    def list_tombstones(self) -> list[TombstoneRecord]: pass
    def insert_permission_grant(self, grant: PermissionGrant) -> None: pass
    def update_permission_grant(self, grant: PermissionGrant) -> None: pass
    def list_permission_grants(self, caller: str | None = None) -> list[PermissionGrant]: pass
    def insert_audit_record(self, record: AuditRecord) -> None: pass
    def query_audit_records(self, selector: AuditSelector | None = None) -> list[AuditRecord]: pass
```

```python
class PermissionService:
    def grant(self, caller: str, scope: PermissionScope, duration_seconds: int) -> PermissionGrant: pass
    def revoke(self, grant_id: str) -> None: pass
    def can_access(self, caller: str, operation: AuditOperation, event: MemoryEvent, *, at: datetime | None = None) -> PermissionDecision: pass
```

```python
class MemoryViewProjector:
    def project(self, caller: str, operation: AuditOperation, events: list[MemoryEvent], *, at: datetime | None = None) -> MemoryView: pass
```

```python
class AuditLog:
    def record(self, caller: str, operation: AuditOperation, scope: dict[str, object], affected_event_ids: list[str], outcome: str, denial_reason: str | None = None) -> AuditRecord: pass
    def query(self, selector: AuditSelector | None = None) -> list[AuditRecord]: pass
```

## Steps

### Task 1: SQLite Schema Bootstrap

**Files:**
- Create: `phone_mem/personal_memory_service/storage.py`
- Test: `tests/test_storage.py`

- [x] **Step 1: Write failing schema test**

Create `tests/test_storage.py`:

```python
from __future__ import annotations

import sqlite3
import unittest

from phone_mem.personal_memory_service.storage import SQLiteMemoryStore


class SQLiteSchemaTest(unittest.TestCase):
    def test_initialize_schema_creates_mvp_tables(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()

        table_names = {
            row[0]
            for row in store.connection.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

        self.assertIn("memory_events", table_names)
        self.assertIn("entities", table_names)
        self.assertIn("event_entities", table_names)
        self.assertIn("permissions", table_names)
        self.assertIn("audit_log", table_names)
        self.assertIn("tombstones", table_names)

    def test_connection_uses_row_factory(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")

        self.assertIs(store.connection.row_factory, sqlite3.Row)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run schema test to verify it fails**

Run:

```bash
uv run python -m unittest tests.test_storage.SQLiteSchemaTest
```

Expected: import failure for `phone_mem.personal_memory_service.storage`.

- [x] **Step 3: Implement schema bootstrap**

Create `phone_mem/personal_memory_service/storage.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import sqlite3
from typing import Any

from phone_mem.personal_memory_service.events import MemoryEvent


class StorageError(RuntimeError):
    """Raised when persisted memory state is invalid."""


@dataclass(frozen=True)
class SQLiteMemoryStore:
    connection: sqlite3.Connection

    @classmethod
    def connect(cls, path: str = ":memory:") -> SQLiteMemoryStore:
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        return cls(connection=connection)

    def initialize_schema(self) -> None:
        self.connection.executescript(
            """
            create table if not exists memory_events (
                event_id text primary key,
                created_at text not null,
                valid_start text not null,
                valid_end text,
                event_type text not null,
                memory_layer text not null,
                semantic_description text not null,
                source_app text not null,
                privacy_level text not null,
                processing_policy text not null,
                lifecycle_state text not null,
                event_json text not null
            );

            create table if not exists entities (
                entity text primary key
            );

            create table if not exists event_entities (
                event_id text not null,
                entity text not null,
                primary key (event_id, entity),
                foreign key (event_id) references memory_events(event_id)
            );

            create table if not exists permissions (
                grant_id text primary key,
                caller text not null,
                operation text not null,
                scope_json text not null,
                granted_at text not null,
                expires_at text not null,
                revoked_at text
            );

            create table if not exists audit_log (
                operation_id text primary key,
                caller text not null,
                operation text not null,
                scope_json text not null,
                affected_event_ids_json text not null,
                occurred_at text not null,
                outcome text not null,
                denial_reason text
            );

            create table if not exists tombstones (
                tombstone_id text primary key,
                event_id text not null,
                deleted_at text not null,
                reason text not null,
                selector_json text not null
            );
            """
        )
        self.connection.commit()
```

- [x] **Step 4: Run schema test to verify it passes**

Run:

```bash
uv run python -m unittest tests.test_storage.SQLiteSchemaTest
```

Expected: `OK`.

- [x] **Step 5: Commit schema bootstrap**

Run:

```bash
git add phone_mem/personal_memory_service/storage.py tests/test_storage.py docs/exec-plans/active/002-storage-audit-governance.md
git commit -m "feat: add SQLite memory schema bootstrap"
```

### Task 2: Event Persistence And Selector Query

**Files:**
- Modify: `phone_mem/personal_memory_service/storage.py`
- Modify: `tests/test_storage.py`

- [x] **Step 1: Add event persistence tests**

Append to `tests/test_storage.py`:

```python
from datetime import UTC, datetime

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
    MemorySelector,
    Modality,
    Privacy,
    PrivacyLevel,
    ProcessingPolicy,
    Quality,
    ValidTime,
)


def make_event(event_id: str, *, app: str = "system_assistant", entity: str = "user") -> MemoryEvent:
    created_at = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
    return MemoryEvent(
        event_id=event_id,
        created_at=created_at,
        valid_time=ValidTime(start=created_at),
        event_type=EventType.USER_UTTERANCE,
        memory_layer=MemoryLayer.EPISODIC,
        semantic_description=f"{entity} prefers morning planning sessions.",
        entities=[entity],
        relations=[],
        source=EventSource(
            app=app,
            actor=Actor.USER,
            modality=[Modality.TEXT],
            attribution=Attribution.USER_STATED,
        ),
        privacy=Privacy(
            level=PrivacyLevel.PERSONAL,
            allowed_scopes=[app],
            processing_policy=ProcessingPolicy.CLIENT_ENCRYPTED_SYNC,
        ),
        quality=Quality(confidence=0.95, importance=0.7, freshness_half_life_days=30),
        lineage=Lineage(),
        lifecycle=Lifecycle(),
    )


class SQLiteEventPersistenceTest(unittest.TestCase):
    def test_insert_and_get_event_round_trips_canonical_data(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        event = make_event("event-1")

        store.insert_event(event)

        loaded = store.get_event("event-1")
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.event_id, "event-1")
        self.assertEqual(loaded.source.app, "system_assistant")
        self.assertEqual(loaded.privacy.level, PrivacyLevel.PERSONAL)
        self.assertEqual(loaded.entities, ["user"])

    def test_query_events_applies_selector_filters(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        store.insert_event(make_event("event-1", app="system_assistant", entity="user"))
        store.insert_event(make_event("event-2", app="calendar", entity="calendar"))

        results = store.query_events(
            MemorySelector(
                app="system_assistant",
                entities=["user"],
                memory_layers=[MemoryLayer.EPISODIC],
                privacy_levels=[PrivacyLevel.PERSONAL],
                lifecycle_states=[LifecycleState.ACTIVE],
            )
        )

        self.assertEqual([event.event_id for event in results], ["event-1"])
```

- [x] **Step 2: Run event persistence tests to verify they fail**

Run:

```bash
uv run python -m unittest tests.test_storage.SQLiteEventPersistenceTest
```

Expected: `AttributeError` for `insert_event` or `get_event`.

- [x] **Step 3: Implement event persistence and rehydration**

Update `SQLiteMemoryStore` with these methods:

```python
    def insert_event(self, event: MemoryEvent) -> None:
        data = event.to_dict()
        self.connection.execute(
            """
            insert into memory_events (
                event_id, created_at, valid_start, valid_end, event_type,
                memory_layer, semantic_description, source_app, privacy_level,
                processing_policy, lifecycle_state, event_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.created_at.isoformat(),
                event.valid_time.start.isoformat(),
                event.valid_time.end.isoformat() if event.valid_time.end else None,
                event.event_type.value,
                event.memory_layer.value,
                event.semantic_description,
                event.source.app,
                event.privacy.level.value,
                event.privacy.processing_policy.value,
                event.lifecycle.state.value,
                json.dumps(data, sort_keys=True),
            ),
        )
        for entity in event.entities:
            self.connection.execute("insert or ignore into entities(entity) values (?)", (entity,))
            self.connection.execute(
                "insert or ignore into event_entities(event_id, entity) values (?, ?)",
                (event.event_id, entity),
            )
        self.connection.commit()

    def get_event(self, event_id: str) -> MemoryEvent | None:
        row = self.connection.execute(
            "select event_json from memory_events where event_id = ?",
            (event_id,),
        ).fetchone()
        if row is None:
            return None
        return self._event_from_dict(json.loads(row["event_json"]))

    def query_events(self, selector: MemorySelector | None = None) -> list[MemoryEvent]:
        selector = selector or MemorySelector()
        sql = ["select distinct e.event_json from memory_events e"]
        params: list[str] = []
        if selector.entities:
            sql.append("join event_entities ee on ee.event_id = e.event_id")
        where: list[str] = []
        if selector.event_ids:
            where.append(f"e.event_id in ({','.join('?' for _ in selector.event_ids)})")
            params.extend(selector.event_ids)
        if selector.app is not None:
            where.append("e.source_app = ?")
            params.append(selector.app)
        if selector.entities:
            where.append(f"ee.entity in ({','.join('?' for _ in selector.entities)})")
            params.extend(selector.entities)
        if selector.memory_layers:
            where.append(f"e.memory_layer in ({','.join('?' for _ in selector.memory_layers)})")
            params.extend(item.value for item in selector.memory_layers)
        if selector.privacy_levels:
            where.append(f"e.privacy_level in ({','.join('?' for _ in selector.privacy_levels)})")
            params.extend(item.value for item in selector.privacy_levels)
        if selector.lifecycle_states:
            where.append(f"e.lifecycle_state in ({','.join('?' for _ in selector.lifecycle_states)})")
            params.extend(item.value for item in selector.lifecycle_states)
        if selector.time_start is not None:
            where.append("e.valid_start >= ?")
            params.append(selector.time_start.isoformat())
        if selector.time_end is not None:
            where.append("e.valid_start <= ?")
            params.append(selector.time_end.isoformat())
        if where:
            sql.append("where " + " and ".join(where))
        sql.append("order by e.created_at, e.event_id")
        rows = self.connection.execute(" ".join(sql), params).fetchall()
        return [self._event_from_dict(json.loads(row["event_json"])) for row in rows]
```

Also import the event value objects needed by `_event_from_dict` and implement `_event_from_dict` by reconstructing `MemoryEvent` from the canonical dictionary produced by `MemoryEvent.to_dict()`.

- [x] **Step 4: Run event persistence tests to verify they pass**

Run:

```bash
uv run python -m unittest tests.test_storage.SQLiteEventPersistenceTest
```

Expected: `OK`.

- [x] **Step 5: Commit event persistence**

Run:

```bash
git add phone_mem/personal_memory_service/storage.py tests/test_storage.py docs/exec-plans/active/002-storage-audit-governance.md
git commit -m "feat: persist canonical memory events"
```

### Task 3: Lifecycle Updates And Tombstones

**Files:**
- Modify: `phone_mem/personal_memory_service/storage.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Add lifecycle and tombstone tests**

Append to `tests/test_storage.py`:

```python
from phone_mem.personal_memory_service.storage import TombstoneRecord


class SQLiteLifecycleAndTombstoneTest(unittest.TestCase):
    def test_update_lifecycle_hides_deleted_event_from_active_selector(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        event = make_event("event-1")
        store.insert_event(event)
        deleted_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)

        store.update_lifecycle(
            "event-1",
            Lifecycle().mark_deleted(deleted_at=deleted_at, reason="user requested deletion"),
        )

        active = store.query_events(MemorySelector(lifecycle_states=[LifecycleState.ACTIVE]))
        deleted = store.get_event("event-1")
        self.assertEqual(active, [])
        self.assertIsNotNone(deleted)
        assert deleted is not None
        self.assertEqual(deleted.lifecycle.state, LifecycleState.DELETED)

    def test_write_tombstone_records_deleted_event_and_selector(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        deleted_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
        tombstone = TombstoneRecord(
            tombstone_id="tombstone-1",
            event_id="event-1",
            deleted_at=deleted_at,
            reason="user requested deletion",
            selector=MemorySelector(event_ids=["event-1"]),
        )

        store.write_tombstone(tombstone)

        self.assertEqual(store.list_tombstones(), [tombstone])
```

- [ ] **Step 2: Run lifecycle tests to verify they fail**

Run:

```bash
uv run python -m unittest tests.test_storage.SQLiteLifecycleAndTombstoneTest
```

Expected: import or attribute failure for `TombstoneRecord`.

- [ ] **Step 3: Implement lifecycle and tombstones**

Add immutable `TombstoneRecord` to `storage.py` and implement:

```python
@dataclass(frozen=True)
class TombstoneRecord:
    tombstone_id: str
    event_id: str
    deleted_at: datetime
    reason: str
    selector: MemorySelector
```

`update_lifecycle` must update both lifecycle columns and the stored canonical `event_json`. `write_tombstone` and `list_tombstones` must persist and rehydrate `TombstoneRecord` using `selector.to_dict()`.

- [ ] **Step 4: Run lifecycle tests to verify they pass**

Run:

```bash
uv run python -m unittest tests.test_storage.SQLiteLifecycleAndTombstoneTest
```

Expected: `OK`.

- [ ] **Step 5: Commit lifecycle and tombstones**

Run:

```bash
git add phone_mem/personal_memory_service/storage.py tests/test_storage.py docs/exec-plans/active/002-storage-audit-governance.md
git commit -m "feat: add lifecycle updates and tombstones"
```

### Task 4: Permission Grants And Scope Matching

**Files:**
- Create: `phone_mem/governance/__init__.py`
- Create: `phone_mem/governance/permissions.py`
- Modify: `phone_mem/personal_memory_service/storage.py`
- Create: `tests/test_governance.py`

- [ ] **Step 1: Write permission service tests**

Create `tests/test_governance.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.governance.permissions import PermissionScope, PermissionService
from phone_mem.personal_memory_service.events import AuditOperation, MemoryLayer, PrivacyLevel
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore
from tests.test_storage import make_event


class PermissionServiceTest(unittest.TestCase):
    def test_grant_allows_matching_event_until_expiry(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        service = PermissionService(store, clock=lambda: now, id_factory=lambda: "grant-1")
        event = make_event("event-1")

        grant = service.grant(
            "calendar_agent",
            PermissionScope(
                operations=[AuditOperation.READ],
                memory_layers=[MemoryLayer.EPISODIC],
                privacy_levels=[PrivacyLevel.PERSONAL],
                apps=["system_assistant"],
                entities=["user"],
            ),
            duration_seconds=60,
        )

        decision = service.can_access("calendar_agent", AuditOperation.READ, event, at=now)
        self.assertTrue(decision.allowed)
        self.assertEqual(grant.grant_id, "grant-1")

    def test_expired_grant_denies_matching_event(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        service = PermissionService(store, clock=lambda: now, id_factory=lambda: "grant-1")
        event = make_event("event-1")
        service.grant(
            "calendar_agent",
            PermissionScope(operations=[AuditOperation.READ]),
            duration_seconds=1,
        )

        later = datetime(2026, 5, 1, 9, 1, tzinfo=UTC)
        decision = service.can_access("calendar_agent", AuditOperation.READ, event, at=later)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "no active grant matched")

    def test_revoked_grant_denies_access(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        service = PermissionService(store, clock=lambda: now, id_factory=lambda: "grant-1")
        event = make_event("event-1")
        service.grant("calendar_agent", PermissionScope(operations=[AuditOperation.READ]), 60)

        service.revoke("grant-1")

        decision = service.can_access("calendar_agent", AuditOperation.READ, event, at=now)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "no active grant matched")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run permission tests to verify they fail**

Run:

```bash
uv run python -m unittest tests.test_governance.PermissionServiceTest
```

Expected: import failure for `phone_mem.governance.permissions`.

- [ ] **Step 3: Implement permission models and service**

Implement in `phone_mem/governance/permissions.py`:

```python
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

@dataclass(frozen=True)
class PermissionGrant:
    grant_id: str
    caller: str
    scope: PermissionScope
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None

@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str | None = None
    grant_id: str | None = None
```

`PermissionService.grant` persists a grant through `SQLiteMemoryStore.insert_permission_grant`. `can_access` loads caller grants, ignores expired/revoked grants, checks operation, layer, privacy, app, entity intersection, event valid time, and processing policy. Empty scope lists mean "not constrained" for that dimension.

- [ ] **Step 4: Run permission tests to verify they pass**

Run:

```bash
uv run python -m unittest tests.test_governance.PermissionServiceTest
```

Expected: `OK`.

- [ ] **Step 5: Commit permission service**

Run:

```bash
git add phone_mem/governance/__init__.py phone_mem/governance/permissions.py phone_mem/personal_memory_service/storage.py tests/test_governance.py docs/exec-plans/active/002-storage-audit-governance.md
git commit -m "feat: add scoped permission grants"
```

### Task 5: Memory View Projection

**Files:**
- Create: `phone_mem/governance/views.py`
- Modify: `phone_mem/governance/__init__.py`
- Modify: `tests/test_governance.py`

- [ ] **Step 1: Add memory view tests**

Append to `tests/test_governance.py`:

```python
from phone_mem.governance.views import MemoryViewProjector


class MemoryViewProjectorTest(unittest.TestCase):
    def test_project_returns_only_authorized_events_and_denials(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        permissions = PermissionService(store, clock=lambda: now, id_factory=lambda: "grant-1")
        permissions.grant(
            "calendar_agent",
            PermissionScope(
                operations=[AuditOperation.READ],
                apps=["system_assistant"],
                entities=["user"],
            ),
            duration_seconds=60,
        )
        projector = MemoryViewProjector(permissions)

        authorized = make_event("event-1", app="system_assistant", entity="user")
        denied = make_event("event-2", app="health", entity="health")

        view = projector.project(
            "calendar_agent",
            AuditOperation.READ,
            [authorized, denied],
            at=now,
        )

        self.assertEqual([event.event_id for event in view.events], ["event-1"])
        self.assertEqual(view.denied_event_ids, {"event-2": "no active grant matched"})
```

- [ ] **Step 2: Run memory view tests to verify they fail**

Run:

```bash
uv run python -m unittest tests.test_governance.MemoryViewProjectorTest
```

Expected: import failure for `phone_mem.governance.views`.

- [ ] **Step 3: Implement memory view projection**

Implement in `phone_mem/governance/views.py`:

```python
@dataclass(frozen=True)
class MemoryView:
    events: list[MemoryEvent]
    denied_event_ids: dict[str, str]

class MemoryViewProjector:
    def __init__(self, permission_service: PermissionService) -> None: pass
    def project(self, caller: str, operation: AuditOperation, events: list[MemoryEvent], *, at: datetime | None = None) -> MemoryView: pass
```

The projector must call `PermissionService.can_access` for each event before returning any event to callers. Denied events are represented only by event ID and denial reason for tests and audit; later retrieval must not score denied memory.

- [ ] **Step 4: Run memory view tests to verify they pass**

Run:

```bash
uv run python -m unittest tests.test_governance.MemoryViewProjectorTest
```

Expected: `OK`.

- [ ] **Step 5: Commit memory view projection**

Run:

```bash
git add phone_mem/governance/__init__.py phone_mem/governance/views.py tests/test_governance.py docs/exec-plans/active/002-storage-audit-governance.md
git commit -m "feat: project permissioned memory views"
```

### Task 6: Audit Log Writer And Query

**Files:**
- Create: `phone_mem/governance/audit.py`
- Modify: `phone_mem/governance/__init__.py`
- Modify: `phone_mem/personal_memory_service/storage.py`
- Modify: `tests/test_governance.py`

- [ ] **Step 1: Add audit log tests**

Append to `tests/test_governance.py`:

```python
from phone_mem.governance.audit import AuditLog, AuditSelector


class AuditLogTest(unittest.TestCase):
    def test_record_persists_allowed_and_denied_audit_records(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        audit = AuditLog(store, clock=lambda: now, id_factory=lambda: "audit-1")

        record = audit.record(
            caller="calendar_agent",
            operation=AuditOperation.READ,
            scope={"app": "system_assistant"},
            affected_event_ids=["event-1"],
            outcome="allowed",
        )

        self.assertEqual(record.operation_id, "audit-1")
        self.assertEqual(audit.query()[0].operation, AuditOperation.READ)

    def test_query_filters_by_caller_and_operation(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        ids = iter(["audit-1", "audit-2"])
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        audit = AuditLog(store, clock=lambda: now, id_factory=lambda: next(ids))
        audit.record("calendar_agent", AuditOperation.READ, {}, ["event-1"], "allowed")
        audit.record("writer_agent", AuditOperation.WRITE, {}, ["event-2"], "allowed")

        records = audit.query(AuditSelector(caller="calendar_agent", operations=[AuditOperation.READ]))

        self.assertEqual([record.operation_id for record in records], ["audit-1"])
```

- [ ] **Step 2: Run audit tests to verify they fail**

Run:

```bash
uv run python -m unittest tests.test_governance.AuditLogTest
```

Expected: import failure for `phone_mem.governance.audit`.

- [ ] **Step 3: Implement audit log wrapper and storage methods**

Implement `AuditSelector` and `AuditLog` in `phone_mem/governance/audit.py`. Add `insert_audit_record` and `query_audit_records` to `SQLiteMemoryStore`. Persist `AuditRecord.scope` and `affected_event_ids` as JSON strings. Query filters should support caller and operations.

- [ ] **Step 4: Run audit tests to verify they pass**

Run:

```bash
uv run python -m unittest tests.test_governance.AuditLogTest
```

Expected: `OK`.

- [ ] **Step 5: Commit audit log**

Run:

```bash
git add phone_mem/governance/__init__.py phone_mem/governance/audit.py phone_mem/personal_memory_service/storage.py tests/test_governance.py docs/exec-plans/active/002-storage-audit-governance.md
git commit -m "feat: add audit log persistence"
```

### Task 7: Full Stage 002 Verification

**Files:**
- Modify: `docs/exec-plans/active/002-storage-audit-governance.md`

- [ ] **Step 1: Run focused Stage 002 tests**

Run:

```bash
uv run python -m unittest tests.test_storage tests.test_governance
```

Expected: all Stage 002 tests pass.

- [ ] **Step 2: Run full test suite**

Run:

```bash
uv run python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 3: Run documentation validation**

Run:

```bash
uv run python scripts/validate_docs.py
```

Expected: `Documentation validation passed.`

- [ ] **Step 4: Review implementation against Stage 002 acceptance**

Confirm these outcomes before closing 002:

- Events persist locally and can be read by ID.
- Selector queries can filter by event ID, app, entity, layer, privacy, lifecycle state, and time range.
- Unauthorized callers are denied by permission projection before retrieval exists.
- Grants are scoped, expiring, and revocable.
- Deletes can be represented by lifecycle state and tombstones.
- Audit records can be written and queried.
- No retrieval ranking, context assembly, cloud sync, graph/vector store, or production encryption was introduced.

- [ ] **Step 5: Commit final plan checkbox updates**

Run:

```bash
git add docs/exec-plans/active/002-storage-audit-governance.md
git commit -m "docs: track storage governance execution"
```

## Validation

- `uv run python -m unittest tests.test_storage tests.test_governance`
- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`

## Acceptance

- Events persist locally and can be read by ID.
- Permission checks deny unauthorized callers before retrieval work.
- Grants are scoped, expiring, and revocable.
- Deletes create tombstones.
- Reads, writes, permission changes, and deletes can create audit records.
- Storage and governance code introduce no model runtime, cloud sync, vector index, graph database, context assembly, or retrieval ranking dependency.

## Self-Review

- Spec coverage: The plan covers SQLite schema, event persistence, selector queries, lifecycle updates, tombstones, permission grants, revoke/expiry matching, memory view projection, audit writing/querying, and validation.
- Placeholder scan: The plan contains no unresolved placeholders or unspecified implementation steps.
- Type consistency: The same names are used across tests and implementation targets: `SQLiteMemoryStore`, `TombstoneRecord`, `PermissionScope`, `PermissionGrant`, `PermissionDecision`, `PermissionService`, `MemoryViewProjector`, `MemoryView`, `AuditLog`, and `AuditSelector`.
