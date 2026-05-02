# Governance, Permissions, And Audit

## Purpose

Governance makes memory usable without turning the phone into an unbounded surveillance store. It defines who can read or write memory, what view they receive, how usage is audited, and how users can inspect, correct, reject, or delete memory.

The current implementation track should prove these governance rules in the Python reference service. Mobile permission UX, OS-level affordances, and third-party SDK access are later-stage surfaces over the same policy boundary.

## Trust Boundaries

The detailed security model is in [../SECURITY.md](../SECURITY.md). The governance design applies those boundaries to service behavior:

- system agents can administer local memory under user and OS policy;
- model runtimes consume context bundles, not the global store;
- third-party apps receive scoped memory views;
- cloud and private-compute systems never become the unconditional source of truth;
- users can inspect and revoke memory use.

## Permission Scope

A grant is scoped by:

- caller identity;
- operation type: read, write, correct, delete, subscribe, audit;
- memory layer;
- privacy class;
- app source;
- entity or topic;
- time range;
- duration or expiry;
- processing policy.

Read grants do not imply write grants. Write grants do not imply promotion into trusted semantic memory.

## Memory Views

A memory view is a filtered projection of canonical memory for a caller and task. It may:

- include only specific layers, topics, entities, or time ranges;
- generalize sensitive details;
- exclude raw source payloads;
- omit lower-confidence inferred facts;
- require user confirmation before returning high-impact facts.

Views are computed before retrieval ranking.

## Audit Records

Every read, write, correction, deletion, permission change, projection, context build, and future sync operation records:

- operation ID;
- caller;
- operation type;
- scope;
- affected event IDs;
- timestamp;
- decision outcome;
- denial reason when applicable.

Audit logs are append-only. User-facing explanations can derive from audit records and event lineage, but explanations are not a substitute for audit.

## Explanation

`explain(event_id, caller=...)` returns:

- source attribution;
- memory layer and privacy class;
- confidence and lifecycle state;
- lineage and supersession links;
- callers that recently used the memory when policy permits;
- whether the memory was user-stated, app-synced, agent-inferred, or derived.

Responses influenced by memory should be able to cite event IDs or explanation handles.

## Correction And Rejection

Correction creates a new lifecycle event or patch record rather than erasing history. Rejection marks an inferred or app-contributed memory as invalid for future retrieval. Both operations must preserve auditability and propagate to derived projections.

## Deletion

Deletion must create tombstones and remove affected memory from retrieval, summaries, embeddings, graph projections, cache, and future sync queues. Selector-based deletion may target event ID, app, entity, topic, or time range.

## Abuse Controls

- Memory poisoning: validate source, quarantine low-trust writes, and require confirmation for high-impact semantic changes.
- Prompt injection through memory: treat retrieved memory as data, not instructions.
- Runtime bypass: block direct storage access by model adapters.
- Cross-agent leakage: return memory views instead of raw global memory.
- Silent over-collection: require consent and visible controls before passive sensing.
- Inference overreach: label inferred memory and make it easy to reject.
