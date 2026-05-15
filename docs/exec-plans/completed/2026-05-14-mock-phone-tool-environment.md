# Mock Phone Tool Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic Python mock phone tool environment for Contacts, Calendar, and Messaging so the LLM can use simulated phone tools and feed action observations back into governed memory capture.

**Architecture:** Create a separate `phone_mem.phone_tools` bounded context for mock app state, with in-memory and SQLite stores behind one registry. Add a combined runtime tool provider that exposes existing memory tools plus phone tools to the LLM while keeping durable memory writes behind `PersonalMemoryService`.

**Tech Stack:** Python dataclasses and protocols, stdlib `sqlite3`, existing `ToolDefinition`/`ToolCall` runtime contracts, `unittest`, existing Web Lab state and docs validation commands.

---

Status: active

## Goal

Implement the approved [Mock Phone Tool Environment](../../design-docs/mock-phone-tool-environment.md) design as an executable Python research harness.

The finished system should support this loop:

```text
user message
  -> governed memory context
  -> LLM sees memory tools and phone tools
  -> phone tool execution over mock app state
  -> final answer with tool results
  -> action observations enter SessionCapture
  -> governed memory candidates become retrievable later
```

## Scope

In scope:

- Add `phone_mem/phone_tools/` with models, observations, store protocol, in-memory store, SQLite store, seed helpers, and `PhoneToolRegistry`.
- Expose these LLM-callable phone tools: `search_contacts`, `get_contact`, `search_calendar`, `create_calendar_event`, `search_messages`, `get_message_thread`, and `draft_message`.
- Make read tools trace-only.
- Make `create_calendar_event` and `draft_message` capture-worthy.
- Add a combined tool provider for runtime dispatch across memory and phone tools.
- Wire Web Lab state to initialize a persistent phone tool store.
- Add deterministic unit tests and docs validation.

Out of scope:

- Real iOS or Android integration.
- `send_message`.
- Full recurrence, delivery, notifications, RSVP, or third-party app permissions.
- Replacing `PersonalMemoryService` or writing directly to memory storage from phone tools.

## File Structure

Create:

- `phone_mem/phone_tools/__init__.py`: public exports for the phone tools package.
- `phone_mem/phone_tools/models.py`: immutable app-domain dataclasses and `to_dict()` methods.
- `phone_mem/phone_tools/observations.py`: `ToolObservation` and capture policy helpers.
- `phone_mem/phone_tools/store.py`: `PhoneToolStore` protocol.
- `phone_mem/phone_tools/in_memory_store.py`: deterministic in-memory implementation.
- `phone_mem/phone_tools/sqlite_store.py`: persistent SQLite implementation and schema initialization.
- `phone_mem/phone_tools/seed.py`: repeatable fixture seed data and seed insertion helpers.
- `phone_mem/phone_tools/registry.py`: phone tool definitions, argument parsing, and dispatch.
- `phone_mem/agent_runtime/tool_provider.py`: combined memory/phone tool provider and execution records.
- `tests/test_phone_tools_models.py`: model and observation tests.
- `tests/test_phone_tools_store.py`: in-memory store tests.
- `tests/test_phone_tools_registry.py`: phone tool schema and dispatch tests.
- `tests/test_phone_tools_sqlite_store.py`: SQLite persistence tests.
- `tests/test_agent_runtime_combined_tools.py`: runtime dispatch and capture-loop tests.

Modify:

- `phone_mem/agent_runtime/runtime.py`: use combined execution records and pass capture-worthy phone observations to `SessionCapture`.
- `phone_mem/agent_runtime/session_capture.py`: accept explicit tool observation strings without changing memory service boundaries.
- `phone_mem/agent_runtime/__init__.py`: export combined provider types.
- `phone_mem/web_lab/state.py`: initialize persistent phone store and combined runtime provider.
- `phone_mem/web_lab/inspector.py`: expose read-only phone app state for debugging.
- `phone_mem/web_lab/schemas.py`: serialize phone state and tool records if needed.
- `phone_mem/web_lab/templates/index.html`: add a compact phone state inspector.
- `phone_mem/web_lab/static/web_lab.js`: fetch and render phone state.
- `phone_mem/web_lab/static/web_lab.css`: style phone state output without changing the core layout.
- `examples/llm_agent_chat.py`: optional fixture-backed phone tools for local demo use.
- `docs/PYTHON_REFERENCE.md`: mention the mock phone tool harness and commands.
- `docs/BACKEND.md`: update Track 2.8 from proposed to implemented when complete.
- `docs/PLANS.md`: move this plan from active to completed when accepted.

