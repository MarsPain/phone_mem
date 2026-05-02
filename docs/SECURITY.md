# Security

## Trust Boundaries

- Device boundary: raw perception, sensitive memory, permission decisions, and final filtering happen locally.
- Model runtime boundary: prompt execution consumes context bundles and must not access the global memory store directly.
- Private-compute boundary: eligible high-compute processing may occur outside the device only under explicit policy and with no durable source-of-truth role.
- Cloud archive boundary: cloud systems may store encrypted personal memory and derived indexes only when policy allows.
- App boundary: third-party apps interact through scoped capability tokens, never direct database access.
- Agent boundary: agents see memory views, not the global memory store.

## Privacy Classes

- Sensitive: device-only by default. Examples: precise location trails, health details, home imagery, private conversations, biometric data.
- Personal: client-encrypted sync allowed with explicit user consent. Examples: preferences, calendar-derived context, social relationship summaries.
- Private-compute eligible: high-compute personal inference allowed only when the user and policy permit it. This is a processing policy, not a storage class.
- Public: cloud indexing allowed when derived from low-risk user-approved data. Examples: generic interests or non-sensitive app settings.

## Permission Model

Access is granted by memory scope, memory layer, entity/topic, time range, operation type, and duration. Reads and writes require separate grants. Write grants do not imply promotion to trusted semantic memory.

## Abuse Cases And Required Controls

- Memory poisoning: validate source, detect anomaly, quarantine low-trust writes, and require user confirmation for high-impact semantic changes.
- Prompt injection through memory: sanitize retrieved memory as data, not instructions; preserve system instruction priority.
- Runtime bypass: block runtime adapters from querying storage directly; all model context must come through permissioned retrieval and context assembly.
- Cross-agent leakage: use memory view projection with filtering, generalization, and anonymization.
- Deletion failure: propagate tombstones to events, embeddings, summaries, graph edges, cache, and cloud replicas.
- Silent over-collection: require visible consent, collection indicators, and minimal sampling for passive sensors.
- Inference overreach: mark inferred memories distinctly and make them easy to confirm, correct, or reject.

## Audit And Explainability

Every read, write, update, delete, sync, and projection must create an audit record with caller, scope, time, operation, and affected event IDs. User-facing responses should be able to explain which memories influenced the result.
