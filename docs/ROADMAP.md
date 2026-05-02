# Roadmap

## Stage 0: Documentation And Context

- Create root entrypoints and canonical docs.
- Review the source architecture PDF.
- Add research-backed v2 review across agent memory, on-device LLM systems, and Apple/Android platform constraints.
- Add docs validation.

## Stage 1: Python Reference Personal Memory Service

- Canonical memory event model.
- SQLite-backed event store and audit log.
- Basic write path with filtering, normalization hooks, and read-before-write validation.
- Permission-scoped retrieval over local events.
- Deletion tombstones and derived projection invalidation.
- Model-runtime-neutral context assembler.
- Measurable acceptance gates for p95 retrieval latency, permission denial correctness, audit completeness, deletion propagation, and context budget adherence.

Stage 1 runs on the development machine as a Python reference implementation. It proves service behavior and testable invariants; it is not the production iOS or Android runtime.

## Stage 2: Mobile Runtime Prototype

- React Native and TypeScript app shell for iPhone and Android.
- TypeScript memory core mirroring the Python reference service boundary.
- On-device SQLite storage adapter.
- Governance, audit, correction, deletion, retrieval, and context assembly flows exposed through mobile UI.
- Contract tests or shared fixtures to keep mobile behavior aligned with the Python reference.

## Stage 3: Retrieval, Context, And Semantic Layer

- Add hybrid lexical, entity, recency, and embedding retrieval.
- Add semantic profile distillation.
- Add contradiction detection and user correction workflow.
- Add token-budgeted context assembly.
- Add offline evaluation with synthetic personal tasks and long-session QA.

## Stage 4: On-Device Agent Runtime Boundary

- Integrate with a local model provider or runtime adapter.
- Add coordinator/specialist interfaces for retrieval, tool interaction, and planning.
- Add prompt compression and latency-SLO-aware context assembly hooks.
- Keep memory service independent from runtime-specific KV-cache management.

## Stage 5: SDK And App Views

- Implement query, write, governance, and subscription APIs.
- Add memory view projection.
- Add app-scope capability tokens.
- Add SDK examples and integration tests.

## Stage 6: Private Compute, Sync, And Consolidation

- Add client-encrypted sync for eligible memory.
- Add private-compute policy for eligible high-compute inference.
- Add cloud archive and consolidation worker only for allowed privacy classes.
- Add graph projection for semantic memory.
- Add cross-device conflict resolution.

## Stage 7: Multimodal Expansion

- Add voice and visual ingestion only after local governance, deletion, and audit are proven.
- Add passive sensor context as metadata, not raw retained memory.
