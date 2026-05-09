# phone-mem

Language: English | [中文](README.zh.md)

`phone-mem` is the architecture and prototype repository for smartphone Agent Memory. The project goal is to build a local-first memory system on the phone that manages user memory with an agentic lifecycle: it understands and maintains long-term preferences, events, context, and operating habits from smartphone scenarios, then exposes governed memory capabilities to broader Agent applications.

The repository now contains a completed deterministic Python reference Personal Memory Service, a completed Stage 1.5 Python LLM Agent runtime spike for real provider-backed chat over governed memory APIs, a completed Stage 1.6 local Python Web Lab for memory inspection and turn debugging, and architecture context for the future mobile runtime. Stage 2 mobile implementation remains deferred until a separate plan is accepted.

## What Exists Now

- `phone_mem.personal_memory_service`: canonical event construction, SQLite-backed storage, governed search, correction, deletion, audit, lifecycle explanation, and metrics.
- `phone_mem.context`: runtime-neutral context bundle assembly and budget accounting.
- `phone_mem.governance`: permission scopes, memory views, audit records, and access checks.
- `phone_mem.agent_runtime`: provider-neutral Agent runtime contracts, memory tools, prompt assembly, and an OpenAI-compatible client adapter.
- `phone_mem.web_lab`: local browser lab for chat, memory inspection, context previews, correction, deletion, audit, metrics, and turn debugging.
- `mobile/`: TypeScript boundary files and Python-backed contract fixtures for the deferred mobile runtime.

## Quick Start

Install dependencies with `uv`, then run the deterministic checks:

```bash
uv run python main.py
uv run python scripts/validate_docs.py
uv run python -m unittest discover -s tests
```

Run deterministic demos that do not call an LLM provider:

```bash
uv run python examples/agent_memory_demo.py
uv run python examples/agent_memory_repl.py
uv run python examples/python_reference_walkthrough.py
uv run python examples/file_backed_sqlite_walkthrough.py
uv run python examples/retrieval_selector_walkthrough.py
```

Run provider-backed Agent experiences:

```bash
OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run python examples/llm_agent_chat.py
OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run python examples/web_lab.py --reload
```

The Web Lab stores local development memory in `.phone-mem-lab/memory.sqlite3` by default. The Python reference remains local-first and deterministic; provider calls live only at the Agent runtime/demo boundary.

## Architecture Snapshot

The Python reference is the executable oracle for future mobile parity. `PersonalMemoryService` owns durable memory events, permissions, audit, tombstones, retrieval, and lifecycle operations. `context` converts governed retrieval results into runtime-neutral bundles. `agent_runtime` lets a chat Agent use memory through scoped tools without making the memory core provider-dependent. `web_lab` exposes the same service and runtime through a local developer UI.

External agents should consume governed views and context bundles, not the raw global memory store. The future phone runtime is expected to preserve this boundary while replacing Python infrastructure with mobile-native storage, permissions, and runtime integration.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): top-level architecture map.
- [AGENTS.md](AGENTS.md): working map for coding agents.
- [docs/README.md](docs/README.md): detailed documentation index.
- [docs/PYTHON_REFERENCE.md](docs/PYTHON_REFERENCE.md): practical Python reference usage guide.
- [docs/design-docs/python-llm-agent-runtime.md](docs/design-docs/python-llm-agent-runtime.md): Python LLM Agent runtime design.
- [docs/design-docs/python-web-lab.md](docs/design-docs/python-web-lab.md): Stage 1.6 local Web Lab design.
- [docs/design-docs/smartphone-agent-memory.md](docs/design-docs/smartphone-agent-memory.md): smartphone Agent Memory development design.
- [docs/references/source-review.md](docs/references/source-review.md): deep review, distilled insights, and corrections for the source PDF.
- [docs/references/research-review-2026.md](docs/references/research-review-2026.md): v2 research basis across agent memory, on-device LLM systems, and Apple/Android platform constraints.
- [mobile/README.md](mobile/README.md): Stage 2 mobile runtime prototype boundary.

## Current Stage

Stage 1, the Python reference maturation track, the Stage 1.5 Python LLM Agent runtime spike, and the Stage 1.6 Python Web Lab are complete. The Python code under `phone_mem/` is now the executable oracle for future mobile parity. The `phone_mem.agent_runtime` boundary supports real LLM API demos while keeping the memory core provider-independent, and `phone_mem.web_lab` provides a local browser surface for chat, memory inspection, and turn debugging.

Stage 2 mobile implementation is deferred. The repository currently has TypeScript boundary files and Python-backed contract fixtures, but no React Native app, mobile SQLite adapter, or TypeScript test toolchain yet.

There is no active execution plan at the moment; completed and deferred tracks are listed in [docs/PLANS.md](docs/PLANS.md).
