# Python Web Lab

Status: active
Type: implementation
Started: 2026-05-05

## Goal

Build a local developer Web Lab around the completed Python Personal Memory Service and Python LLM Agent Runtime so a developer can chat with the Agent, inspect memory behavior, and discover retrieval, lifecycle, and audit issues before mobile runtime work resumes.

## Scope

- Add a FastAPI-based local Web Lab with server-rendered HTML and minimal vanilla JavaScript.
- Reuse the existing Python `PersonalMemoryService`, `SQLiteMemoryStore`, `MemoryToolRegistry`, `AgentRuntime`, and OpenAI-compatible client.
- Use a file-backed SQLite database at `.phone-mem-lab/memory.sqlite3` by default.
- Keep the default runtime path real-first while ensuring automated tests use fake clients and temporary SQLite files.
- Add a single-screen Hybrid Lab with chat, memory inspector, and turn debugger panels.
- Expose turn-level memory context, tool results, evidence IDs, recent audit records, and structured errors.
- Update documentation to describe the Web Lab as a Stage 1.6 developer experience track.

## Architecture

The Web Lab is an outer experience shell. It owns HTTP routes, templates, static assets, local app state, file-backed service startup, and in-process turn snapshots. It must not become a parallel memory implementation.

`phone_mem.web_lab` may create and hold a `PersonalMemoryService`, but all memory behavior shown in the UI must come from the Python reference service and Python Agent runtime. The UI must not read or write SQLite directly.

```text
Browser
  |
  v
phone_mem.web_lab
  |
  +--> AgentRuntime
  |       +--> OpenAICompatibleClient or fake test client
  |       +--> MemoryToolRegistry
  |
  +--> PersonalMemoryService
          |
          v
     SQLiteMemoryStore
```

## Design Inputs

- [Python Web Lab](../../design-docs/python-web-lab.md)
- [Python LLM Agent Runtime](../../design-docs/python-llm-agent-runtime.md)
- [Python Reference Guide](../../PYTHON_REFERENCE.md)
- [Backend And Runtime Strategy](../../BACKEND.md)
- [Governance, Permissions, And Audit](../../design-docs/governance-permissions-audit.md)
- [Retrieval And Context Assembly](../../design-docs/retrieval-and-context-assembly.md)

## Out Of Scope

- Mobile React Native or TypeScript implementation.
- Production web deployment, login, remote access, or multi-user support.
- Reimplementing memory service behavior outside Python.
- Direct SQL reads or writes from route handlers or UI code.
- Cloud sync, provider-side memory, vector databases, embeddings, or graph visualization.
- Persistent chat transcript storage beyond in-process developer session snapshots.
- Default tests that require network access or provider API keys.

## Files And Responsibilities

- Modify `pyproject.toml` and `uv.lock`: add FastAPI, Uvicorn, and any explicit HTTP test dependency required by FastAPI `TestClient`.
- Modify `phone_mem/agent_runtime/runtime.py`: add turn observability to `AgentTurnResponse` without changing memory service behavior.
- Modify `tests/test_agent_runtime.py`: verify `AgentTurnResponse` exposes the memory context used for the turn.
- Create `phone_mem/web_lab/__init__.py`: export the app factory and lab state types needed by examples and tests.
- Create `phone_mem/web_lab/state.py`: own `LabState`, runtime construction, file-backed SQLite service startup, grants, shutdown, and turn snapshot storage.
- Create `phone_mem/web_lab/schemas.py`: define request and response DTOs for route serialization.
- Create `phone_mem/web_lab/inspector.py`: provide memory list, search, context preview, explain, correct, delete, audit, and metrics use cases over the service boundary.
- Create `phone_mem/web_lab/app.py`: create the FastAPI app, register HTML and JSON routes, mount static assets, and wire app lifetime to `LabState`.
- Create `phone_mem/web_lab/templates/index.html`: render the single-screen Hybrid Lab.
- Create `phone_mem/web_lab/static/web_lab.css`: provide a dense developer-lab layout with stable three-panel sizing.
- Create `phone_mem/web_lab/static/web_lab.js`: submit forms, refresh memory/audit state, and render turn debugger payloads.
- Create `examples/web_lab.py`: optional local launch wrapper around the FastAPI app.
- Create `tests/test_web_lab_state.py`: cover lab state startup, grants, file-backed persistence, fake runtime injection, and shutdown.
- Create `tests/test_web_lab_inspector.py`: cover inspector operations through service APIs.
- Create `tests/test_web_lab_routes.py`: cover HTML and JSON routes with fake clients and temporary databases.
- Modify `docs/PYTHON_REFERENCE.md`: document Web Lab setup, run command, environment variables, database path, and test policy.
- Modify `README.md`, `README.zh-CN.md`, `docs/BACKEND.md`, `docs/ROADMAP.md`, and `docs/PLANS.md`: mark Stage 1.6 Web Lab as active developer experience work while keeping Stage 2 mobile deferred.

## Steps

- [ ] Add Web Lab dependencies.
  - Files: `pyproject.toml`, `uv.lock`.
  - Add FastAPI and Uvicorn as project dependencies.
  - Add an explicit HTTP test dependency if FastAPI `TestClient` requires it in this environment.
  - Validate with `uv run python -c "import fastapi, uvicorn; print(fastapi.__version__)"`.

- [ ] Add runtime turn observability.
  - Files: `phone_mem/agent_runtime/runtime.py`, `tests/test_agent_runtime.py`.
  - Extend `AgentTurnResponse` with `memory_context: dict[str, Any] | None = None`.
  - Return the initial `memory_context` for no-tool and tool-call turns.
  - Add tests proving `response.memory_context["snippets"]` and `response.memory_context["evidence_event_ids"]` match the context used during the turn.
  - Validate with `uv run python -m unittest tests.test_agent_runtime`.

