# Stage 1.7 Web Lab Alignment Implementation Plan

> **For agentic workers:** Use `subagent-driven-development` or `executing-plans` to implement this plan task by task. Steps use checkbox syntax for tracking.

Status: completed
Type: implementation
Started: 2026-05-10
Completed: 2026-05-10

## Goal

Align the Python Web Lab with the completed Stage 1.7 Python Agentic Memory Lifecycle Maturation work so the browser lab can inspect and exercise the current Python oracle's runtime capture, hybrid retrieval, hot capsules, relation context, maintenance reports, and quality metrics without becoming a parallel memory implementation.

## Architecture

The Web Lab remains an outer developer-experience shell over `AgentRuntime`, `MemoryToolRegistry`, and `PersonalMemoryService`. It may add routes, DTO fields, templates, and browser controls, but every memory behavior must still come from the Python service/runtime boundary.

The alignment work should expose already-implemented Stage 1.7 behavior, not reimplement it. Session capture, retrieval ranking, capsule construction, relation projection, maintenance reports, audit, and metrics remain owned by `phone_mem.agent_runtime`, `phone_mem.context`, and `phone_mem.personal_memory_service`.

## Tech Stack

- Python 3 with the existing `uv` workflow.
- FastAPI local app in `phone_mem.web_lab`.
- Server-rendered HTML plus vanilla JavaScript.
- SQLite-backed `PersonalMemoryService`.
- Deterministic `unittest` coverage with fake LLM clients and temporary SQLite files.

## Scope

- Expose `AgentTurnResponse.captured_event_ids` through Web Lab chat responses and turn snapshots.
- Make context preview and turn debugging show Stage 1.7 context details: hot memory capsules, relation paths, omitted-memory reasons, token/capsule budget metadata, and evidence IDs.
- Make search results visibly expose hybrid retrieval score explanations and component metadata already returned by `MemoryToolRegistry.search_memory`.
- Add dry-run maintenance inspection routes for `reflect()`, `defrag()`, and `schema_diff()`.
- Add UI controls and debugger tabs for capture, context quality, retrieval explanation, maintenance, audit, and metrics views.
- Update Web Lab documentation to describe the Stage 1.7 debugging surface and keep Stage 2 mobile work deferred.
- Preserve the current no-network test policy for automated tests.

## Non-Goals

- Mobile runtime implementation, React Native, TypeScript service boundaries, or mobile SQLite adapters.
- Production web deployment, login, remote access, multi-user accounts, or persistent chat session management.
- Direct SQL inspection or mutation from Web Lab routes or browser code.
- Reimplementing hybrid ranking, capsule building, relation graph projection, session capture, lifecycle decisions, or maintenance workflows in `phone_mem.web_lab`.
- Automatic semantic or procedural memory promotion from dry-run reflection proposals.
- Provider-backed automated tests.
- Fixture/contract generation UI for future mobile artifacts unless a later plan accepts that scope.

## Design Inputs

- [Python Agentic Memory Lifecycle Maturation](../completed/2026-05-09-python-agentic-memory-lifecycle-maturation.md)
- [Python Web Lab](../../design-docs/python-web-lab.md)
- [Python LLM Agent Runtime](../../design-docs/python-llm-agent-runtime.md)
- [Memory Lifecycle And Data Flow](../../design-docs/memory-lifecycle-and-data-flow.md)
- [Retrieval And Context Assembly](../../design-docs/retrieval-and-context-assembly.md)
- [Personal Memory Service](../../design-docs/personal-memory-service.md)
- [Python Reference Guide](../../PYTHON_REFERENCE.md)
- [Data](../../DATA.md)
- [Security](../../SECURITY.md)

## Files And Responsibilities