## Steps

### Task 1: Phone Tool Models And Observations

**Files:**

- Create: `phone_mem/phone_tools/__init__.py`
- Create: `phone_mem/phone_tools/models.py`
- Create: `phone_mem/phone_tools/observations.py`
- Test: `tests/test_phone_tools_models.py`

- [x] **Step 1: Write failing model and observation tests**

Create `tests/test_phone_tools_models.py` with focused tests:

```python
from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.phone_tools.models import CalendarEvent, Contact, Message, MessageDraft, MessageThread
from phone_mem.phone_tools.observations import ToolObservation


class PhoneToolModelsTest(unittest.TestCase):
    def test_contact_serializes_stable_fields(self) -> None:
        contact = Contact(
            contact_id="contact-1",
            display_name="Alice Chen",
            aliases=["Alice"],
            phones=["+1-555-0100"],
            emails=["alice@example.com"],
            company="Atlas",
            relationship="dentist",
            notes="Prefers afternoon appointments.",
        )

        self.assertEqual(contact.to_dict()["display_name"], "Alice Chen")
        self.assertEqual(contact.to_dict()["aliases"], ["Alice"])
        self.assertEqual(contact.to_dict()["relationship"], "dentist")

    def test_calendar_event_serializes_iso_times(self) -> None:
        event = CalendarEvent(
            event_id="cal-1",
            title="Dentist appointment",
            start_at=datetime(2026, 5, 15, 15, 0, tzinfo=UTC),
            end_at=datetime(2026, 5, 15, 16, 0, tzinfo=UTC),
            participant_contact_ids=["contact-1"],
            location="Clinic",
            notes="Bring insurance card.",
            created_by_tool=True,
        )

        self.assertEqual(event.to_dict()["start_at"], "2026-05-15T15:00:00+00:00")
        self.assertTrue(event.to_dict()["created_by_tool"])

    def test_message_thread_and_draft_serialize(self) -> None:
        message = Message(
            message_id="msg-1",
            thread_id="thread-1",
            sender_contact_id="contact-1",
            sent_at=datetime(2026, 5, 14, 9, 0, tzinfo=UTC),
            text="Can we reschedule dinner?",
        )
        thread = MessageThread(
            thread_id="thread-1",
            participant_contact_ids=["contact-1", "self"],
            messages=[message],
        )
        draft = MessageDraft(
            draft_id="draft-1",
            thread_id="thread-1",
            recipient_contact_ids=["contact-1"],
            text="How about Friday?",
            created_at=datetime(2026, 5, 14, 9, 5, tzinfo=UTC),
        )

        self.assertEqual(thread.to_dict()["messages"][0]["text"], "Can we reschedule dinner?")
        self.assertEqual(draft.to_dict()["recipient_contact_ids"], ["contact-1"])

    def test_tool_observation_marks_capture_policy(self) -> None:
        observation = ToolObservation(
            tool_name="create_calendar_event",
            text="Agent created a calendar event with Alice.",
            capture_worthy=True,
        )

        self.assertTrue(observation.capture_worthy)
        self.assertEqual(observation.to_dict()["tool_name"], "create_calendar_event")


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run failing tests**

Run:

```bash
uv run python -m unittest tests.test_phone_tools_models
```

Expected: fail with `ModuleNotFoundError: No module named 'phone_mem.phone_tools'`.

- [x] **Step 3: Implement model dataclasses and observations**

Create `phone_mem/phone_tools/models.py` with immutable dataclasses for `Contact`, `CalendarEvent`, `Message`, `MessageThread`, and `MessageDraft`. Each class should expose `to_dict()` and should use strings, lists, booleans, and ISO datetime strings only in serialized output.

Create `phone_mem/phone_tools/observations.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolObservation:
    tool_name: str
    text: str
    capture_worthy: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "text": self.text,
            "capture_worthy": self.capture_worthy,
            "metadata": dict(self.metadata),
        }
