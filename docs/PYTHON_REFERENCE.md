# Python Reference Guide

This guide is the practical entrypoint for using and iterating on the current Python Personal Memory Service before returning to mobile runtime work.

## What Exists

The Python reference implements a local-only memory service under `phone_mem/`:

- `personal_memory_service.constructor`: builds canonical events from structured candidates.
- `personal_memory_service.service`: service facade for record, search, explain, correct, delete, grant, revoke, audit, build context, and metrics.
- `personal_memory_service.storage`: SQLite-backed event, permission, audit, and tombstone persistence.
- `personal_memory_service.lifecycle`: duplicate detection and simple contradiction quarantine.
- `personal_memory_service.retrieval`: governed lexical retrieval after permission projection.
- `context`: runtime-neutral context bundle assembly and budget accounting.
- `governance`: permission grants, audit records, and memory views.

The reference version is intentionally deterministic. It is the executable oracle for future mobile behavior, not the final phone runtime.

## Quick Walkthrough

Run the lifecycle walkthrough:

```bash
uv run python examples/python_reference_walkthrough.py
```

The walkthrough demonstrates:

1. grant a caller scoped access;
2. record a user-stated memory;
3. search with governed retrieval;
4. build a model-runtime-neutral context bundle;
5. delete the memory and write a tombstone;
6. inspect audit and metrics outputs.

The same flow is covered by:

```bash
uv run python -m unittest tests.test_python_reference_walkthrough
```

## File-Backed SQLite Walkthrough

Run the file-backed walkthrough with a temporary SQLite file:

```bash
uv run python examples/file_backed_sqlite_walkthrough.py
```

Or reuse a specific local database across runs:

```bash
uv run python examples/file_backed_sqlite_walkthrough.py memory-dev.sqlite3
```

The walkthrough opens the same SQLite file three times:

1. initialize schema, grant a caller, and record one memory;
2. reopen the file and confirm search, audit, and tombstone queries see persisted state;
3. delete the memory, reopen again, and confirm search excludes the deleted event while tombstone and audit records remain.

It uses `SQLiteMemoryStore.connect(path)` plus `PersonalMemoryService.from_store(store)`, so the service orchestration stays reusable while file path ownership remains outside the service facade.

The same flow is covered by:

```bash
uv run python -m unittest tests.test_file_backed_sqlite_walkthrough
```

## Minimal Service Usage

```python
from datetime import UTC, datetime

from phone_mem.context.budgets import ContextBudget
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    AuditOperation,
    MemoryLayer,
    Modality,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService

now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
service = PersonalMemoryService.in_memory(clock=lambda: now)

service.grant(
    "calendar_agent",
    PermissionScope(
        operations=[
            AuditOperation.WRITE,
            AuditOperation.READ,
            AuditOperation.DELETE,
            AuditOperation.CONTEXT_BUILD,
        ],
        apps=["system_assistant"],
        privacy_levels=[PrivacyLevel.PERSONAL],
        memory_layers=[MemoryLayer.EPISODIC],
    ),
    duration_seconds=60,
)

event_id = service.record(
    MemoryCandidate(
        semantic_description="User prefers morning planning sessions.",
        source_app="system_assistant",
        actor=Actor.USER,
        modality=[Modality.TEXT],
        attribution=Attribution.USER_STATED,
        entities=["planning"],
    ),
    caller="calendar_agent",
)

results = service.search("morning planning", caller="calendar_agent")
bundle = service.build_context(
    "morning planning",
    caller="calendar_agent",
    task={"id": "task-1"},
    budget=ContextBudget(max_tokens=80, safety_reserve_tokens=10, output_reserve_tokens=20),
)

service.delete_by_event_id(event_id, caller="calendar_agent", reason="user requested deletion")
service.close()
```

## File-Backed Service Usage

```python
from phone_mem.personal_memory_service.service import PersonalMemoryService
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore

store = SQLiteMemoryStore.connect("memory-dev.sqlite3")
store.initialize_schema()
service = PersonalMemoryService.from_store(store)

try:
    ...
finally:
    service.close()
```

## Service Error Contracts

Service methods raise domain-specific exceptions for caller-visible failures while preserving Python compatibility with built-in exception families:

- `MemoryPermissionDenied` subclasses `PermissionError`.
- `MemoryEventNotFound` subclasses `KeyError`.

Both expose structured context so callers and future mobile contract tests do not need to parse message strings:

```python
from phone_mem.personal_memory_service.errors import (
    MemoryEventNotFound,
    MemoryPermissionDenied,
)

try:
    service.explain("event-123", caller="calendar_agent")
except MemoryPermissionDenied as error:
    print(error.operation, error.caller, error.denial_reason)
except MemoryEventNotFound as error:
    print(error.operation, error.caller, error.event_id)
```

Permission denials include the attempted operation, caller, affected event IDs when known, selector context when relevant, and the denial reason that is also written to audit. Missing event reads and updates also write denied audit records with `memory event not found`.

## Iteration Priorities

Focus Python maturation work on behavior that improves the reference oracle:

- richer examples and usage notes;
- clearer error types and service API ergonomics;
- persistent file-backed SQLite usage examples;
- stronger lifecycle rules for correction, contradiction, rejection, and quarantine;
- better retrieval scoring and query selectors while preserving permission-before-ranking;
- fixture generation for cross-runtime contracts only after Python behavior stabilizes;
- tests for every behavior change.

Do not resume mobile implementation until the Python API feels stable enough to mirror.
