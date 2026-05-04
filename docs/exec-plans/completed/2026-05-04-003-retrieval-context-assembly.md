# 003 Retrieval And Context Assembly

Status: completed
Type: execution
Completed: 2026-05-04

## Goal

Implement governed local retrieval and runtime-neutral context bundle assembly for MVP Agent Memory use cases.

This subplan belongs to Stage 1: the Python reference implementation. It should emit model-runtime-neutral bundles without adding phone runtime adapters or prompt execution.

## Scope

- Deterministic lexical and metadata retrieval over authorized local events.
- Entity, source app, time range, layer, privacy, and lifecycle filters.
- Scoring based on lexical match, recency, confidence, and importance.
- Snippet shaping with event IDs, attribution, confidence, and explanation metadata.
- Context assembler with explicit token budget accounting and evidence preservation.

## Design Inputs

- [Retrieval And Context Assembly](../../design-docs/retrieval-and-context-assembly.md)
- [Governance, Permissions, And Audit](../../design-docs/governance-permissions-audit.md)
- [Data](../../DATA.md)
- [Backend](../../BACKEND.md)

## Out Of Scope

- Production embeddings.
- Cross-device retrieval.
- Runtime-specific prompt execution.
- Learned ranking.
- Semantic graph traversal.

## Steps

- [x] Implement retrieval query models and result snippets.
- [x] Apply memory view projection before scoring.
- [x] Implement deterministic lexical, entity, recency, confidence, and importance scoring.
- [x] Exclude deleted, superseded, and unauthorized events.
- [x] Implement `ContextAssembler.build_context`.
- [x] Add tests for permission-before-ranking, ranking determinism, deleted event exclusion, budget limits, evidence ID preservation, and context-build audit records.

## Implementation Notes

- `phone_mem/personal_memory_service/retrieval.py` implements deterministic local retrieval over active events only.
- `LocalMemoryRetriever` applies `MemoryViewProjector` before scoring and writes read audit records for allowed and denied projections.
- `phone_mem/context/assembler.py` emits runtime-neutral `ContextBundle` values and keeps model execution out of the memory service.
- MVP token accounting uses deterministic word counting. A production tokenizer remains out of scope until model-runtime adapters exist.

## Validation

- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`

## Acceptance

- Search returns only authorized active memory.
- Unauthorized memory is not scored or leaked through metadata.
- Results include event IDs and explanation fields.
- Context assembly respects configured budgets.
- Every included memory snippet keeps source evidence IDs.