- Modify `phone_mem/web_lab/schemas.py`: add `captured_event_ids` to `TurnSnapshot` and keep JSON serialization centralized.
- Modify `phone_mem/web_lab/state.py`: persist captured event IDs in in-process turn snapshots.
- Modify `phone_mem/web_lab/app.py`: include captured event IDs in `/api/chat`; add maintenance routes for reflection, defrag, and schema diff.
- Modify `phone_mem/web_lab/inspector.py`: add `reflect()`, `defrag()`, and `schema_diff()` use cases over `PersonalMemoryService`; keep all outputs JSON-safe through existing serializers.
- Modify `phone_mem/agent_runtime/tools.py`: serialize the full Stage 1.7 context bundle shape needed by the lab, including relation paths and omitted-memory reasons, while preserving the existing tool boundary.
- Modify `phone_mem/web_lab/templates/index.html`: add debugger tabs and controls for capture/context/retrieval/maintenance inspection without turning the page into a product UI.
- Modify `phone_mem/web_lab/static/web_lab.js`: refresh and render new route payloads; keep fetch logic small and generic.
- Modify `phone_mem/web_lab/static/web_lab.css`: keep the dense developer-lab layout stable after adding tabs and controls.
- Modify `tests/test_web_lab_state.py`: cover captured event IDs in snapshots.
- Modify `tests/test_web_lab_inspector.py`: cover maintenance report serialization and Stage 1.7 context payload fields.
- Modify `tests/test_web_lab_routes.py`: cover `/api/chat` captured IDs, maintenance routes, and HTML debugger controls.
- Modify `docs/design-docs/python-web-lab.md`: update Stage 1.6 wording to describe the Stage 1.7 aligned debugging surface.
- Modify `docs/PYTHON_REFERENCE.md`: document the aligned Web Lab inspection capabilities.
- Modify `docs/PLANS.md`: track this plan as active, then move it to completed when implementation and validation pass.

## Steps

- [x] Add captured event IDs to turn snapshots.
  - Files: `phone_mem/web_lab/schemas.py`, `phone_mem/web_lab/state.py`, `phone_mem/web_lab/app.py`.
  - Tests: `tests/test_web_lab_state.py`, `tests/test_web_lab_routes.py`.
  - Add `captured_event_ids: list[str]` to `TurnSnapshot`.
  - In `LabState.run_chat_turn(...)`, copy `response.captured_event_ids` into successful snapshots.
  - In `/api/chat`, include `captured_event_ids=response.captured_event_ids` in the response payload.
  - Add a fake-client test where `AgentRuntime` captures a turn-boundary event and the route payload plus `/api/turns` both expose that event ID.
  - Validate with `uv run python -m unittest tests.test_web_lab_state tests.test_web_lab_routes`.

- [x] Complete Stage 1.7 context serialization for the lab.
  - Files: `phone_mem/agent_runtime/tools.py`, `tests/test_agent_runtime_tools.py`, `tests/test_web_lab_inspector.py`.
  - Extend `MemoryToolRegistry.build_memory_context(...)` output to include:
    - `omitted_memory` from the `ContextBundle`;
    - `relation_paths` with relation type, source/target labels when available, compression score, evidence event IDs, and path metadata already present on the domain object;
    - existing `hot_memory_capsules`, `safety_metadata`, and `token_budget`.
  - Do not query SQLite or rebuild relation paths inside `phone_mem.web_lab`.
  - Add tests that call context preview through `MemoryInspector` and assert the payload contains `hot_memory_capsules`, `omitted_memory`, `relation_paths`, `safety_metadata["capsule_budget"]`, and evidence IDs.
  - Validate with `uv run python -m unittest tests.test_agent_runtime_tools tests.test_web_lab_inspector`.

- [x] Add maintenance report use cases and routes.
  - Files: `phone_mem/web_lab/inspector.py`, `phone_mem/web_lab/app.py`, `tests/test_web_lab_inspector.py`, `tests/test_web_lab_routes.py`.
  - Add `MemoryInspector.reflect()`, `MemoryInspector.defrag()`, and `MemoryInspector.schema_diff()` methods.
  - Route them as:
    - `GET /api/maintenance/reflect`
    - `GET /api/maintenance/defrag`
    - `GET /api/maintenance/schema-diff`
  - Return JSON-safe dataclass output with `mutates_store` visible so the UI makes dry-run behavior explicit.
  - Add tests proving all three routes return `200`, are JSON serializable, and do not add memory events when run.
  - Validate with `uv run python -m unittest tests.test_web_lab_inspector tests.test_web_lab_routes`.

- [x] Make retrieval explanations easy to inspect.
  - Files: `phone_mem/web_lab/templates/index.html`, `phone_mem/web_lab/static/web_lab.js`, `tests/test_web_lab_routes.py`.
  - Keep `/api/search` backed by `MemoryToolRegistry.search_memory(...)`.
  - Add UI affordance in the Memory Inspector for search output that keeps `score`, `explanation`, `score_components`, and `score_weights` visible in the rendered JSON.
  - Add route/UI tests that assert the HTML contains the retrieval explanation control text or tab target, and API tests that search output includes `explanation`.
  - Validate with `uv run python -m unittest tests.test_web_lab_routes`.

