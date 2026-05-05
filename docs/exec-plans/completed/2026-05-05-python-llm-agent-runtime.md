# Python LLM Agent Runtime

Status: completed
Type: implementation
Started: 2026-05-05
Completed: 2026-05-05

## Goal

Add a provider-backed Python Agent runtime around the completed Personal Memory Service so a developer can run a real LLM chat experience while preserving the memory service as a deterministic, governed core.

## Scope

- Add provider-neutral LLM request, response, and tool-call interfaces.
- Add a fake deterministic LLM client for unit tests.
- Add an OpenAI-compatible adapter for real local development use.
- Add a memory tool registry that exposes only audited `PersonalMemoryService` operations.
- Add a chat-turn runtime that retrieves authorized memory, builds context bundles, invokes the model, executes requested memory tools, and returns a response with memory evidence metadata.
- Add an interactive Python chat example using environment-based provider configuration.
- Keep real provider calls out of default tests.

## Architecture

The runtime wraps the memory service; it does not become part of the memory service. `phone_mem.agent_runtime` owns prompt execution, provider adapters, tool schemas, and chat orchestration. `phone_mem.personal_memory_service` continues to own canonical events, storage, permissions, audit, retrieval, lifecycle, and context assembly.

Provider adapters must not import storage modules or query memory directly. Runtime tests should prove that all memory access is mediated by `PersonalMemoryService`.

## Design Inputs

- [Python LLM Agent Runtime](../../design-docs/python-llm-agent-runtime.md)
- [Backend And Runtime Strategy](../../BACKEND.md)
- [Python Reference Guide](../../PYTHON_REFERENCE.md)
- [Retrieval And Context Assembly](../../design-docs/retrieval-and-context-assembly.md)
- [Governance, Permissions, And Audit](../../design-docs/governance-permissions-audit.md)
- [Security](../../SECURITY.md)

## Out Of Scope

- Mobile React Native or TypeScript implementation.
- OS-level Apple Foundation Models, Android AICore, or Gemini Nano integration.
- Cloud sync, provider-side memory, or remote canonical storage.
- Passive sensing, voice, image, or multimodal ingestion.
- Autonomous cross-app actions outside explicit memory tools.
- Default CI tests that require network access or API keys.

## Steps

- [x] Create `phone_mem/agent_runtime/__init__.py` exporting the public runtime interfaces.
- [x] Create `phone_mem/agent_runtime/client.py` with provider-neutral request, response, message, and tool-call value objects.
- [x] Add `tests/test_agent_runtime_client.py` covering request construction, response parsing, and tool-call representation without importing provider SDKs.
- [x] Create `phone_mem/agent_runtime/tools.py` with `MemoryToolRegistry` methods for search, context build, remember, explain, correct, and delete.
- [x] Add `tests/test_agent_runtime_tools.py` proving each memory tool uses service permissions, writes audit records through the service, and preserves structured domain errors.
- [x] Create `phone_mem/agent_runtime/prompts.py` with system prompt assembly that treats retrieved memory as data and preserves source event IDs.
- [x] Add `tests/test_agent_runtime_prompts.py` covering instruction priority, citation metadata, and exclusion of unauthorized memory.
- [x] Create `phone_mem/agent_runtime/runtime.py` with one-turn orchestration over context assembly, fake-client model calls, memory tool execution, and final response shaping.
- [x] Add `tests/test_agent_runtime.py` covering a full deterministic chat turn with retrieved memory and a tool-writing turn that records a new memory.
- [x] Create `phone_mem/agent_runtime/openai_client.py` behind the `LLMClient` interface with environment-based configuration and clear missing-credential errors.
- [x] Add provider adapter tests that mock the SDK boundary and do not perform network calls.
- [x] Create `examples/llm_agent_chat.py` as the real-provider interactive demo.
- [x] Update `docs/PYTHON_REFERENCE.md` with setup, environment variables, fake-vs-real test policy, and example commands.
- [x] Update `README.md`, `README.zh-CN.md`, `ARCHITECTURE.md`, `docs/BACKEND.md`, `docs/ROADMAP.md`, and `docs/PLANS.md` as implementation status changes.

## Validation

- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`
- Manual real-provider smoke test when credentials are available: `uv run python examples/llm_agent_chat.py`

## Acceptance

- The default test suite passes without network access or API keys.
- The memory service has no hard dependency on an LLM provider package.
- The real-provider demo can answer a chat turn using authorized memory context.
- Runtime tool calls for remember, search, explain, correct, and delete are permissioned and audited.
- Missing credentials produce a clear setup error before a provider request is attempted.
- Documentation distinguishes the Stage 1.5 Python runtime spike from the deferred Stage 2 mobile runtime.