```

Create `phone_mem/phone_tools/__init__.py` exporting the public model and observation classes.

- [x] **Step 4: Run model tests**

Run:

```bash
uv run python -m unittest tests.test_phone_tools_models
```

Expected: `OK`.

### Task 2: In-Memory Phone Tool Store And Seed Fixtures

**Files:**

- Create: `phone_mem/phone_tools/store.py`
- Create: `phone_mem/phone_tools/in_memory_store.py`
- Create: `phone_mem/phone_tools/seed.py`
- Test: `tests/test_phone_tools_store.py`

- [x] **Step 1: Write failing store tests**

Create `tests/test_phone_tools_store.py` with tests for seeded search and controlled writes:

```python
from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.phone_tools.in_memory_store import InMemoryPhoneToolStore
from phone_mem.phone_tools.seed import seed_research_phone_state


class InMemoryPhoneToolStoreTest(unittest.TestCase):
    def test_seeded_contacts_calendar_and_messages_are_searchable(self) -> None:
        store = InMemoryPhoneToolStore()
        seed_research_phone_state(store)

        self.assertEqual(store.search_contacts("alice")[0].display_name, "Alice Chen")
        self.assertTrue(store.search_calendar(keyword="dentist"))
        self.assertTrue(store.search_messages(keyword="dinner"))

    def test_create_calendar_event_persists_event(self) -> None:
        store = InMemoryPhoneToolStore()
        event = store.create_calendar_event(
            title="Review mock phone tools",
            start_at=datetime(2026, 5, 15, 15, 0, tzinfo=UTC),
            end_at=datetime(2026, 5, 15, 16, 0, tzinfo=UTC),
            participant_contact_ids=["contact-alice"],
            location="Office",
            notes="Discuss tool capture policy.",
        )

        self.assertTrue(event.event_id.startswith("cal-"))
        self.assertEqual(store.get_calendar_event(event.event_id).title, "Review mock phone tools")

    def test_draft_message_persists_draft(self) -> None:
        store = InMemoryPhoneToolStore()
        draft = store.draft_message(
            thread_id="thread-alice",
            recipient_contact_ids=["contact-alice"],
            text="Friday afternoon works.",
            created_at=datetime(2026, 5, 14, 9, 0, tzinfo=UTC),
        )

        self.assertTrue(draft.draft_id.startswith("draft-"))
        self.assertEqual(store.list_message_drafts()[0].text, "Friday afternoon works.")


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run failing store tests**

Run:

```bash
uv run python -m unittest tests.test_phone_tools_store
```

Expected: fail because `store.py`, `in_memory_store.py`, and `seed.py` do not exist.

- [x] **Step 3: Implement store protocol and in-memory store**

Create `phone_mem/phone_tools/store.py` with a `PhoneToolStore` protocol covering:

- `add_contact(contact)`;
- `get_contact(contact_id)`;
- `search_contacts(query)`;
- `add_calendar_event(event)`;
- `get_calendar_event(event_id)`;
- `search_calendar(start_at=None, end_at=None, keyword=None)`;
- `create_calendar_event(...)`;
- `add_message_thread(thread)`;
- `get_message_thread(thread_id)`;
- `search_messages(keyword=None, contact_id=None)`;
- `draft_message(...)`;
- `list_message_drafts()`.

Create `phone_mem/phone_tools/in_memory_store.py` using dictionaries keyed by IDs and deterministic counters for generated `cal-*` and `draft-*` IDs. Search should be case-insensitive substring matching over the fields needed by tests.

Create `phone_mem/phone_tools/seed.py` with `seed_research_phone_state(store)` that inserts Alice contact data, one dentist calendar event, one dinner-related thread, and one message.

- [x] **Step 4: Run store tests**

Run:

```bash
uv run python -m unittest tests.test_phone_tools_store
```

Expected: `OK`.

### Task 3: PhoneToolRegistry Schemas And Dispatch

**Files:**

- Create: `phone_mem/phone_tools/registry.py`
- Modify: `phone_mem/phone_tools/__init__.py`
- Test: `tests/test_phone_tools_registry.py`

- [x] **Step 1: Write failing registry tests**

Create `tests/test_phone_tools_registry.py`:

