# Python Agent Session Multi-Turn Chat Implementation Plan

> **For agentic workers:** Use `subagent-driven-development` or `executing-plans` to implement this plan task by task. Steps use checkbox syntax for tracking.

Status: completed
Type: implementation
Started: 2026-05-10
Completed: 2026-05-10

## Goal

Make the Python LLM chat demo and Web Lab default to session-scoped multi-turn chat while preserving the memory service boundary: transient transcript helps current reasoning, and durable memory still goes through governed memory tools, lifecycle checks, permissions, and audit.

## Architecture

Add a small `AgentSession` wrapper around `AgentRuntime`. `AgentRuntime` remains the deterministic one-turn orchestrator, but accepts optional recent conversation messages that are explicitly marked as transient context in the prompt. CLI and Web Lab own session lifetime and use `AgentSession` by default.

Conversation history is in-process only. It is not persisted to SQLite, not treated as retrieved memory, and not allowed to replace `remember`, `correct_memory`, or `delete_memory` flows.

## Tech Stack

- Python 3 with the existing `uv` workflow.
- Provider-neutral `phone_mem.agent_runtime` interfaces.
- FastAPI local Web Lab state in `phone_mem.web_lab`.
- Deterministic `unittest` coverage with `FakeLLMClient`; no provider credentials or network access in automated tests.

## Scope

- Add session-scoped recent conversation history for LLM prompt assembly.
- Make `examples/llm_agent_chat.py` and `phone_mem.web_lab.state.LabState` use the session wrapper by default.
- Keep history window bounded by message count.
- Expose enough request/debug state in tests to prove prior turns are sent as transient context.
- Update docs to distinguish transient conversation context from governed memory.

## Non-Goals

- Persistent transcript storage.
- Multi-conversation management, user accounts, or conversation IDs.
- Provider-side memory.
- Automatic promotion of raw transcript into durable memory.
- Token-based compaction or LLM-generated session summaries.
- Mobile runtime implementation.

## Design Inputs

- [Python LLM Agent Runtime](../../design-docs/python-llm-agent-runtime.md)
- [Python Web Lab](../../design-docs/python-web-lab.md)
- [Memory Lifecycle And Data Flow](../../design-docs/memory-lifecycle-and-data-flow.md)
- [Agent Memory Flow Architecture](../../AGENT_MEMORY_FLOW_ARCHITECTURE.md)
- [Python Reference Guide](../../PYTHON_REFERENCE.md)
- [Security](../../SECURITY.md)

## Files And Responsibilities

- Create `phone_mem/agent_runtime/session.py`: session-scoped conversation history, bounded window selection, and turn recording.
- Modify `phone_mem/agent_runtime/prompts.py`: accept optional recent conversation messages and serialize them as transient context.
- Modify `phone_mem/agent_runtime/runtime.py`: accept optional conversation context without owning session state.
- Modify `phone_mem/agent_runtime/__init__.py`: export `AgentSession`.
- Modify `examples/llm_agent_chat.py`: use `AgentSession` in the default interactive loop.
- Modify `phone_mem/web_lab/state.py`: create and use `AgentSession`; keep existing turn snapshots for debugging.
- Modify tests under `tests/`: cover prompt shaping, runtime forwarding, session window behavior, CLI default multi-turn behavior, and Web Lab session behavior.
- Modify docs: describe default session-scoped multi-turn behavior and its non-persistent boundary.
- Modify `docs/PLANS.md`: track this plan as active, then move it to completed when implementation and validation pass.

## Steps

- [x] Add prompt-level transient conversation context.
  - Files: `phone_mem/agent_runtime/prompts.py`, `tests/test_agent_runtime_prompts.py`.
  - Add a failing test proving `build_agent_messages(...)` includes prior user/assistant messages under a system message labelled as transient conversation context.
  - Implement the minimal prompt change.
  - Validate with `uv run python -m unittest tests.test_agent_runtime_prompts`.

