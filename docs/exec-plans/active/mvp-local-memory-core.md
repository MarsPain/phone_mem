# MVP Local Personal Memory Service

Status: active
Type: umbrella

## Goal

Implement a local-only Personal Memory Service that proves the service boundary before adding model-runtime integration, cloud sync, multimodal sensing, or third-party ecosystem access.

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
- Learned forgetting.
- Graph database.
- Runtime-specific KV-cache optimization.
- Private compute integration.

## Steps

1. Complete subplan 001 to establish package structure and event types.
2. Complete subplan 002 to persist events and enforce grants.
3. Complete subplan 003 to retrieve authorized memory and build context bundles.
4. Complete subplan 004 to expose service operations and cover lifecycle behavior.
5. Sync implementation notes back into [../../BACKEND.md](../../BACKEND.md), [../../DATA.md](../../DATA.md), and relevant design docs when behavior changes.

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