```python
from __future__ import annotations

import unittest

from phone_mem.phone_tools.in_memory_store import InMemoryPhoneToolStore
from phone_mem.phone_tools.registry import PhoneToolRegistry
from phone_mem.phone_tools.seed import seed_research_phone_state


class PhoneToolRegistryTest(unittest.TestCase):
    def test_tool_definitions_expose_expected_phone_tools(self) -> None:
        registry = PhoneToolRegistry(InMemoryPhoneToolStore())
        definitions = {definition.name: definition for definition in registry.tool_definitions()}

        self.assertIn("search_contacts", definitions)
        self.assertIn("get_contact", definitions)
        self.assertIn("search_calendar", definitions)
        self.assertIn("create_calendar_event", definitions)
        self.assertIn("search_messages", definitions)
        self.assertIn("get_message_thread", definitions)
        self.assertIn("draft_message", definitions)
        self.assertEqual(definitions["draft_message"].parameters["type"], "object")

    def test_read_tools_are_trace_only(self) -> None:
        store = InMemoryPhoneToolStore()
        seed_research_phone_state(store)
        registry = PhoneToolRegistry(store)

        result = registry.execute("search_contacts", {"query": "Alice"})

        self.assertFalse(result.observation.capture_worthy)
        self.assertEqual(result.result["contacts"][0]["display_name"], "Alice Chen")

    def test_create_calendar_event_is_capture_worthy(self) -> None:
        registry = PhoneToolRegistry(InMemoryPhoneToolStore())

        result = registry.execute(
            "create_calendar_event",
            {
                "title": "Review mock phone tools",
                "start_at": "2026-05-15T15:00:00+00:00",
                "end_at": "2026-05-15T16:00:00+00:00",
                "participant_contact_ids": ["contact-alice"],
                "location": "Office",
                "notes": "Discuss tool capture policy.",
            },
        )

        self.assertTrue(result.observation.capture_worthy)
        self.assertIn("created a calendar event", result.observation.text)
        self.assertEqual(result.result["event"]["title"], "Review mock phone tools")

    def test_draft_message_is_capture_worthy(self) -> None:
        registry = PhoneToolRegistry(InMemoryPhoneToolStore())

        result = registry.execute(
            "draft_message",
            {
                "thread_id": "thread-alice",
                "recipient_contact_ids": ["contact-alice"],
                "text": "Friday afternoon works.",
            },
        )

        self.assertTrue(result.observation.capture_worthy)
        self.assertIn("drafted a message", result.observation.text)
        self.assertEqual(result.result["draft"]["text"], "Friday afternoon works.")


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run failing registry tests**

Run:

```bash
uv run python -m unittest tests.test_phone_tools_registry
```

Expected: fail because `PhoneToolRegistry` does not exist.

- [x] **Step 3: Implement registry and result object**

In `phone_mem/phone_tools/registry.py`, define:

- `PhoneToolResult` dataclass with `name`, `arguments`, `result`, and `observation`.
- `PhoneToolRegistry.tool_definitions()` returning seven `ToolDefinition` objects.
- `PhoneToolRegistry.execute(name, arguments)` dispatching each supported tool.
- ISO datetime parsing for calendar arguments.
- trace-only observations for reads and capture-worthy observations for `create_calendar_event` and `draft_message`.

Reuse the same `_object_schema(...)` shape as `MemoryToolRegistry` rather than introducing a new schema builder style.

- [x] **Step 4: Run registry tests**

Run:

```bash
uv run python -m unittest tests.test_phone_tools_registry
```

Expected: `OK`.

### Task 4: SQLite Phone Tool Store

**Files:**

- Create: `phone_mem/phone_tools/sqlite_store.py`
- Test: `tests/test_phone_tools_sqlite_store.py`

- [x] **Step 1: Write failing SQLite persistence tests**

Create `tests/test_phone_tools_sqlite_store.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from phone_mem.phone_tools.models import Contact
from phone_mem.phone_tools.sqlite_store import SQLitePhoneToolStore


class SQLitePhoneToolStoreTest(unittest.TestCase):
    def test_persists_contacts_events_and_drafts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "phone.sqlite3"
            store = SQLitePhoneToolStore.connect(str(db_path))
            store.initialize_schema()
            store.add_contact(
                Contact(
                    contact_id="contact-alice",
                    display_name="Alice Chen",
                    aliases=["Alice"],
                    phones=[],
                    emails=["alice@example.com"],
                    company="Atlas",
                    relationship="friend",
                    notes="",
                )
            )
            event = store.create_calendar_event(
                title="Planning",
                start_at=datetime(2026, 5, 15, 15, 0, tzinfo=UTC),
                end_at=datetime(2026, 5, 15, 16, 0, tzinfo=UTC),
                participant_contact_ids=["contact-alice"],
                location="Office",
                notes="",
            )
            draft = store.draft_message(
                thread_id="thread-alice",
                recipient_contact_ids=["contact-alice"],
                text="Friday works.",
                created_at=datetime(2026, 5, 14, 9, 0, tzinfo=UTC),
            )
            store.close()

            reopened = SQLitePhoneToolStore.connect(str(db_path))
            reopened.initialize_schema()
            self.addCleanup(reopened.close)

            self.assertEqual(reopened.get_contact("contact-alice").display_name, "Alice Chen")
            self.assertEqual(reopened.get_calendar_event(event.event_id).title, "Planning")
            self.assertEqual(reopened.list_message_drafts()[0].draft_id, draft.draft_id)
