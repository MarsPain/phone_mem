# Mock Phone Tool Environment

## Purpose

The mock phone tool environment is a Python research harness for studying the full Agent Memory loop before a real mobile runtime exists. It gives the LLM controlled access to simulated phone apps while preserving the existing Personal Memory Service boundary.

The environment should make this loop executable:

```text
user message
  -> governed memory context
  -> LLM chooses memory tools and phone tools
  -> mock phone tool execution
  -> final answer with tool results
  -> action observations become governed memory candidates
  -> later turns retrieve those memories
```

This is not a production mobile runtime, not an OS integration layer, and not a replacement for app-specific mobile APIs. It is a deterministic research environment for algorithms, prompts, lifecycle policy, and Web Lab inspection.

## Scope

The first version should model three high-value phone app domains:

- Contacts;
- Calendar;
- Messaging.

The tool depth is intentionally read-heavy with controlled writes:

- read contacts, calendar events, message threads, and messages;
- create calendar events;
- create message drafts;
- do not send messages or model irreversible real-world side effects.

The storage model should support both in-memory fixtures for deterministic tests and SQLite persistence for Web Lab or longer research sessions.

## Architecture Boundary

Add `phone_mem/phone_tools/` as a sibling bounded context to `phone_mem/agent_runtime/` and `phone_mem/personal_memory_service/`.

```text
phone_mem.agent_runtime.AgentRuntime
        |
        +--> MemoryToolRegistry
        |       |
        |       v
        |  PersonalMemoryService
        |
        +--> PhoneToolRegistry
                |
                v
           Mock phone app stores
```

`PhoneToolRegistry` owns mock app tool schemas and dispatch. It does not own memory, construct durable memory events directly, or bypass `PersonalMemoryService`. Phone app state belongs to phone tool stores. Memory state belongs to the Personal Memory Service.

The runtime should expose one combined tool surface to the LLM, but execution remains routed by bounded context:

- memory tool names dispatch to `MemoryToolRegistry`;
- phone tool names dispatch to `PhoneToolRegistry`;
- unknown tool names fail as structured runtime errors.

## Proposed Modules

```text
phone_mem/phone_tools/
|-- registry.py
|-- models.py
|-- store.py
|-- in_memory_store.py
|-- sqlite_store.py
|-- seed.py
`-- observations.py
```

- `registry.py`: provider-neutral tool definitions, argument normalization, and tool dispatch.
- `models.py`: `Contact`, `CalendarEvent`, `MessageThread`, `Message`, and `MessageDraft`.
- `store.py`: `PhoneToolStore` protocol shared by in-memory and SQLite implementations.
- `in_memory_store.py`: deterministic fixture-backed store for unit tests.
- `sqlite_store.py`: file-backed store for Web Lab and longer experiments.
- `seed.py`: repeatable seed helpers for contacts, calendars, and messages.
- `observations.py`: `ToolObservation`, capture policy, and serialization helpers.

## LLM Tool Surface

The first version should expose these provider-neutral phone tools alongside the existing memory tools:

| Tool | Operation | Description | Memory capture |
| --- | --- | --- | --- |
| `search_contacts` | read | Search contacts by name, alias, company, relationship, or keyword. | Trace only |
| `get_contact` | read | Return one contact by ID. | Trace only |
| `search_calendar` | read | Search calendar events by time range and optional keyword. | Trace only |
| `create_calendar_event` | write-lite | Create a mock calendar event. | Capture-worthy |
| `search_messages` | read | Search threads or messages by participant, time range, or keyword. | Trace only |
| `get_message_thread` | read | Return recent messages from one thread. | Trace only |
| `draft_message` | write-lite | Create a message draft without sending it. | Capture-worthy |

The first version should not expose `send_message`. Sending introduces real-world semantics such as delivery, consent, confirmation, retries, and recipient-side effects. Drafting is enough to study memory-assisted communication and action-derived memory without pretending the Python harness has real phone authority.

## Store Model

Phone tool state should be separate from canonical memory events. SQLite tables may live in the same `.phone-mem-lab/memory.sqlite3` file as the Web Lab memory database for convenience, but table ownership must remain separate.

Suggested table ownership:

- `phone_contacts`;
- `phone_calendar_events`;
- `phone_message_threads`;
- `phone_messages`;
- `phone_message_drafts`.

In-memory and SQLite stores should expose the same protocol so tests and Web Lab use the same registry behavior. Tests should seed deterministic app state through `seed.py`; Web Lab should be able to persist mock phone state across restarts.

## Runtime Integration

Introduce a combined runtime tool provider that aggregates independent registries:

```text
CombinedToolProvider
  -> memory_tools.tool_definitions()
  -> phone_tools.tool_definitions()
  -> execute(name, arguments)
  -> ToolExecutionRecord
