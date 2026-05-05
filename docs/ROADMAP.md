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

Status: completed on 2026-05-04 as the local Python reference core.

## Recently Completed Track: Python Reference Maturation

- Improve service API ergonomics and caller-facing failure messages.
- Expand lifecycle behavior for rejection, quarantine review, correction explainability, and contradiction handling.
- Add retrieval selector examples and tests.
- Keep the Python reference as the executable oracle for future mobile parity.

Status: completed on 2026-05-05. Tracked by [PLANS.md](PLANS.md) and [exec-plans/completed/2026-05-05-python-reference-maturation.md](exec-plans/completed/2026-05-05-python-reference-maturation.md).

## Recently Completed Track: Stage 1.5 Python LLM Agent Runtime

- Add a provider-neutral Python Agent runtime around the completed memory service.
- Add a fake deterministic LLM client for tests and an OpenAI-compatible adapter for real local development.
- Add memory tools for governed search, context build, remember, explain, correct, and delete.
- Add a real-provider interactive chat demo while keeping default tests network-free.
- Preserve the Personal Memory Service as provider-independent and permission-gated.

Status: completed on 2026-05-05. The Python runtime modules, fake-client tests, OpenAI-compatible adapter, thinking configuration, provider request error handling, and `examples/llm_agent_chat.py` demo now exist. Tracked by [PLANS.md](PLANS.md), [design-docs/python-llm-agent-runtime.md](design-docs/python-llm-agent-runtime.md), and [exec-plans/completed/2026-05-05-python-llm-agent-runtime.md](exec-plans/completed/2026-05-05-python-llm-agent-runtime.md).

## Stage 2: Mobile Runtime Prototype

- React Native and TypeScript app shell for iPhone and Android.
- TypeScript memory core mirroring the Python reference service boundary.
- On-device SQLite storage adapter.
- Governance, audit, correction, deletion, retrieval, and context assembly flows exposed through mobile UI.
- Contract tests or shared fixtures to keep mobile behavior aligned with the Python reference.

Status: deferred planning. Stage 2 has a documented `mobile/` boundary and Python-backed contract fixtures, but implementation work remains parked until a separate Stage 2 execution plan is accepted. The deferred plan is tracked in [exec-plans/tech-debt/deferred-stage2-mobile-runtime-prototype.md](exec-plans/tech-debt/deferred-stage2-mobile-runtime-prototype.md).

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
