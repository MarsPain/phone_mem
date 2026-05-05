# Smartphone Agent Memory Development Design

## Purpose

This document is the umbrella design map for smartphone Agent Memory. It keeps the full architecture navigable while detailed subsystem decisions live in focused design documents. The corrected source review is in [../references/source-review.md](../references/source-review.md), and the research-backed upgrade rationale is in [../references/research-review-2026.md](../references/research-review-2026.md).

## Architecture Summary

The system is a local-first OS-level Personal Memory Service for smartphone agents. It converts user-approved phone-context signals into structured memory events, stores them across memory layers, retrieves only authorized memory views, and emits token-budgeted context bundles to on-device or private-compute model runtimes.

Apps and agents do not own the global memory store. They receive scoped projections through service APIs.

The completed Stage 1 implementation is a Python reference version running on the development machine. It proves the service contract and lifecycle invariants before the later React Native, TypeScript, and on-device SQLite mobile runtime. The active Stage 1.5 track adds a Python LLM Agent runtime around that service to test a real provider-backed Agent loop without changing the memory service boundary.

## Key Corrections To The Source Design

- The source of truth is privacy-partitioned. Sensitive memory is device-only; personal memory may sync as client-encrypted data; only low-risk derived memory may be cloud-indexed.
- Deletion is a distributed lifecycle operation, not a row delete. Tombstones must invalidate events, embeddings, summaries, graph edges, caches, and cloud replicas.
- Inferred memory is lower-trust than user-stated memory and must remain easy to inspect and reject.
- Third-party writes cannot directly update global user profile facts. They enter quarantine or app-scoped memory until validation promotes them.
- Passive multimodal sensing is outside the MVP. It requires explicit consent, visible indicators, minimal sampling, and strong local filtering.
- Token budget management happens after permission filtering and before model context assembly.
- The Memory SDK is a facade over the service boundary, not the core architecture.
- Cloud reasoning is an optional accelerator. Personal context retrieval and planning should prefer local service boundaries first.

## Design Document Map

- [personal-memory-service.md](personal-memory-service.md): service ownership, public operations, module boundaries, and MVP implementation shape.
- [memory-lifecycle-and-data-flow.md](memory-lifecycle-and-data-flow.md): event lifecycle from authorized input through construction, validation, storage, retrieval, consolidation, correction, and deletion.
- [retrieval-and-context-assembly.md](retrieval-and-context-assembly.md): governed retrieval, ranking, snippet shaping, context budgets, and runtime-neutral bundles.
- [governance-permissions-audit.md](governance-permissions-audit.md): memory views, grants, audit, explanations, correction, deletion, and abuse controls.

The canonical data event schema remains in [../DATA.md](../DATA.md). Security and privacy rules remain in [../SECURITY.md](../SECURITY.md). Implementation and runtime strategy remain in [../BACKEND.md](../BACKEND.md).

## Bounded Contexts

- Personal Memory Service: owns canonical events, indexes, permissions, audit, tombstones, memory views, and retrieval APIs.
- Context Assembler: converts authorized retrieval results into token-budgeted model context with source metadata and safety priority.
- Model Runtime: owns prompt execution, tool calling, prompt compression, KV-cache lifecycle, model routing, and latency SLOs.
- App/Agent Gateway: exposes scoped SDK/API access for system agents first and third-party apps later.
- Governance UI: supports inspection, correction, deletion, permission review, and memory-use explanations.

## Memory Layers

- Working memory: current task context, scratchpad state, active system constraints, and loaded memory snippets. It is a projection, not the durable store.
- Episodic memory: time-anchored events from conversations, app actions, visual scenes, locations, and user feedback. This is the first persistent layer to implement.
- Semantic memory: distilled user profile, preferences, entities, relationships, and stable knowledge. Semantic facts must keep evidence lineage.
- Procedural memory: reusable workflows, skills, triggers, tool-call templates, and automation habits. Procedural automation requires confirmation before execution.

## MVP Boundary

The MVP proves the local service boundary as the Stage 1 Python reference implementation:

- text and app-event ingestion;
- local SQLite-backed episodic store;
- simple semantic profile store;
- lexical retrieval with a replaceable vector-style interface;
- permission-scoped memory views;
- model-runtime-neutral context assembly;
- correction, deletion, tombstone, and audit primitives;
- deterministic lifecycle tests.

The completed execution records are [../exec-plans/completed/2026-05-04-mvp-local-memory-core.md](../exec-plans/completed/2026-05-04-mvp-local-memory-core.md) and [../exec-plans/completed/2026-05-05-python-reference-maturation.md](../exec-plans/completed/2026-05-05-python-reference-maturation.md). The active Python LLM runtime plan is [../exec-plans/active/2026-05-05-python-llm-agent-runtime.md](../exec-plans/active/2026-05-05-python-llm-agent-runtime.md); mobile prototype planning remains deferred in [../exec-plans/tech-debt/deferred-stage2-mobile-runtime-prototype.md](../exec-plans/tech-debt/deferred-stage2-mobile-runtime-prototype.md).

## Non-Goals For MVP

- Always-on microphone, camera, sensor, or biometric memory.
- Open third-party marketplace access.
- Cloud source-of-truth memory.
- Fully autonomous cross-app actions.
- Learned forgetting policy. Start with deterministic retention rules and explicit deletion.
- Runtime-specific KV-cache optimization.

## Acceptance Criteria

- A memory event can be recorded, retrieved, explained, corrected, and deleted locally.
- Permission filtering prevents unauthorized callers from seeing restricted events.
- Deletion tombstones invalidate retrieval and derived projections.
- Write path detects duplicates and marks contradictions without silent overwrite.
- Audit log records all reads and writes.
- Context assembly respects explicit token budgets and preserves evidence IDs.
- Documentation validation passes.
