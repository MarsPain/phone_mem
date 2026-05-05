# phone-mem

Language: English | [Chinese](README.zh-CN.md)

`phone-mem` is the architecture and prototype repository for smartphone Agent Memory. The project goal is to build a local-first memory system on the phone that manages user memory with an agentic lifecycle: it understands and maintains long-term preferences, events, context, and operating habits from smartphone scenarios, then exposes governed memory capabilities to broader Agent applications.

The repository now contains a completed deterministic Python reference Personal Memory Service, a completed Stage 1.5 Python LLM Agent runtime spike for real provider-backed chat over governed memory APIs, and architecture context for the future mobile runtime. Stage 2 mobile implementation remains deferred until a separate plan is accepted.

## Quick Start

```bash
uv run python main.py
uv run python examples/agent_memory_demo.py
uv run python examples/agent_memory_repl.py
OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run python examples/llm_agent_chat.py
uv run python scripts/validate_docs.py
uv run python -m unittest discover -s tests
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): top-level architecture map.
- [AGENTS.md](AGENTS.md): working map for coding agents.
- [docs/README.md](docs/README.md): detailed documentation index.
- [docs/PYTHON_REFERENCE.md](docs/PYTHON_REFERENCE.md): practical Python reference usage guide.
- [docs/design-docs/python-llm-agent-runtime.md](docs/design-docs/python-llm-agent-runtime.md): Python LLM Agent runtime design.
- [docs/design-docs/smartphone-agent-memory.md](docs/design-docs/smartphone-agent-memory.md): smartphone Agent Memory development design.
- [docs/references/source-review.md](docs/references/source-review.md): deep review, distilled insights, and corrections for the source PDF.
- [docs/references/research-review-2026.md](docs/references/research-review-2026.md): v2 research basis across agent memory, on-device LLM systems, and Apple/Android platform constraints.
- [mobile/README.md](mobile/README.md): Stage 2 mobile runtime prototype boundary.

## Current Stage

Stage 1, the Python reference maturation track, and the Stage 1.5 Python LLM Agent runtime spike are complete. The Python code under `phone_mem/` is now the executable oracle for future mobile parity. The `phone_mem.agent_runtime` boundary supports real LLM API demos while keeping the memory core provider-independent.

Stage 2 mobile implementation is deferred. The repository currently has TypeScript boundary files and Python-backed contract fixtures, but no React Native app, mobile SQLite adapter, or TypeScript test toolchain yet.
