# 001 Package And Event Model

Status: active
Type: execution

## Goal

Create the initial Python package structure and canonical event model needed by the local Personal Memory Service.

This subplan belongs to Stage 1: the Python reference implementation. It should not introduce mobile runtime, OS integration, or model-provider dependencies.

## Scope

- Add the `phone_mem/` package skeleton.
- Define canonical event, source, privacy, quality, lineage, lifecycle, selector, and audit-related value models.
- Keep event construction independent from persistence.
- Add deterministic validation for required event fields and lifecycle states.
- Update affected architecture/data docs if implementation names differ from the current design.

## Design Inputs

- [Personal Memory Service](../../design-docs/personal-memory-service.md)
- [Memory Lifecycle And Data Flow](../../design-docs/memory-lifecycle-and-data-flow.md)
- [Data](../../DATA.md)
- [Backend](../../BACKEND.md)

## Out Of Scope

- SQLite persistence.
- Permission grant enforcement.
- Retrieval ranking.
- Context assembly.
- Cloud or model runtime adapters.

## Steps

1. Create the package directories listed in [../../BACKEND.md](../../BACKEND.md) only where needed for MVP.
2. Implement event and selector models in `phone_mem/personal_memory_service/events.py`.
3. Implement constructor-level normalization hooks in `phone_mem/personal_memory_service/constructor.py`.
4. Add unit tests for valid events, invalid required fields, privacy policy classification, lineage defaults, and lifecycle state transitions.
5. Keep `main.py` as a placeholder unless a minimal demo entrypoint is needed.

## Validation

- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`

## Acceptance

- A canonical memory event can be created from structured input.
- Invalid event input fails with a clear error.
- Event models preserve event IDs, source attribution, privacy policy, quality metadata, lineage, and lifecycle state.
- Constructor code has no dependency on SQLite or model runtimes.