```

- [x] **Step 2: Run failing SQLite tests**

Run:

```bash
uv run python -m unittest tests.test_phone_tools_sqlite_store
```

Expected: fail because `SQLitePhoneToolStore` does not exist.

- [x] **Step 3: Implement SQLite store**

Create `SQLitePhoneToolStore` with:

- `connect(path: str) -> SQLitePhoneToolStore`;
- `initialize_schema()`;
- `close()`;
- JSON serialization for list fields and nested message lists;
- tables named `phone_contacts`, `phone_calendar_events`, `phone_message_threads`, `phone_messages`, and `phone_message_drafts`;
- the same public methods as `InMemoryPhoneToolStore`.

Keep SQL localized in `sqlite_store.py`. Do not reuse or modify `SQLiteMemoryStore`.

- [x] **Step 4: Run SQLite tests**

Run:

```bash
uv run python -m unittest tests.test_phone_tools_sqlite_store
```

Expected: `OK`.

### Task 5: Combined Runtime Tool Provider

**Files:**

- Create: `phone_mem/agent_runtime/tool_provider.py`
- Modify: `phone_mem/agent_runtime/runtime.py`
- Modify: `phone_mem/agent_runtime/session_capture.py`
- Modify: `phone_mem/agent_runtime/__init__.py`
- Test: `tests/test_agent_runtime_combined_tools.py`

- [x] **Step 1: Write failing combined-provider tests**

Create `tests/test_agent_runtime_combined_tools.py` with two tests:

```python
from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.agent_runtime.client import FakeLLMClient, LLMResponse, ToolCall
from phone_mem.agent_runtime.runtime import AgentRuntime
from phone_mem.agent_runtime.tool_provider import CombinedToolProvider
from phone_mem.agent_runtime.tools import MemoryToolRegistry
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.events import AuditOperation, MemoryLayer, PrivacyLevel
from phone_mem.personal_memory_service.service import PersonalMemoryService
from phone_mem.phone_tools.in_memory_store import InMemoryPhoneToolStore
from phone_mem.phone_tools.registry import PhoneToolRegistry


CALLER = "runtime_agent"
SOURCE_APP = "system_assistant"


