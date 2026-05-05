# Python Reference Guide

This guide is the practical entrypoint for using and maintaining the completed Python Personal Memory Service reference.

## What Exists

The Python reference implements a local-only memory service under `phone_mem/`:

- `personal_memory_service.constructor`: builds canonical events from structured candidates.
- `personal_memory_service.service`: service facade for record, search, explain, correct, delete, grant, revoke, audit, build context, and metrics.
- `personal_memory_service.storage`: SQLite-backed event, permission, audit, and tombstone persistence.
- `personal_memory_service.lifecycle`: duplicate detection and simple contradiction quarantine.
- `personal_memory_service.retrieval`: governed lexical retrieval after permission projection.
- `context`: runtime-neutral context bundle assembly and budget accounting.
- `governance`: permission grants, audit records, and memory views.

The reference version is intentionally deterministic. It is the executable oracle for future mobile behavior, not the final phone runtime. The active Stage 1.5 plan adds a separate Python LLM Agent runtime around this service so real provider-backed demos can be built without making the memory core depend on a model provider.

## Product-Style Demo

Run the product-style memory Agent demo:

```bash
uv run python examples/agent_memory_demo.py
```

The demo prints a readable story for the current reference behavior:

1. grant a planner Agent scoped memory access;
2. record a user planning preference;
3. retrieve that memory for a later planning task;
4. build a context bundle from the retrieved memory;
5. correct the memory and explain the lifecycle transition;
6. delete the corrected memory and confirm later retrieval returns nothing.

The same flow is covered by:

```bash
uv run python -m unittest tests.test_agent_memory_demo
```

## Interactive REPL Demo

Run the command-based interactive memory Agent demo:

```bash
uv run python examples/agent_memory_repl.py
```

The REPL keeps one in-memory service alive for the session. It supports:

- `remember <memory text>`
- `search <query>`
- `context <query>`
- `correct <event-id> <new memory text>`
- `explain <event-id>`
- `delete <event-id> [reason]`
- `audit`
- `metrics`
- `quit`

This is a command interface over the reference service, not an LLM chat runtime. It is meant to make memory lifecycle behavior easy to feel in one terminal session.

The planned real LLM chat runtime is tracked separately in [design-docs/python-llm-agent-runtime.md](design-docs/python-llm-agent-runtime.md) and [exec-plans/active/2026-05-05-python-llm-agent-runtime.md](exec-plans/active/2026-05-05-python-llm-agent-runtime.md). Until that plan is implemented, `examples/agent_memory_repl.py` remains deterministic and does not call a provider API.

The same flow is covered by:

```bash
uv run python -m unittest tests.test_agent_memory_repl
```

## LLM Agent Chat Demo

Run the provider-backed Python Agent chat demo:

```bash
OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run python examples/llm_agent_chat.py
```

Optional environment variables:

- `PHONE_MEM_LLM_MODEL`: model used for the chat request; defaults to `gpt-4.1` for local demos.
- `PHONE_MEM_LLM_BASE_URL`: OpenAI-compatible base URL; defaults to `https://api.openai.com/v1`.

The demo creates an in-memory service, grants `llm_memory_agent` scoped read, write, update, delete, and context-build access to `system_assistant` personal episodic memory, then runs chat turns through `phone_mem.agent_runtime.AgentRuntime`.

The runtime path is intentionally separate from the memory core:

- `phone_mem.agent_runtime.client`: provider-neutral request, response, message, and tool-call contracts.
- `phone_mem.agent_runtime.tools`: governed memory tools backed only by `PersonalMemoryService`.
- `phone_mem.agent_runtime.prompts`: prompt assembly that marks retrieved memory as data, not instruction.
- `phone_mem.agent_runtime.runtime`: one-turn orchestration with optional memory tool execution.
- `phone_mem.agent_runtime.openai_client`: OpenAI-compatible Chat Completions adapter using environment configuration.

Default tests use `FakeLLMClient` or injected HTTP transports and do not call provider APIs:

```bash
uv run python -m unittest tests.test_agent_runtime_client tests.test_agent_runtime_tools tests.test_agent_runtime_prompts tests.test_agent_runtime tests.test_agent_runtime_openai_client tests.test_llm_agent_chat_example
```

The demo is the first real Agent experience for the Python reference. It is still a developer-machine runtime spike, not the production mobile runtime.

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

## Retrieval Selector Walkthrough

Run the selector walkthrough:

```bash
uv run python examples/retrieval_selector_walkthrough.py
```

The walkthrough records planning and travel memories, then demonstrates scoped search with `MemorySelector`:

1. entity-scoped retrieval for planning memory;
2. app-scoped retrieval for `system_assistant` memory;
3. app-scoped retrieval for a calendar-synced app event;
4. selector-based deletion for travel memory;
5. post-delete retrieval filtering.

The same flow is covered by:

```bash
uv run python -m unittest tests.test_retrieval_selector_walkthrough
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

## Lifecycle Explainability

`service.explain(event_id, caller=...)` returns the canonical event metadata plus a `lifecycle_explanation` object for caller-facing review:

```python
explanation = service.explain(event_id, caller="calendar_agent")
print(explanation["lifecycle_explanation"])
```

The lifecycle explanation contains:

- `state`: current lifecycle state, such as `active`, `quarantined`, `superseded`, or `deleted`;
- `reason`: caller-readable lifecycle reason;
- `related_event_ids`: contradiction parents, corrected originals, or correction replacements when known.

Rejected writes are not persisted as memory events. They are represented by denied audit records and `MemoryPermissionDenied`.

## Mobile Contract Fixtures

The Python reference is also the executable oracle for future mobile TypeScript behavior. Shared contract fixtures live under `tests/fixtures/memory_service/` and are validated by:

```bash
uv run python -m unittest tests.test_stage2_mobile_contract_fixtures
```

Those fixtures cover canonical events, permission grants, retrieval results, context bundles, tombstones, audit records, lifecycle explanations for correction and quarantine, and structured service errors for permission denial and missing events.

## Maintenance Guidance

The Python memory core remains the reference oracle. Keep future changes to `phone_mem.personal_memory_service`, `phone_mem.context`, and `phone_mem.governance` scoped to behavior that preserves or clarifies that oracle:

- bug fixes in reference behavior;
- contract fixture updates needed for mobile parity;
- small documentation or example clarifications;
- lifecycle, retrieval, permission, or service-error clarifications discovered while implementing Stage 2;
- tests for every behavior change.

Real LLM API work belongs in a separate `phone_mem.agent_runtime` boundary. Broader mobile product implementation should still move to Stage 2 only after a separate mobile execution plan is accepted.
