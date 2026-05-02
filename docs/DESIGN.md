# Design

This document is the canonical system overview. Deep implementation detail starts at [design-docs/smartphone-agent-memory.md](design-docs/smartphone-agent-memory.md), with focused subsystem docs for the [Personal Memory Service](design-docs/personal-memory-service.md), [memory lifecycle](design-docs/memory-lifecycle-and-data-flow.md), [retrieval and context assembly](design-docs/retrieval-and-context-assembly.md), and [governance](design-docs/governance-permissions-audit.md). The research rationale is in [references/research-review-2026.md](references/research-review-2026.md).

## Thesis

Smartphone Agent Memory should be a local-first OS-level Personal Memory Service, not a single assistant feature and not merely a third-party SDK. The phone owns canonical personal memory, permission enforcement, audit, deletion, fast retrieval, and context assembly. Model runtimes, agents, apps, and optional cloud systems consume scoped memory views through service APIs.

The system should behave like an agentic memory manager for the smartphone: it observes authorized phone-context signals, decides what should become durable memory, maintains confidence and lifecycle state, asks for user correction when needed, and supplies only task-appropriate memory views to downstream agents. Broader Agent applications should build on this service boundary instead of rebuilding private memory stores inside each app.

## Corrected Architecture Principles

1. Local-first is a hard privacy boundary, not only a latency optimization.
2. Memory service and model runtime are separate bounded contexts. The memory service owns facts, permissions, audit, and deletion; the model runtime owns prompt execution, KV-cache lifecycle, model choice, and latency SLOs.
3. The cloud is not the unconditional source of truth. The source of truth is partitioned by privacy class:
   - sensitive memory: device-only unless the user explicitly exports it;
   - personal memory: client-encrypted sync is allowed;
   - high-compute personal inference: private-compute processing may be allowed with explicit policy;
   - public or low-risk derived memory: cloud indexing can be allowed by policy.
4. Reads must be permission-filtered before ranking and before model context assembly.
5. Writes must use read-before-write validation to avoid duplicate, contradictory, or poisoned memory.
6. Deletion must be propagated as a tombstone and honored by local cache, cloud archive, graph projections, embeddings, summaries, and sync queues.
7. Every memory used in a response must be traceable to source, confidence, permission scope, and last update.
8. On-device small-model reasoning should be preferred for personal context retrieval, planning, and tool routing; cloud reasoning is an optional accelerator, not the default architecture.

## Four Memory Layers

- Working memory: current task context, scratchpad state, active system constraints, and loaded memory snippets.
- Episodic memory: time-anchored events from conversations, app actions, visual scenes, locations, and user feedback.
- Semantic memory: distilled user profile, preferences, entities, relationships, and stable knowledge.
- Procedural memory: reusable workflows, skills, triggers, tool-call templates, and automation habits.

## Bounded Contexts

- Personal Memory Service: canonical event store, indexes, permissions, audit, tombstones, memory views, and retrieval APIs.
- Context Assembler: converts authorized retrieval results into token-budgeted model context with source metadata and safety priority.
- Model Runtime: on-device or private-compute model execution, tool calling, prompt compression, KV-cache lifecycle, model routing, and latency SLOs.
- App/Agent Gateway: scoped SDK/API facade for system agents first and third-party apps later.
- Governance UI: user inspection, correction, deletion, permission review, and memory-use explanations.

## Runtime Components

- Perception Orchestrator: receives multimodal signals and performs low-level filtering.
- Memory Constructor: normalizes inputs into canonical memory events.
- Storage Manager: owns local stores, optional cloud stores, indexes, and lifecycle transitions.
- Retrieval Router: performs gated, multi-signal retrieval after permission projection.
- Context Assembler: allocates token budget and emits model-runtime-neutral context bundles.
- Consolidation Evolver: extracts semantic memory, detects contradictions, compresses old episodic memory, and maintains graph links.
- Governance Controller: enforces permissions, memory views, audit, correction, and deletion.

## MVP Boundary

The MVP must not attempt continuous always-on multimodal sensing, graph memory, cloud sync, or open third-party ecosystem access. It should prove the local service boundary:

- text and app-event ingestion;
- local SQLite-backed episodic store;
- simple semantic profile store;
- lexical plus vector-style retrieval abstraction;
- permission-scoped memory views;
- model-runtime-neutral context assembly;
- correction/deletion/audit primitives;
- deterministic tests for write, read, deletion, permission behavior, audit completeness, and context budget adherence.
