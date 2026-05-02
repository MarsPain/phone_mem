# phone-mem

Language: English | [Chinese](README.zh-CN.md)

`phone-mem` is the architecture and prototype repository for smartphone Agent Memory. The project goal is to build a local-first memory system on the phone that manages user memory with an agentic lifecycle: it understands and maintains long-term preferences, events, context, and operating habits from smartphone scenarios, then exposes governed memory capabilities to broader Agent applications.

The current focus is to turn the source architecture proposal into executable development context: product goals, system boundaries, data model, safety constraints, SDK shape, and staged delivery.

## Quick Start

```bash
uv run python main.py
uv run python scripts/validate_docs.py
uv run python -m unittest discover -s tests
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): top-level architecture map.
- [AGENTS.md](AGENTS.md): working map for coding agents.
- [docs/README.md](docs/README.md): detailed documentation index.
- [docs/design-docs/smartphone-agent-memory.md](docs/design-docs/smartphone-agent-memory.md): smartphone Agent Memory development design.
- [docs/references/source-review.md](docs/references/source-review.md): deep review, distilled insights, and corrections for the source PDF.
- [docs/references/research-review-2026.md](docs/references/research-review-2026.md): v2 research basis across agent memory, on-device LLM systems, and Apple/Android platform constraints.

## Current Stage

The project is in the architecture-to-implementation preparation stage. The short-term goal is to implement a Python reference version of the local Personal Memory Service: canonical event abstraction, local memory service, permission views, audit and deletion, basic retrieval, and a context assembly boundary decoupled from model runtimes. The first real phone runtime should then mirror those boundaries in React Native, TypeScript, and on-device SQLite for iPhone and Android.