```

`ToolExecutionRecord` should preserve:

- provider name, such as `memory` or `phone`;
- tool name;
- normalized arguments;
- raw result payload;
- user-visible observation text when available;
- evidence event IDs when the tool result came from memory;
- whether the observation is eligible for session capture.

`AgentRuntime` should continue building governed memory context before the first model call. During tool execution, it should collect all tool records and pass capture-worthy observations to `SessionCapture`.

## Capture Policy

Phone tool observations should not all become memory. The policy is action-based:

- read tools are trace-only;
- `create_calendar_event` is capture-worthy;
- `draft_message` is capture-worthy.

Capture-worthy observations should become `MemoryCandidate` proposals through the existing session-capture path. They must still pass through `PersonalMemoryService.record(...)`, caller grants, lifecycle checks, duplicate handling, audit records, and later correction/deletion workflows.

Example observation for `create_calendar_event`:

```text
Agent created a calendar event with Alice for 2026-05-15 15:00 about the dentist appointment.
```

Example observation for `draft_message`:

```text
Agent drafted a message to Bob about rescheduling dinner.
```

Read tools may still appear in the Turn Debugger and tool result traces, but they should not be durable memory candidates by default. This prevents routine lookup from silently turning into user memory.

## Web Lab Observability

The Web Lab should remain an inspection shell over the runtime. It may initialize the phone tool store, expose mock app state, and show phone tool traces, but it must not become a second implementation of phone tools or memory behavior.

The Turn Debugger should show:

- combined tool calls and execution records;
- phone tool observations;
- whether each observation was trace-only or capture-worthy;
- captured event IDs produced from phone actions;
- current mock contacts, calendar events, message threads, and drafts when useful for debugging.

The existing Memory Inspector should continue to show governed memory state, not raw phone app state. Phone app state should have a separate inspector section so users can distinguish simulated external app data from durable memory.

## Testing Strategy

The first implementation should add deterministic tests for:

- provider-neutral phone tool schemas;
- seeded in-memory contacts, calendar events, threads, messages, and drafts;
- read tools returning structured results without capture-worthy observations;
- `create_calendar_event` producing a persisted event and capture-worthy observation;
- `draft_message` producing a persisted draft and capture-worthy observation;
- combined tool dispatch across memory tools and phone tools;
- a runtime turn where phone action observations become governed memory candidates;
- later retrieval of memory created from a phone action observation;
- SQLite persistence of mock phone state;
- Web Lab state initialization for memory service, runtime, and phone tool store.

Tests must remain network-free by default. Real provider behavior can be exercised manually through existing OpenAI-compatible runtime configuration.

## Non-Goals

- Real iOS or Android API integration.
- Background sensing or notification streams.
- Sending real messages.
- Full calendar recurrence, invitations, attendee RSVP, or time-zone complexity beyond what tests need.
- Third-party app ecosystem permissions.
- Replacing `PersonalMemoryService` as the source of truth for durable memory.

## Acceptance

- LLM-visible memory tools and phone tools are separate registries exposed through one combined runtime surface.
- Mock Contacts, Calendar, and Messaging state can be seeded in memory and persisted in SQLite.
- Phone read tools are trace-only by default.
- Calendar creation and message drafting can feed governed session capture.
- Durable memory still enters the system only through `PersonalMemoryService`.
- Web Lab inspection clearly separates memory state from mock phone app state.
