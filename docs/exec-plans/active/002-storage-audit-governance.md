# 002 Storage Audit And Governance

Status: active
Type: execution

## Goal

Persist local memory events in SQLite and enforce the first permission, memory view, tombstone, and audit invariants.

## Scope

- SQLite schema for canonical events, entities, event-entity links, permissions, tombstones, and audit records.
- Repository/storage interface for event create, read, update lifecycle, and selector queries.
- Grant and revoke operations for scoped permissions.
- Memory view projection before retrieval.
- Audit log writer for reads, writes, permission changes, corrections, and deletions.

## Design Inputs

- [Personal Memory Service](../../design-docs/personal-memory-service.md)
- [Governance, Permissions, And Audit](../../design-docs/governance-permissions-audit.md)
- [Memory Lifecycle And Data Flow](../../design-docs/memory-lifecycle-and-data-flow.md)
- [Security](../../SECURITY.md)

## Out Of Scope

- Full retrieval ranking.
- Context bundle construction.
- Cloud sync.
- Graph or vector stores.
- Production encryption.

## Steps

1. Implement SQLite schema creation and migration bootstrap.
2. Implement storage operations for event insert, lookup, selector query, lifecycle update, and tombstone write.
3. Implement permission grant, revoke, and scope matching.
4. Implement memory view projection for caller, operation, layer, privacy class, app, entity/topic, and time range.
5. Implement audit writing and query helpers.
6. Add tests for persistence, permission denial, grant expiry, tombstone creation, and audit completeness.

## Validation

- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`

## Acceptance

- Events persist locally and can be read by ID.
- Permission checks deny unauthorized callers before retrieval work.
- Grants are scoped and revocable.
- Deletes create tombstones.
- Reads, writes, permission changes, and deletes create audit records.