- [x] Let the one-turn runtime receive explicit recent conversation.
  - Files: `phone_mem/agent_runtime/runtime.py`, `tests/test_agent_runtime.py`.
  - Add a failing test proving `AgentRuntime.run_turn(..., conversation_messages=[...])` forwards prior messages to the first provider request.
  - Keep tool-followup requests based on the same initial messages plus tool results.
  - Validate with `uv run python -m unittest tests.test_agent_runtime`.

- [x] Add `AgentSession`.
  - Files: `phone_mem/agent_runtime/session.py`, `phone_mem/agent_runtime/__init__.py`, `tests/test_agent_runtime_session.py`.
  - Add failing tests for:
    - first turn sends no prior conversation;
    - second turn sends the previous user and assistant messages;
    - bounded history keeps the most recent messages only.
  - Implement the minimal session wrapper over `AgentRuntime`.
  - Validate with `uv run python -m unittest tests.test_agent_runtime_session`.

- [x] Make the CLI demo session-based by default.
  - Files: `examples/llm_agent_chat.py`, `tests/test_llm_agent_chat_example.py`.
  - Add a failing test using a runtime fake that proves the default loop uses an `AgentSession` and carries previous turns into later `run_turn` calls.
  - Preserve the injected-runtime test path for simple deterministic tests.
  - Validate with `uv run python -m unittest tests.test_llm_agent_chat_example`.

- [x] Make the Web Lab session-based by default.
  - Files: `phone_mem/web_lab/state.py`, `tests/test_web_lab_state.py`, `tests/test_web_lab_routes.py`.
  - Add failing tests proving two Web Lab chat turns send prior turn context to the fake LLM.
  - Keep `turn_snapshots` as debugger state, not as provider prompt source.
  - Validate with `uv run python -m unittest tests.test_web_lab_state tests.test_web_lab_routes`.

- [x] Update documentation.
  - Files: `docs/design-docs/python-llm-agent-runtime.md`, `docs/design-docs/python-web-lab.md`, `docs/PYTHON_REFERENCE.md`, `docs/AGENT_MEMORY_FLOW_ARCHITECTURE.md`.
  - Document that default chat is session-scoped multi-turn.
  - Document that conversation context is transient and not durable memory.
  - Keep Stage 2 mobile work deferred.
  - Validate with `uv run python scripts/validate_docs.py`.

- [x] Run final verification and close the plan.
  - Commands:
    - `uv run python -m unittest tests.test_agent_runtime_prompts tests.test_agent_runtime tests.test_agent_runtime_session tests.test_llm_agent_chat_example tests.test_web_lab_state tests.test_web_lab_routes`
    - `uv run python -m unittest discover -s tests`
    - `uv run python scripts/validate_docs.py`
  - Move this plan to `docs/exec-plans/completed/` only after tests pass and docs reflect final behavior.
  - Update `docs/PLANS.md` so Active returns to no active execution plan.

## Validation

- `uv run python -m unittest tests.test_agent_runtime_prompts`
- `uv run python -m unittest tests.test_agent_runtime`
- `uv run python -m unittest tests.test_agent_runtime_session`
- `uv run python -m unittest tests.test_llm_agent_chat_example`
- `uv run python -m unittest tests.test_web_lab_state tests.test_web_lab_routes`
- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`

## Acceptance

- CLI chat defaults to session-scoped multi-turn behavior.
- Web Lab chat defaults to session-scoped multi-turn behavior.
- `AgentRuntime` remains usable as a one-turn primitive with explicit optional conversation context.
- Recent conversation context is labelled as transient and never serialized as authorized memory.
- Durable memory writes, corrections, deletions, permissions, lifecycle decisions, and audit stay behind `PersonalMemoryService` and memory tools.
- No automated tests require provider credentials or network access.
- Documentation clearly distinguishes transient conversation context from governed memory.
