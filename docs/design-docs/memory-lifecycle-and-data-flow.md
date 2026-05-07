# Memory Lifecycle And Data Flow

## Purpose

This document defines how authorized phone-context signals become durable memory and how memory moves through validation, retrieval, context assembly, consolidation, correction, and deletion.

The current implementation track should make this lifecycle executable in the Stage 1 Python reference service. Mobile OS integration, passive sensing adapters, and production phone runtime behavior belong to later stages.

## End-To-End Flow

1. Ingest authorized input from system assistant text, app events, or future multimodal adapters.
2. Reject unauthorized, low-signal, or unsupported input before construction.
3. Normalize time, entities, app source, modality, attribution, privacy level, and retention hints.
4. Construct a canonical memory event using [../DATA.md](../DATA.md).
5. Read before write to detect duplicates, contradictions, stale facts, and trust problems.
6. Persist the event and local projections.
7. Retrieve through permission-scoped memory views.
8. Assemble runtime-neutral context bundles after retrieval.
9. Consolidate eligible events into summaries, semantic facts, or procedural candidates.
10. Correct or delete through lifecycle operations that propagate to derived projections.

## MVP Ingestion Boundary

MVP ingestion supports:

- direct user-stated text memory;
- system assistant interaction events;
- app action events supplied as structured dictionaries.

MVP ingestion does not support:

- always-on microphone or camera collection;
- raw sensor retention;
- third-party background collection;
- cloud-originated canonical writes.

## Construction Rules

The Memory Constructor must:

- assign event ID and timestamps;
- classify `event_type`, `memory_layer`, privacy level, and processing policy;
- attach source attribution and caller identity;
- assign confidence, importance, freshness hint, and lifecycle state;
- extract normalized entities when available;
- create lineage metadata for derived or corrected events.

Raw sensory payloads are not stored by default. If future stages retain raw media, the memory event stores an encrypted object reference rather than the payload.

## Validation Rules

Before storage, the service performs read-before-write checks:

- duplicate: the new event is equivalent to an existing active event;
- contradiction: the new event conflicts with an active event and both should remain traceable;
- supersession: the new event explicitly replaces an older fact;
- quarantine: source trust or scope is too weak for promotion;
- rejection: caller lacks permission or the payload violates safety policy.

Conflict is a first-class lifecycle state. The service must not silently rewrite user memory.

The Python reference narrows read-before-write validation through indexed selectors before applying duplicate or contradiction rules in memory. Duplicate checks use active events with the same source app, entity scope, and memory layer. Contradiction checks use active events with the same source app and overlapping entity scope, then apply the current deterministic preference parser across a small predicate family such as "prefers" and "likes." Later semantic contradiction detectors should keep the same candidate narrowing boundary.

## Lifecycle States

- `active`: eligible for permission-filtered retrieval.
- `superseded`: retained for lineage and explanation, not primary retrieval.
- `deleted`: hidden from retrieval and represented by a tombstone.
- `quarantined`: retained for review or app scope, not promoted into global memory.

## Deletion Propagation

Deletion is selector-based and may target event ID, entity, time range, app source, or topic. A deletion operation must:

- create an audit record;
- write a tombstone;
- mark canonical events deleted;
- remove or invalidate derived projections;
- hide affected memories from retrieval and context assembly;
- queue later sync invalidation when cloud sync exists.

Correction and deletion operations are transactional in the Python reference. A failed supersession update must not leave a new corrected event behind, and selector deletion must preflight permissions for every matched event before any lifecycle mutation or tombstone write occurs.

## Consolidation Boundary

Consolidation is not required for the first implementation pass. When introduced, it should run as a background process that:

- clusters episodic memory into summaries;
- proposes semantic profile facts with evidence lineage;
- detects stale preferences and contradictions;
- proposes procedural candidates from repeated actions.

Promotion from inferred memory to semantic memory requires confidence thresholds and user-visible review for high-impact facts.
