# phone-mem

Language: English | [中文](README.zh.md)

`phone-mem` is the architecture and prototype repository for smartphone Agent Memory. The project goal is to build a local-first memory system on the phone that manages user memory with an agentic lifecycle: it understands and maintains long-term preferences, events, context, and operating habits from smartphone scenarios, then exposes governed memory capabilities to broader Agent applications.

The repository now contains a completed deterministic Python reference Personal Memory Service, a completed Stage 1.5 Python LLM Agent runtime spike for real provider-backed chat over governed memory APIs, a completed Stage 1.6 local Python Web Lab for memory inspection and turn debugging, and a completed Stage 1.7 Python-only maturation track for deeper agentic memory lifecycle behavior. Stage 2 mobile implementation remains deferred until a separate mobile plan is accepted; stale mobile TypeScript boundary files are intentionally not retained.

## What Exists Now

- `phone_mem.personal_memory_service`: canonical event construction, SQLite-backed storage, governed hybrid search, correction, deletion, audit, lifecycle explanation, maintenance reports, and quality metrics.
- `phone_mem.context`: runtime-neutral context bundle assembly, hot memory capsules, relation paths, and budget accounting.
- `phone_mem.governance`: permission scopes, memory views, audit records, and access checks.
- `phone_mem.agent_runtime`: provider-neutral Agent runtime contracts, memory tools, prompt assembly, and an OpenAI-compatible client adapter.
- `phone_mem.web_lab`: local browser lab for chat, memory inspection, context previews, correction, deletion, audit, metrics, and turn debugging.
- `docs/exec-plans/completed/`: completed Stage 1.7 Python Agentic Memory Lifecycle Maturation plan.

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

## Current Stage

Stage 1, the Python reference maturation track, the Stage 1.5 Python LLM Agent runtime spike, the Stage 1.6 Python Web Lab, and Stage 1.7 Python Agentic Memory Lifecycle Maturation are complete. The Python code under `phone_mem/` remains the executable oracle for future mobile parity, now including runtime memory protocol, governed session capture, hot capsules, hybrid retrieval, relation projections, maintenance workflows, quality metrics, and refreshed future-mobile fixtures.

Stage 2 mobile implementation is deferred. The repository currently has no retained mobile TypeScript boundary, React Native app, mobile SQLite adapter, or TypeScript test toolchain. Future mobile work should start from a separate accepted Stage 2 plan and recreate those boundaries from the stabilized post-Stage 1.7 Python oracle.

Execution plan status is listed in [docs/PLANS.md](docs/PLANS.md).