- [ ] Add Web Lab state construction.
  - Files: `phone_mem/web_lab/__init__.py`, `phone_mem/web_lab/state.py`, `tests/test_web_lab_state.py`.
  - Implement default constants for `web_lab_agent`, `system_assistant`, and `.phone-mem-lab/memory.sqlite3`.
  - Implement `LabState.create(...)` for file-backed SQLite startup, schema initialization, permission grant, tool registry construction, and runtime construction.
  - Allow tests to inject an `LLMClient` and temporary database path.
  - Implement `LabState.close()`.
  - Validate with `uv run python -m unittest tests.test_web_lab_state`.

- [ ] Add route and inspector schemas.
  - Files: `phone_mem/web_lab/schemas.py`, `tests/test_web_lab_inspector.py`.
  - Define small dataclasses or typed dictionaries for chat turn requests, chat turn responses, memory operation responses, error payloads, lab metadata, and turn snapshots.
  - Ensure every response can be serialized to JSON without custom framework hooks.
  - Validate with `uv run python -m unittest tests.test_web_lab_inspector`.

- [ ] Add Memory Inspector use cases.
  - Files: `phone_mem/web_lab/inspector.py`, `tests/test_web_lab_inspector.py`.
  - Implement memory listing through `service.store.query_events()` and domain `to_dict()` serialization.
  - Implement search and context preview through `MemoryToolRegistry`.
  - Implement explain, correct, and delete through `MemoryToolRegistry` or `PersonalMemoryService` APIs.
  - Implement audit and metrics views through `service.audit()` and `service.metrics_snapshot()`.
  - Preserve structured domain errors in returned payloads.
  - Validate with `uv run python -m unittest tests.test_web_lab_inspector`.

- [ ] Add FastAPI app and JSON routes.
  - Files: `phone_mem/web_lab/app.py`, `tests/test_web_lab_routes.py`.
  - Implement `create_app(state: LabState | None = None) -> FastAPI`.
  - Add `GET /` for the lab page.
  - Add JSON routes for lab metadata, chat turns, turn snapshots, memories, search, context preview, explain, correct, delete, audit, and metrics.
  - Ensure route handlers call `LabState` and inspector use cases rather than directly embedding memory logic.
  - Validate with `uv run python -m unittest tests.test_web_lab_routes`.

- [ ] Add the single-screen Hybrid Lab UI.
  - Files: `phone_mem/web_lab/templates/index.html`, `phone_mem/web_lab/static/web_lab.css`, `phone_mem/web_lab/static/web_lab.js`, `tests/test_web_lab_routes.py`.
  - Render Chat Panel, Memory Inspector, Turn Debugger, and Lab Header.
  - Use stable three-panel layout sizing for desktop developer use.
  - Implement form submission and panel refreshes with vanilla JavaScript.
  - Display model, provider status, database path, caller, source app, evidence IDs, memory context, tool results, audit records, and errors.
  - Validate with `uv run python -m unittest tests.test_web_lab_routes`.

- [ ] Add the optional launch wrapper.
  - Files: `examples/web_lab.py`, `tests/test_web_lab_routes.py`.
  - Implement a small wrapper that imports `phone_mem.web_lab.app:create_app` and runs Uvicorn.
  - Keep the canonical command documented as `uv run uvicorn phone_mem.web_lab.app:create_app --factory --reload`.
  - Validate with an import-only or argument-level test that does not start a network server.

- [ ] Update user-facing documentation.
  - Files: `README.md`, `README.zh-CN.md`, `docs/PYTHON_REFERENCE.md`, `docs/BACKEND.md`, `docs/ROADMAP.md`, `docs/PLANS.md`.
  - Document the Web Lab as Stage 1.6 active developer experience work.
  - Document run commands, environment variables, default database path, reset caution, and fake-client test policy.
  - Keep mobile runtime status deferred.
  - Validate with `uv run python scripts/validate_docs.py`.

- [ ] Run final verification.
  - Commands:
    - `uv run python -m unittest discover -s tests`
    - `uv run python scripts/validate_docs.py`
  - Manual real-provider smoke test when credentials are available:
    - `OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run uvicorn phone_mem.web_lab.app:create_app --factory --reload`
  - Confirm the browser page can complete a chat turn, show memory context, list memories, run search/context/explain/correct/delete, show audit, and preserve SQLite memory across restart.

## Validation

- `uv run python -m unittest tests.test_agent_runtime`
- `uv run python -m unittest tests.test_web_lab_state`
- `uv run python -m unittest tests.test_web_lab_inspector`
- `uv run python -m unittest tests.test_web_lab_routes`
- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`
- Manual real-provider smoke test when credentials are available: `OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run uvicorn phone_mem.web_lab.app:create_app --factory --reload`

## Acceptance

- The local Web Lab opens in a browser and shows Chat Panel, Memory Inspector, Turn Debugger, and Lab Header.
- Chat turns use the existing Python `AgentRuntime` and do not bypass `MemoryToolRegistry`.
- The default provider path is real-first and OpenAI-compatible.
- Automated tests use fake clients and require no API key or network access.
- Memory persists across restarts through `.phone-mem-lab/memory.sqlite3` by default.
- The Memory Inspector can list memories, search, preview context, explain, correct, delete, show audit records, and show metrics.
- The Turn Debugger shows the exact memory context attached to `AgentTurnResponse`, tool results, evidence IDs, recent audit records, provider errors, and domain errors.
- Route handlers and UI code do not perform direct SQL operations.
- Documentation distinguishes Stage 1.6 Python Web Lab work from deferred Stage 2 mobile implementation.
- Standard tests and documentation validation pass.