- [x] Add Stage 1.7 debugger tabs.
  - Files: `phone_mem/web_lab/templates/index.html`, `phone_mem/web_lab/static/web_lab.js`, `phone_mem/web_lab/static/web_lab.css`, `tests/test_web_lab_routes.py`.
  - Keep the existing Turns, Audit, and Metrics tabs.
  - Add tabs or equivalent compact controls for:
    - Capture: latest turn `captured_event_ids` and related audit entries;
    - Context: latest turn memory context, hot capsules, omitted-memory reasons, and budget metadata;
    - Maintenance: reflect, defrag, and schema-diff dry-run reports.
  - Keep the UI as a developer lab: dense, JSON-forward, and single-page.
  - Update JavaScript refresh behavior so one refresh updates turns, audit, metrics, and maintenance payloads without requiring a chat turn.
  - Validate with `uv run python -m unittest tests.test_web_lab_routes`.

- [x] Update Web Lab documentation for Stage 1.7 alignment.
  - Files: `docs/design-docs/python-web-lab.md`, `docs/PYTHON_REFERENCE.md`.
  - Describe the Web Lab as a Stage 1.6 developer shell that has been aligned to the completed Stage 1.7 Python oracle.
  - Document that the lab can inspect runtime capture, hybrid retrieval explanations, hot capsules, relation context metadata, dry-run maintenance reports, metrics, audit, correction, and deletion.
  - Keep the architecture boundary explicit: Web Lab calls service/runtime APIs and does not own memory algorithms.
  - Keep Stage 2 mobile runtime deferred.
  - Validate with `uv run python scripts/validate_docs.py`.

- [x] Run focused verification.
  - Commands:
    - `uv run python -m unittest tests.test_agent_runtime_tools tests.test_web_lab_state tests.test_web_lab_inspector tests.test_web_lab_routes`
    - `uv run python scripts/validate_docs.py`
  - Confirm all focused Web Lab and tool-boundary tests pass.

- [x] Run final verification and close the plan.
  - Commands:
    - `uv run python -m unittest discover -s tests`
    - `uv run python scripts/validate_docs.py`
  - Manual provider-backed smoke test when credentials are available:
    - `OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run python examples/web_lab.py --reload`
  - Move this plan to `docs/exec-plans/completed/` only after tests pass and docs reflect final behavior.
  - Update `docs/PLANS.md` so Active returns to no active execution plan.

## Validation

- `uv run python -m unittest tests.test_agent_runtime_tools`
- `uv run python -m unittest tests.test_web_lab_state`
- `uv run python -m unittest tests.test_web_lab_inspector`
- `uv run python -m unittest tests.test_web_lab_routes`
- `uv run python -m unittest tests.test_agent_runtime_tools tests.test_web_lab_state tests.test_web_lab_inspector tests.test_web_lab_routes`
- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`
- Manual provider-backed smoke test when credentials are available: `OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run python examples/web_lab.py --reload`

## Acceptance

- Web Lab chat responses and turn snapshots expose `captured_event_ids`.
- The Turn Debugger makes runtime capture, memory context, hot memory capsules, omitted-memory reasons, token/capsule budget metadata, tool results, evidence IDs, audit records, and domain errors inspectable.
- Memory Inspector search exposes hybrid retrieval scores and score-component explanations already produced by the Python retriever.
- Context preview exposes Stage 1.7 context bundle details without recomputing retrieval, capsules, or relation projections in `phone_mem.web_lab`.
- Maintenance routes expose dry-run reflection, defrag, and schema-diff reports with `mutates_store` visible.
- Metrics remain available and show Stage 1.7 quality dimensions after capture, retrieval, context, deletion, audit, and maintenance operations.
- Route handlers and browser code do not directly read or write SQLite.
- Automated tests require no provider credentials or network access.
- Documentation clearly states that this is a Web Lab alignment over the completed Stage 1.7 Python oracle and that Stage 2 mobile runtime work remains deferred.
- Full test suite and documentation validation pass.
