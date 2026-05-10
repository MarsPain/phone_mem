# Python Web Lab

## Purpose

The Python Web Lab is a local developer experience layer over the completed Python Personal Memory Service and Python LLM Agent Runtime. Its job is to make the current Agent feel inspectable in a browser so algorithm and lifecycle problems can be discovered before mobile runtime work resumes.

The Stage 1.6 browser shell is now aligned with the completed Stage 1.7 Python oracle. It exposes runtime capture, hybrid retrieval explanations, hot memory capsules, relation context metadata, dry-run maintenance reports, metrics, audit, correction, and deletion through the existing service/runtime boundary.

This track is a developer-machine lab. It is not the production mobile runtime, not a hosted web product, and not a parallel memory implementation.

## Product Goal

The first useful experience should be a single-screen Hybrid Lab where a developer can:

- chat with a real provider-backed Agent;
- inspect the memory context and evidence that shaped each answer;
- search with hybrid retrieval explanations, explain, correct, and delete memory through governed service APIs;
- see tool calls, tool results, recent audit records, and domain errors for each turn;
- inspect turn-boundary capture event IDs, hot capsules, omitted-memory reasons, relation paths, token/capsule budget metadata, quality metrics, and maintenance dry-run reports;
- keep memory across restarts using a local SQLite file.

The lab should help answer questions such as:

- Which memories did the Agent retrieve, and why?
- Did the context bundle hide important memory because of scoring, filtering, or token budget?
- Did a write, correction, or deletion go through the expected lifecycle path?
- Did audit records make the Agent's behavior explainable enough for future product flows?

## Architecture Boundary

```text
Browser
  |
  v
phone_mem.web_lab
  |
  +--> phone_mem.agent_runtime.AgentRuntime
  |       |
  |       +--> phone_mem.agent_runtime.OpenAICompatibleClient
  |       +--> phone_mem.agent_runtime.MemoryToolRegistry
  |
  +--> PersonalMemoryService
          |
          v
     SQLiteMemoryStore
```

The Web Lab may own application startup, local database path selection, HTTP routes, HTML templates, static assets, and session-level turn history. It must not own memory algorithms, provider execution, lifecycle decisions, permission filtering, or direct SQL-level behavior.

Any memory behavior shown in the UI must be produced through the Python reference service and Python Agent runtime, so the lab remains an experience layer over the executable oracle.

## Reused Python Components

The Web Lab must reuse the current Python implementation instead of reimplementing it:

- `SQLiteMemoryStore.connect(path)` and `PersonalMemoryService.from_store(...)` for the file-backed memory core.
- `MemoryToolRegistry` as the Web and LLM memory tool boundary.
- `AgentRuntime.run_turn(...)` as the chat-turn orchestration entrypoint.
- `OpenAICompatibleClient.from_env()` for real provider-backed local use.
- Existing service operations for record, search, build context, explain, correct, delete, audit, and metrics.

The only expected runtime enhancement is observability: `AgentTurnResponse` should expose the memory context used during a turn so the Turn Debugger can display what the model actually received without duplicating retrieval work.

## Runtime Defaults

Default configuration should optimize for local exploration:

- caller: `web_lab_agent`;
- source app: `system_assistant`;
- database path: `.phone-mem-lab/memory.sqlite3`;
- model: `PHONE_MEM_LLM_MODEL`, falling back to the existing runtime default;
- provider credentials: `OPENAI_API_KEY` and existing OpenAI-compatible environment variables;
- permissions: grant read, write, update, delete, and context-build operations for personal episodic memory from `system_assistant`.

The SQLite file should persist across restarts. Resetting the lab memory is useful, but it must be explicit and safe because the default behavior is cumulative exploration.

## Page Structure

The first version should be a single browser page with three work areas.

### Chat Panel

The Chat Panel sends natural-language user messages to `AgentRuntime.run_turn(...)`. It displays:

- user and assistant messages;
- assistant evidence event IDs;
- turn-level errors;
- a selectable turn history for the current browser session.

The first version does not need persistent chat sessions or multi-conversation management. The SQLite memory store is persistent; browser turn history can remain process or session state.

### Memory Inspector

The Memory Inspector exposes current memory state and service operations:

- memory list from reference domain objects, serialized through `to_dict()`;
- search over authorized memory with score explanations, score components, and score weights from `MemoryToolRegistry.search_memory(...)`;
- context preview for a query, including hot memory capsules, omitted-memory reasons, relation paths, evidence IDs, safety metadata, and token budget metadata from `MemoryToolRegistry.build_memory_context(...)`;
- explain by event ID;
- correct by event ID and replacement text;
- delete by event ID and reason;
- metrics and recent audit records.
- dry-run `reflect()`, `defrag()`, and `schema_diff()` maintenance reports with `mutates_store` visible.

