# Data

## Canonical Memory Event

Every persisted memory item must be represented as a structured event before indexing:

```json
{
  "event_id": "uuid",
  "created_at": "2026-05-01T09:00:00+08:00",
  "valid_time": {
    "start": "2026-05-01T09:00:00+08:00",
    "end": null
  },
  "event_type": "user_utterance | app_action | visual_scene | sensor_snapshot | derived_summary | procedural_skill",
  "memory_layer": "working | episodic | semantic | procedural",
  "semantic_description": "human-readable summary",
  "entities": [],
  "relations": [],
  "source": {
    "app": "system_assistant",
    "actor": "user | agent | app | cloud_consolidator",
    "modality": ["text"],
    "attribution": "user_stated | agent_inferred | app_synced | derived"
  },
  "privacy": {
    "level": "sensitive | personal | public",
    "allowed_scopes": [],
    "processing_policy": "device_only | client_encrypted_sync | private_compute | cloud_indexable"
  },
  "quality": {
    "confidence": 0.95,
    "importance": 0.7,
    "freshness_half_life_days": 30
  },
  "lineage": {
    "parents": [],
    "derived_from": [],
    "supersedes": []
  },
  "lifecycle": {
    "state": "active | superseded | deleted | quarantined",
    "deleted_at": null,
    "delete_reason": null
  }
}
```

## Required Invariants

- No raw sensory payload is stored in a memory event by default. Raw data, if retained, must be encrypted and referenced by object ID.
- Embeddings, summaries, graph edges, and cached projections inherit the strongest privacy restriction of their source events.
- Derived memory must keep lineage to source events so correction and deletion can propagate.
- Conflict is a first-class state. A new contradictory event does not silently overwrite old memory.
- Third-party writes start with lower trust and may require confirmation before promotion into semantic memory.
- Context bundles are projections, not canonical memory. They must preserve event IDs so later correction or deletion remains traceable.
- Private-compute eligibility is explicit metadata. It is not implied by `personal` privacy level.

## Lifecycle

1. Filter: reject low-signal or unauthorized input.
2. Normalize: resolve time, entities, units, app source, and privacy labels.
3. Construct: produce a canonical event plus indexes.
4. Validate: read before write, deduplicate, detect contradictions, and score trust.
5. Store: persist event and index projections.
6. Retrieve: permission-filter before ranking and context assembly.
7. Assemble context: convert authorized retrieval results into model-runtime-neutral context bundles.
8. Consolidate: distill summaries, semantic facts, and procedural candidates.
9. Correct or delete: propagate to all derived projections through tombstones.

## Storage Strategy

- Local L1: in-memory active working context and hot semantic facts.
- Local L2: SQLite tables for events, entities, permissions, audit, and lightweight search indexes.
- Local L3: compressed summaries and inactive procedural versions.
- Private compute: optional high-compute processing for explicitly eligible events; no durable source-of-truth role.
- Cloud archive: optional, policy-dependent, client-encrypted for personal memory and unavailable for sensitive memory by default.
