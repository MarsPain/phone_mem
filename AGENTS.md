# Agent Working Map

This repository is currently a small Python project plus architecture documents for smartphone Agent Memory. The product goal is a local-first phone memory system that manages user memory in smartphone contexts with Agent-style lifecycle control, then exposes scoped memory views to broader Agent applications.

## Start Here

- Human onboarding: [README.md](README.md)
- Architecture map: [ARCHITECTURE.md](ARCHITECTURE.md)
- Documentation index: [docs/README.md](docs/README.md)
- Canonical design: [docs/DESIGN.md](docs/DESIGN.md)
- Deep memory design: [docs/design-docs/smartphone-agent-memory.md](docs/design-docs/smartphone-agent-memory.md)
- PDF review: [docs/references/source-review.md](docs/references/source-review.md)

## Commands

```bash
uv run python main.py
uv run python examples/agent_memory_demo.py
uv run python examples/agent_memory_repl.py
uv run python examples/web_lab.py --reload
uv run python scripts/validate_docs.py
uv run python -m unittest discover -s tests
```

## Repository Rules

- Keep root docs concise. Put detailed decisions under `docs/`.
- Update code and affected docs in the same change set.
- Treat [docs/DESIGN.md](docs/DESIGN.md), [docs/DATA.md](docs/DATA.md), and [docs/SECURITY.md](docs/SECURITY.md) as canonical for architecture, data, and safety constraints.
- Preserve the core product framing: memory is managed as an agentic phone subsystem, while external agents consume governed views rather than the raw global store.
- Use [docs/PLANS.md](docs/PLANS.md) and `docs/exec-plans/` for execution lifecycle.
- Run the docs validator before claiming documentation work is complete.

## Current Implementation State

- `main.py` is still only a placeholder.
- Stage 1 Python reference memory core is implemented under `phone_mem/`.
- Stage 1.5 Python LLM Agent runtime is implemented under `phone_mem/agent_runtime/`.
- Stage 1.6 local Python Web Lab is implemented under `phone_mem/web_lab/`.
- Stage 1.7 Python Agentic Memory Lifecycle Maturation is active; keep mobile work deferred and do not preserve stale TypeScript mobile boundaries while the Python oracle deepens.
- No production mobile runtime exists yet.
- The active execution plan is tracked in [docs/PLANS.md](docs/PLANS.md); mobile work remains deferred until Stage 1.7 stabilizes and a separate Stage 2 plan is accepted.
