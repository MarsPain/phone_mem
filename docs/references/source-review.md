# Source PDF Review

Source file reviewed locally: `手机端Agent_Memory架构设计方案.pdf`.

This is the PDF-specific review. The broader v2 research-backed review is [research-review-2026.md](research-review-2026.md).

## Executive Summary

The PDF is strong as an architecture vision. Its best ideas are the local-first edge plus cloud-deep split, four-layer memory model, unified multimodal event abstraction, hybrid retrieval, memory SDK, and explicit governance surface. The main gap is that several principles are stated but not hardened into enforceable invariants. This repository's design documents convert those principles into development rules around privacy partitioning, deletion propagation, permission-first retrieval, third-party write quarantine, and MVP scope control.

## Essence Worth Preserving

- Treat the phone as the cognitive edge node. Real-time working memory, recent episodic memory, hot semantic profile, and permission enforcement belong on device.
- Treat cloud services as optional deep memory infrastructure. They can archive, consolidate, build graphs, and sync, but should not see sensitive raw data.
- Use four memory layers: working, episodic, semantic, and procedural. This avoids mixing transient prompt context, time-anchored events, durable user facts, and executable habits.
- Normalize multimodal input into a unified event abstraction. Retrieval and governance become tractable only after voice, visual, sensor, and app events share a common schema.
- Use hybrid retrieval. Semantic search alone is insufficient; real systems need lexical search, entity linking, metadata filters, recency, importance, context signals, and reranking.
- Make memory an SDK/platform capability. Cross-app personalization requires scoped memory views, not each app building its own private memory silo.
- Manage lifecycle deliberately. Filtering, normalization, validation, consolidation, contradiction detection, forgetting, and audit are core behavior, not background cleanup.

## Critical Gaps And Clarifications

### 1. Cloud Source Of Truth Conflicts With Local-First Privacy

The PDF says the cloud can be the "source of truth" while also saying sensitive raw data should not leave the device. That is contradictory for sensitive memory.

Correction: source of truth is partitioned by privacy class. Sensitive memory is device-only. Personal memory can sync only as client-encrypted data. Public or low-risk derived memory can be cloud-indexed by policy.

### 2. Deletion Is Under-Specified

The PDF supports fine-grained forgetting but does not define how deletion affects embeddings, summaries, graph edges, sync queues, and cloud archives.

Correction: deletion must create tombstones and propagate through all derived projections. A deleted event must not remain visible through a semantic summary or graph neighbor.

### 3. Third-Party Writes Can Pollute Shared Memory

The PDF identifies memory pollution but needs a stricter write model.

Correction: third-party writes start as app-scoped or quarantined events. Promotion to global semantic memory requires source trust, contradiction checks, confidence threshold, and user-visible correction.

### 4. Passive Multimodal Sensing Is Too Broad For Early Stages

The source design discusses voice, camera, visual streams, sensors, and app interaction together. This is powerful but high-risk.

Correction: MVP should exclude always-on microphone/camera/biometric memory. Start with text and app-event ingestion, then add voice/visual only after audit, permission, deletion, and local filtering are proven.

### 5. Retrieval Needs Permission-First Ordering

The PDF describes retrieval pipelines but does not always make clear that permission projection must happen before scoring.

Correction: retrieval order is authenticate, project authorized view, filter privacy and scope, then rank. Unauthorized data should never enter candidate scoring for third-party callers.

### 6. Inferred Memory Needs A Separate Trust State

The design mixes user-stated, app-synced, and agent-inferred memory as confidence metadata.

Correction: attribution must affect lifecycle. Inferred memory should remain visibly inferred, lower-trust, and easy to reject. It should not silently become a durable user fact.

### 7. Token Budgeting Needs A System Contract

The PDF includes token budget formulas, but implementation needs deterministic behavior.

Correction: memory context assembly should reserve space for system constraints, current task, and retrieved memory. Safety instructions and user-confirmed constraints outrank opportunistic recall.

### 8. MVP Scope Is Too Large

The three-stage roadmap is directionally useful but still broad.

Correction: first milestone should build a local event store, permission view, audit log, retrieval path, correction, deletion, and tests. Cloud, open SDK, multimodal streams, and learned forgetting come later.

## Development Implications

- Build local storage and governance before cloud sync.
- Build deletion and audit before third-party SDK access.
- Build deterministic retrieval before adding learned rankers.
- Build text/app ingestion before passive multimodal ingestion.
- Build explicit evidence lineage before semantic consolidation.

## Canonical Follow-Up Docs

- Corrected system overview: [../DESIGN.md](../DESIGN.md)
- Data model and lifecycle: [../DATA.md](../DATA.md)
- Security and governance: [../SECURITY.md](../SECURITY.md)
- Detailed development design: [../design-docs/smartphone-agent-memory.md](../design-docs/smartphone-agent-memory.md)
