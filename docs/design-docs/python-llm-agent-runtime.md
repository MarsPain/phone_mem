# Python LLM Agent Runtime

## Purpose

The Python LLM Agent Runtime is a Stage 1.5 planning track for making the reference memory service feel like a real Agent without changing the phone-first product architecture. It adds prompt execution and provider adapters around the completed Python Personal Memory Service so a developer can chat with an Agent that retrieves, cites, writes, corrects, and deletes governed memory.

This track is a developer-machine runtime spike. It is not the production mobile runtime, not an OS service, and not a replacement for the deterministic memory core.

## Product Goal

The first useful experience should be a terminal chat Agent that can:

- answer the user with relevant scoped memory;
- write new memory through explicit memory-service operations;
- explain which memory shaped a response;
- correct or delete memory by going through audited service APIs;
- keep provider details outside the Personal Memory Service.

The experience should demonstrate the product loop that the mobile runtime will later need: task input, governed retrieval, context assembly, model reasoning, tool use, memory lifecycle action, and auditability.

## Architecture Boundary

```text
examples/llm_agent_chat.py
        |
        v
phone_mem.agent_runtime.AgentRuntime
        |
        +--> phone_mem.agent_runtime.LLMClient
        |        +--> OpenAI-compatible adapter
        |        +--> fake deterministic test client
        |
        +--> phone_mem.agent_runtime.MemoryToolRegistry
                 |
                 v
          PersonalMemoryService
```

The runtime may call the service. The provider adapter may not. The LLM receives context bundles and tool schemas, never the raw SQLite store or unfiltered memory list.

## Proposed Python Modules

- `phone_mem/agent_runtime/client.py`: provider-neutral `LLMClient`, request, response, and tool-call value objects.
- `phone_mem/agent_runtime/openai_client.py`: OpenAI-compatible chat or responses adapter selected by environment configuration.
- `phone_mem/agent_runtime/runtime.py`: chat-turn orchestration over retrieval, context assembly, model call, tool execution, and final answer.
- `phone_mem/agent_runtime/tools.py`: audited memory tools backed only by `PersonalMemoryService`.
- `phone_mem/agent_runtime/prompts.py`: system instructions that mark retrieved memory as data, preserve instruction priority, and require citation metadata.
- `examples/llm_agent_chat.py`: interactive chat demo for real provider use.
- `tests/test_agent_runtime_*.py`: fake-client unit tests for orchestration, tool authorization, prompt shaping, and provider-independent errors.

## Provider Policy

The first implementation should use an OpenAI-compatible adapter because that keeps the API surface small while leaving room for local and private-compute backends. The dependency should sit behind `LLMClient`; tests must use a fake client and must not require network access or API keys.

Runtime configuration should come from environment variables such as:

- `PHONE_MEM_LLM_PROVIDER`;
- `PHONE_MEM_LLM_MODEL`;
- `OPENAI_API_KEY` or provider-specific compatible credentials;
- optional base URL for OpenAI-compatible local or hosted providers.

Missing credentials should fail with a clear setup error before a chat turn starts.

## Memory Tool Policy

The runtime should expose a narrow memory tool set first:

- `search_memory(query, top_k)`;
- `build_memory_context(query, budget)`;
- `remember(text, entities, privacy_level, memory_layer)`;
- `explain_memory(event_id)`;
- `correct_memory(event_id, replacement_text)`;
- `delete_memory(event_id, reason)`.

Every tool must call `PersonalMemoryService` with a caller identity and existing grants. Tool failures must preserve domain errors such as permission denial and missing events instead of turning them into generic provider errors.

## Safety Rules

- Prompt execution must consume only authorized context bundles and explicit tool results.
- Retrieved memory is model input data, not developer or system instruction.
- The runtime must preserve source event IDs in responses or in response metadata.
- Provider adapters must not read from storage, construct memory events directly, or bypass permissions.
- Real API integration tests must be optional and skipped unless explicit credentials are present.
- Sensitive memory should default to local-only behavior; external provider calls require an allowed processing policy before this runtime is used with such data.

## Development Sequence

1. Add provider-neutral runtime interfaces and fake-client tests.
2. Add memory tool registry tests proving all tool calls go through service permissions and audit.
3. Add orchestration for one chat turn: retrieve, build context, call model, execute memory tools, produce final answer.
4. Add OpenAI-compatible adapter and credential validation.
5. Add interactive chat example and documentation.
6. Add optional manual integration instructions for real API use.

## Non-Goals

- Mobile React Native runtime work.
- Direct SQLite access from the Agent runtime.
- Always-on sensing or multimodal ingestion.
- Autonomous cross-app action execution.
- Cloud sync, private-compute storage, or provider-side memory.
- Production-grade conversation persistence beyond what is needed for the demo loop.

## Acceptance

- The deterministic memory service remains provider-independent.
- Unit tests cover runtime behavior without network access.
- A developer with credentials can run a real chat demo locally.
- Memory read/write/correction/delete operations remain permissioned and audited.
- The docs make clear that this is Stage 1.5 Python runtime exploration, while Stage 2 mobile remains deferred.
