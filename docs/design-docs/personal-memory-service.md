# Personal Memory Service

## Purpose

The Personal Memory Service is the local source of truth for smartphone Agent Memory. It owns durable memory events, lifecycle state, local projections, governance checks, audit records, and service APIs. Model runtimes and apps consume service outputs; they do not read the canonical store directly.

The current repository implementation should realize this service first as a deterministic Python reference package. The production phone runtime is a later mobile track that should mirror the same operations and invariants.

## Responsibilities

- Persist canonical memory events defined in [../DATA.md](../DATA.md).
- Enforce read and write permissions before storage, retrieval, or context assembly.
- Maintain local indexes and derived projections as replaceable views.
- Record audit events for every read, write, correction, delete, permission change, and context build.
- Create and propagate tombstones for deletion.
- Expose runtime-neutral operations for record, search, explain, correct, delete, grant, revoke, and audit.

## Python Reference MVP Module Boundary

The Stage 1 Python reference MVP package should grow around these modules from [../BACKEND.md](../BACKEND.md):

- `personal_memory_service/events.py`: typed event and selector models.
- `personal_memory_service/constructor.py`: candidate-to-event normalization, privacy classification, confidence, and lineage preparation.
- `personal_memory_service/storage.py`: SQLite persistence for events, entities, tombstones, permissions, and audit records.
- `personal_memory_service/retrieval.py`: permission-filtered search over local events.
- `personal_memory_service/lifecycle.py`: correction, deletion, supersession, contradiction, and tombstone propagation.
- `personal_memory_service/service.py`: orchestration facade for callers.
- `governance/permissions.py`, `governance/audit.py`, and `governance/views.py`: grants, audit writing, and memory view projection.
- `context/assembler.py`: context bundle construction after governed retrieval.

## Service Operations

```python
class PersonalMemoryService:
    def record(self, event: dict, *, caller: str) -> str:
        ...

    def search(self, query: str, *, caller: str, scope: dict, top_k: int = 10) -> list[dict]:
        ...

    def explain(self, event_id: str, *, caller: str) -> dict:
        ...

    def correct(self, event_id: str, patch: dict, *, caller: str) -> str:
        ...

    def delete(self, selector: dict, *, caller: str, reason: str) -> list[str]:
        ...

    def grant(self, caller: str, scope: dict, duration_seconds: int) -> str:
        ...

    def revoke(self, grant_id: str) -> None:
        ...

    def audit(self, selector: dict) -> list[dict]:
        ...
```

The product-level SDK facade is documented in [../product-specs/memory-sdk.md](../product-specs/memory-sdk.md).

## MVP Storage Tables

- `memory_events`: canonical event JSON plus lifecycle columns needed for filtering.
- `entities`: normalized entities and aliases.
- `event_entities`: event-to-entity links.
- `permissions`: capability grants by caller, operation, scope, and expiry.
- `audit_log`: immutable operation records.
- `tombstones`: deletion records and propagation state.

Indexes and summaries are projections. They must be rebuildable from canonical events and tombstones.

The Python reference store keeps common selector, permission, entity, and audit lookups indexed so the reference does not normalize full-table scans as the expected mobile behavior. Multi-row lifecycle operations use a store transaction boundary; service-level corrections, selector deletes, grant changes, and record-plus-audit writes should either commit all affected rows or leave canonical memory unchanged.

Lineage is also projected into an indexed edge table. Event JSON remains canonical, while `lineage_edges` supports explanation and deletion-propagation queries such as "which event supersedes this one" without scanning every event payload.

## Invariants

- Permission projection happens before retrieval ranking.
- Writes use read-before-write validation for dedupe and contradiction marking.
- Derived memory keeps lineage to source events.
- Lifecycle validation narrows duplicate and contradiction checks to active candidates that share source app and entity scope before applying in-memory equivalence rules.
- Third-party writes remain app-scoped or quarantined until promoted by policy.
- Deletion creates tombstones rather than only mutating rows.
- Selector deletion preflights permissions across the full matched event set before mutating any event.
- Service APIs return event IDs and evidence metadata for explainability.
- Runtime adapters cannot bypass service permissions.

## MVP Test Coverage

- Recording a valid event persists canonical data and audit records.
- Duplicate writes are detected.
- Contradictory writes are marked rather than silently overwriting.
- Unauthorized callers cannot retrieve restricted memory.
- Corrections preserve lineage and audit history.
- Deletions create tombstones and hide deleted memory from search.
