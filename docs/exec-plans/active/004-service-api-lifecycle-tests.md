# 004 Service API And Lifecycle Tests

Status: active
Type: execution

## Goal

Expose the MVP `PersonalMemoryService` facade and verify complete record, search, explain, correct, delete, grant, revoke, and audit behavior.

This subplan belongs to Stage 1: the Python reference implementation. The facade should be a testable service contract for later mobile parity, not a production phone runtime or SDK surface.

## Scope

- Orchestrating service facade in `phone_mem/personal_memory_service/service.py`.
- Lifecycle operations for correction, rejection, supersession, contradiction, and deletion.
- Explain operation based on event metadata, audit records, and lineage.
- End-to-end tests for user-facing service behavior.
- Documentation updates for any implementation decisions that change the design.

## Design Inputs

- [Personal Memory Service](../../design-docs/personal-memory-service.md)
- [Memory Lifecycle And Data Flow](../../design-docs/memory-lifecycle-and-data-flow.md)
- [Governance, Permissions, And Audit](../../design-docs/governance-permissions-audit.md)
- [Retrieval And Context Assembly](../../design-docs/retrieval-and-context-assembly.md)

## Out Of Scope

- SDK packaging.
- Mobile UI.
- Cloud or private-compute adapters.
- Autonomous procedural execution.
- Continuous multimodal ingestion.

## Steps

1. Implement `PersonalMemoryService.record`.
2. Implement `PersonalMemoryService.search` through governed retrieval.
3. Implement `PersonalMemoryService.explain`.
4. Implement `PersonalMemoryService.correct` and contradiction/supersession behavior.
5. Implement `PersonalMemoryService.delete` with tombstone propagation.
6. Implement `grant`, `revoke`, and `audit` facade methods.
7. Add end-to-end lifecycle tests and update affected docs.

## Validation

- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`

## Acceptance

- A memory event can be recorded, searched, explained, corrected, and deleted through the service facade.
- Unauthorized callers cannot access restricted memory through any facade method.
- Contradictory memory is marked and explainable.
- Deleted memory is hidden from search and context assembly.
- Audit records cover all facade operations.
- The service exposes runtime-neutral APIs and has no hard dependency on an LLM provider.
