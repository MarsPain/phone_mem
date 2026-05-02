# 003 Retrieval And Context Assembly

Status: active
Type: execution

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

1. Implement retrieval query models and result snippets.
2. Apply memory view projection before scoring.
3. Implement deterministic lexical, entity, recency, confidence, and importance scoring.
4. Exclude deleted, superseded, and unauthorized events.
5. Implement `ContextAssembler.build_context`.
6. Add tests for permission-before-ranking, ranking determinism, deleted event exclusion, budget limits, and evidence ID preservation.

## Validation

- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`

## Acceptance

- Search returns only authorized active memory.
- Unauthorized memory is not scored or leaked through metadata.
- Results include event IDs and explanation fields.
- Context assembly respects configured budgets.
- Every included memory snippet keeps source evidence IDs.