class AgentRuntimeCombinedToolsTest(unittest.TestCase):
    def test_combined_provider_exposes_memory_and_phone_tools(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        provider = CombinedToolProvider(
            memory_tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
            phone_tools=PhoneToolRegistry(InMemoryPhoneToolStore()),
        )

        names = {definition.name for definition in provider.tool_definitions()}

        self.assertIn("search_memory", names)
        self.assertIn("create_calendar_event", names)

    def test_phone_action_observation_is_captured_as_governed_memory(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        provider = CombinedToolProvider(
            memory_tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
            phone_tools=PhoneToolRegistry(InMemoryPhoneToolStore()),
        )
        runtime = AgentRuntime(
            client=FakeLLMClient(
                [
                    LLMResponse(
                        text="",
                        tool_calls=[
                            ToolCall(
                                call_id="call-1",
                                name="create_calendar_event",
                                arguments={
                                    "title": "Dentist appointment",
                                    "start_at": "2026-05-15T15:00:00+00:00",
                                    "end_at": "2026-05-15T16:00:00+00:00",
                                    "participant_contact_ids": ["contact-alice"],
                                    "location": "Clinic",
                                    "notes": "Bring insurance card.",
                                },
                            )
                        ],
                    ),
                    LLMResponse(text="I created the calendar event."),
                ]
            ),
            model="fake-model",
            tools=provider,
        )

        response = runtime.run_turn("Schedule my dentist appointment for Friday at 3 PM.")

        self.assertEqual(response.tool_results[0]["name"], "create_calendar_event")
        self.assertEqual(response.captured_event_ids, ["event-1"])
        search = provider.memory_tools.search_memory("dentist appointment", top_k=3)
        self.assertEqual(search["results"][0]["event_id"], "event-1")


def _service_with_grant() -> PersonalMemoryService:
    service = PersonalMemoryService.in_memory(clock=lambda: datetime(2026, 5, 14, 9, 0, tzinfo=UTC))
    service.grant(
        CALLER,
        PermissionScope(
            operations=[
                AuditOperation.WRITE,
                AuditOperation.READ,
                AuditOperation.UPDATE,
                AuditOperation.DELETE,
                AuditOperation.CONTEXT_BUILD,
            ],
            apps=[SOURCE_APP],
            privacy_levels=[PrivacyLevel.PERSONAL],
            memory_layers=[MemoryLayer.EPISODIC],
        ),
        duration_seconds=3_600,
    )
    return service
```

- [x] **Step 2: Run failing combined-provider tests**

Run:

```bash
uv run python -m unittest tests.test_agent_runtime_combined_tools
```

Expected: fail because `CombinedToolProvider` does not exist and `AgentRuntime.tools` does not accept it yet.

- [x] **Step 3: Implement combined provider**

Create `phone_mem/agent_runtime/tool_provider.py`:

- `ToolExecutionRecord` dataclass with `call_id`, `provider`, `name`, `arguments`, `result`, `observation`, `capture_worthy`, and `evidence_event_ids`.
- `CombinedToolProvider` dataclass with `memory_tools: MemoryToolRegistry` and `phone_tools: PhoneToolRegistry | None = None`.
- `build_memory_context(...)` delegates to `memory_tools`.
- `record_candidate(...)` delegates to `memory_tools` for `SessionCapture`.
- `tool_definitions()` concatenates memory and phone definitions.
- `execute(call_id, name, arguments)` dispatches to memory first, then phone, and returns `ToolExecutionRecord`.

- [x] **Step 4: Modify runtime to consume execution records**

Update `AgentRuntime.run_turn(...)` so it:

- calls `self.tools.tool_definitions()`;
- executes tool calls through `self.tools.execute(call.call_id, call.name, call.arguments)`;
- serializes `ToolExecutionRecord` objects into the existing `tool_results` list;
- passes only capture-worthy observation text to `_flush_session_capture(...)`;
- keeps existing no-tool behavior unchanged.

For compatibility, either update all runtime constructors to pass `CombinedToolProvider`, or add a small normalization helper that wraps a plain `MemoryToolRegistry` into `CombinedToolProvider`.

- [x] **Step 5: Run combined-provider tests**

Run:

```bash
uv run python -m unittest tests.test_agent_runtime_combined_tools tests.test_agent_runtime tests.test_agent_runtime_tools
```

Expected: `OK`.

### Task 6: Web Lab Persistent Phone Tool State

**Files:**

- Modify: `phone_mem/web_lab/state.py`
- Modify: `phone_mem/web_lab/inspector.py`
- Modify: `phone_mem/web_lab/schemas.py`
- Modify: `phone_mem/web_lab/templates/index.html`
- Modify: `phone_mem/web_lab/static/web_lab.js`
- Modify: `phone_mem/web_lab/static/web_lab.css`
- Test: `tests/test_web_lab_state.py`
- Test: `tests/test_web_lab_inspector.py`
- Test: `tests/test_web_lab_routes.py`

- [ ] **Step 1: Write failing Web Lab state test**

Extend `tests/test_web_lab_state.py` with a test that creates `LabState` against a temporary SQLite path and asserts:

- `state.phone_tools` exists;
- `state.runtime.tools.tool_definitions()` includes `create_calendar_event`;
- seeded phone state contains Alice or another deterministic contact.

- [ ] **Step 2: Add phone store initialization to LabState**

Modify `LabState.create(...)`:

- derive the phone tool store from the same `.phone-mem-lab/memory.sqlite3` file;
- call `SQLitePhoneToolStore.initialize_schema()`;
- seed default phone data only when the phone tables are empty;
- build `PhoneToolRegistry`;
- build `CombinedToolProvider(memory_tools=memory_tools, phone_tools=phone_tools)`;
- pass the combined provider to `AgentRuntime`.

Keep `LabState.tools` available as the memory registry for existing inspector code, and add `LabState.phone_tools` plus `LabState.phone_store`.

- [ ] **Step 3: Add read-only phone inspector payload**

Add a Web Lab inspector method such as `phone_state()` returning contacts, calendar events, message threads, and drafts through phone store APIs. This method is for debugging only; it should not mutate state.

- [ ] **Step 4: Add route and compact UI output**

Add a route such as `/api/phone-state` that returns the inspector payload. Render it in a separate "Phone State" output area in the existing single-page lab. Do not mix phone app state into the Memory Inspector output.

- [ ] **Step 5: Run Web Lab tests**

Run:

```bash
uv run python -m unittest tests.test_web_lab_state tests.test_web_lab_inspector tests.test_web_lab_routes
```

Expected: `OK`.

### Task 7: Demo, Documentation, And Public Exports

**Files:**

- Modify: `phone_mem/agent_runtime/__init__.py`
- Modify: `phone_mem/phone_tools/__init__.py`
- Modify: `examples/llm_agent_chat.py`
- Modify: `docs/PYTHON_REFERENCE.md`
- Modify: `docs/BACKEND.md`
- Modify: `docs/PLANS.md` when implementation is accepted

- [ ] **Step 1: Export public types**

Export `CombinedToolProvider`, `ToolExecutionRecord`, `PhoneToolRegistry`, `InMemoryPhoneToolStore`, `SQLitePhoneToolStore`, and seed helpers from their package `__init__.py` files.

- [ ] **Step 2: Update CLI demo construction**

Modify `examples/llm_agent_chat.py` so the default runtime includes seeded in-memory phone tools. Keep provider credentials optional exactly as before.

- [ ] **Step 3: Update Python reference docs**

Add a short section to `docs/PYTHON_REFERENCE.md` explaining:

- mock phone tools are research harness tools, not real mobile APIs;
- the seven phone tools exposed to LLMs;
- read tools are trace-only;
- calendar creation and message drafting can become governed memory candidates.

- [ ] **Step 4: Update backend track status**

After code and tests pass, update `docs/BACKEND.md` so Track 2.8 describes implemented behavior instead of proposed behavior.

Do not move this plan to `completed` until the user accepts the implementation.

### Task 8: Full Validation

**Files:**

- No new files unless validation reveals a missing focused test.

- [ ] **Step 1: Run focused test suite**

Run:

```bash
uv run python -m unittest tests.test_phone_tools_models tests.test_phone_tools_store tests.test_phone_tools_registry tests.test_phone_tools_sqlite_store tests.test_agent_runtime_combined_tools tests.test_web_lab_state tests.test_web_lab_inspector tests.test_web_lab_routes
```

Expected: `OK`.

- [ ] **Step 2: Run full unit suite**

Run:

```bash
uv run python -m unittest discover -s tests
```

Expected: `OK`.

- [ ] **Step 3: Run docs validator**

Run:

```bash
uv run python scripts/validate_docs.py
```

Expected: `Documentation validation passed.`

- [ ] **Step 4: Review architectural boundaries**

Check:

- no `phone_mem/phone_tools` module imports `PersonalMemoryService`;
- phone stores do not write memory tables;
- `PersonalMemoryService` does not import phone tools;
- read phone tools do not produce capture-worthy observations;
- `create_calendar_event` and `draft_message` observations enter memory only through `SessionCapture`.

- [ ] **Step 5: Prepare completion notes**

Summarize:

- new LLM tool names;
- storage behavior;
- capture policy;
- test commands and results;
- any follow-up limitations such as no `send_message` and no recurrence support.

## Validation

Required validation before claiming implementation complete:

```bash
uv run python -m unittest tests.test_phone_tools_models tests.test_phone_tools_store tests.test_phone_tools_registry tests.test_phone_tools_sqlite_store tests.test_agent_runtime_combined_tools tests.test_web_lab_state tests.test_web_lab_inspector tests.test_web_lab_routes
uv run python -m unittest discover -s tests
uv run python scripts/validate_docs.py
```

## Acceptance

- `PhoneToolRegistry` exposes the seven approved provider-neutral phone tools.
- In-memory and SQLite phone stores support seeded Contacts, Calendar, Messaging, and drafts.
- `AgentRuntime` exposes memory and phone tools through one combined tool surface.
- Phone read tools stay trace-only.
- `create_calendar_event` and `draft_message` produce capture-worthy observations.
- Capture-worthy phone observations become memory only through `SessionCapture` and `PersonalMemoryService`.
- Web Lab can inspect memory state separately from mock phone app state.
- All focused tests, full unit tests, and docs validation pass.