Inspector operations must call `PersonalMemoryService` or `MemoryToolRegistry`. They must not write SQL, bypass grants, or mutate storage directly.

### Turn Debugger

The Turn Debugger displays the selected chat turn's internal evidence:

- memory context snippets and token budget;
- captured event IDs from runtime session capture;
- hot memory capsules, omitted-memory reasons, relation paths, capsule budget metadata, and safety metadata;
- tool calls and tool results;
- evidence event IDs;
- recent audit records;
- dry-run maintenance reports and aggregate quality metrics;
- provider request errors;
- domain errors such as permission denial or missing memory.

This is the core difference between the lab and a user-facing product UI. The lab should make internals visible even when a future product experience would hide them.

### Lab Header

The header should display:

- provider and model;
- database path;
- caller and source app;
- setup status;
- reload or reset entrypoints.

Reset can be a CLI/dev command in the first implementation. If a browser reset button is added, it must require confirmation.

## Backend Modules

The implementation should introduce a focused bounded context:

```text
phone_mem/web_lab/
├── app.py
├── state.py
├── schemas.py
├── inspector.py
├── templates/
└── static/
```

Suggested responsibilities:

- `app.py`: FastAPI app factory, route registration, and static/template wiring.
- `state.py`: `LabState` for service, runtime, tools, database path, caller, source app, and in-process turn snapshots.
- `schemas.py`: request and response DTOs for routes.
- `inspector.py`: use cases for memory list, audit list, context preview, dry-run maintenance reports, and safe reset orchestration if implemented.
- `templates/`: server-rendered HTML.
- `static/`: CSS and small vanilla JavaScript for form submission and panel updates.

The route layer should stay thin. It should translate HTTP requests into lab use cases and serialize domain responses, not embed lifecycle, retrieval, or provider logic.

## Dependencies

The first implementation should use:

- FastAPI for the local HTTP application;
- Uvicorn for local serving;
- server-rendered HTML plus minimal vanilla JavaScript;
- no React, Vite, or frontend build chain.

FastAPI `TestClient` may require an explicit HTTP test dependency. If so, the dependency should be added to project metadata rather than relying on transitive installation.

## Error Handling

Errors should be visible and structured because the lab is a debugging surface:

- Missing provider credentials should show a setup error while leaving non-provider memory inspection usable.
- Provider request failures should attach to the current turn snapshot and not terminate the lab process.
- Domain errors should preserve operation, caller, affected event IDs, selector, and denial reason when available.
- SQLite setup failures should fail startup with the database path and exception summary.
- Reset failures should leave the current state explicit rather than silently partially clearing memory.

## Testing Strategy

Default tests must remain deterministic and network-free:

- state tests should verify file-backed SQLite initialization, permission grants, runtime construction, and shutdown behavior;
- route tests should use fake clients and a temporary SQLite file;
- turn tests should verify that memory context, captured event IDs, tool results, evidence IDs, and recent audit records are exposed;
- inspector tests should cover search, context preview, explain, correct, delete, audit, metrics, and dry-run maintenance through service APIs;
- provider-backed manual testing should remain opt-in through environment variables.

Existing full-suite tests and documentation validation should continue to pass:

```bash
uv run python -m unittest discover -s tests
uv run python scripts/validate_docs.py
```

## Run Command

The main local command should be explicit:

```bash
OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run uvicorn phone_mem.web_lab.app:create_app --factory --reload
```

An optional convenience script can wrap the same app:

```bash
uv run python examples/web_lab.py
```

## Non-Goals

- Production web deployment.
- Login, authentication, remote access, or multi-user accounts.
- Mobile runtime implementation.
- Reimplementing the memory service in TypeScript.
- Direct SQL operations from the UI.
- Cloud sync, provider-side memory, vector databases, or embedding visualization.
- Persistent chat transcript storage beyond what is needed for local session debugging.

## Acceptance

- A developer can open the local Web Lab in a browser.
- Chat turns use the existing Python `AgentRuntime`.
- The default provider path is real-first and OpenAI-compatible.
- Memory persists across restarts through a local SQLite file.
- The Memory Inspector can search with retrieval explanations, preview context, explain, correct, delete memory, and inspect dry-run maintenance reports.
- The Turn Debugger shows memory context, captured event IDs, hot capsules, omitted-memory reasons, relation paths, maintenance reports, tool results, evidence IDs, recent audit records, metrics, and errors.
- Default automated tests require no API key and no network access.
- Documentation makes clear that this is a Stage 1.6 developer experience shell aligned to the Stage 1.7 Python oracle and that Stage 2 mobile remains deferred.
