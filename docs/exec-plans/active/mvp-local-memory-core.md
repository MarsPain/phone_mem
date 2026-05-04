# MVP Local Personal Memory Service

Status: active
Type: umbrella

## Goal

Implement a local-only Python reference Personal Memory Service that proves the service boundary before adding the real mobile runtime, model-runtime integration, cloud sync, multimodal sensing, or third-party ecosystem access.

This plan is the executable specification track. It is not the final iOS or Android runtime. The future mobile runtime should mirror the same domain operations and invariants in React Native, TypeScript, and on-device SQLite.

## Scope

- Canonical memory event model.
- SQLite local store.
- Permission grants and memory views.
- Write path with dedupe and contradiction marking.
- Retrieval with permission filtering.
- Model-runtime-neutral context assembly.
- Correction, deletion tombstones, and audit log.
- Unit tests for lifecycle operations.
- Basic metrics hooks for retrieval latency, permission denial, audit coverage, deletion propagation, and context budget adherence.

## Design Inputs

- [Personal Memory Service](../../design-docs/personal-memory-service.md)
- [Memory Lifecycle And Data Flow](../../design-docs/memory-lifecycle-and-data-flow.md)
- [Retrieval And Context Assembly](../../design-docs/retrieval-and-context-assembly.md)
- [Governance, Permissions, And Audit](../../design-docs/governance-permissions-audit.md)
- [Data](../../DATA.md)
- [Backend](../../BACKEND.md)
- [Security](../../SECURITY.md)

## Subplans

1. [001 Package And Event Model](001-package-event-model.md)
2. [002 Storage Audit And Governance](002-storage-audit-governance.md)
3. [003 Retrieval And Context Assembly](003-retrieval-context-assembly.md)
4. [004 Service API And Lifecycle Tests](004-service-api-lifecycle-tests.md)

## Out Of Scope

- Cloud sync.
- Always-on sensors.
- Production mobile SDK packaging.
- React Native or TypeScript mobile runtime implementation.
- Learned forgetting.
- Graph database.
- Runtime-specific KV-cache optimization.
- Private compute integration.

## Steps

- [x] Complete subplan 001 to establish package structure and event types.
- [x] Complete subplan 002 to persist events and enforce grants.
- [x] Complete subplan 003 to retrieve authorized memory and build context bundles.
- [x] Complete subplan 004 to expose service operations and cover lifecycle behavior.
- [x] Sync implementation notes back into [../../BACKEND.md](../../BACKEND.md), [../../DATA.md](../../DATA.md), and relevant design docs when behavior changes.

## Implementation Notes

- The Python reference now exposes a service-level `build_context` facade that runs governed retrieval before context assembly.
- `phone_mem/personal_memory_service/metrics.py` provides MVP metrics hooks from audit records, tombstones, deleted lifecycle rows, and latest context budget usage.
- `phone_mem/personal_memory_service/lifecycle.py` owns duplicate detection and simple same-entity preference contradiction quarantine.
- The MVP remains local-only and does not introduce model providers, vector stores, cloud sync, mobile runtime code, or SDK packaging.

## Validation

- `uv run python scripts/validate_docs.py`
- `uv run python -m unittest discover -s tests`

## Acceptance

- Unauthorized caller cannot retrieve restricted memory.
- Deleted memory cannot be retrieved directly or through derived summaries.
- Contradictory memory is marked, not silently overwritten.
- Every read and write creates an audit record.
- Context assembly respects configured budgets and preserves memory evidence IDs.
- MVP exposes service interfaces without coupling to one model runtime.
- Standard validation commands pass.
