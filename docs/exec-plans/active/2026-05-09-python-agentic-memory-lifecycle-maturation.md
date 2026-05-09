# Python Agentic Memory Lifecycle Maturation

Status: active
Type: implementation
Started: 2026-05-09

## Goal

Mature the Python reference from a completed deterministic Personal Memory Service into a deeper agentic memory lifecycle oracle before any mobile runtime implementation begins.

## Scope

- Promote the OpenClaw-inspired memory optimization track into Stage 1.7 Python-only implementation work.
- Keep `phone_mem/` as the executable oracle for future mobile parity.
- Add runtime memory protocol rules, governed session capture, compact hot memory capsules, hybrid retrieval, relation projections, maintenance workflows, and quality metrics in Python first.
- Preserve the canonical event store, permission-first retrieval, audit, tombstone, and context assembly boundaries already documented in [Design](../../DESIGN.md), [Data](../../DATA.md), [Security](../../SECURITY.md), and [Backend And Runtime Strategy](../../BACKEND.md).
- Do not maintain stale `mobile/` TypeScript boundary files while Stage 1.7 changes the Python oracle; future mobile boundaries should be recreated after Python behavior stabilizes.

## Architecture

Stage 1.7 keeps canonical memory events in `PersonalMemoryService` and SQLite as the source of truth. New capabilities must be projections, runtime hooks, candidate-producing workflows, or maintenance operations around that source of truth; they must not become alternate memory stores.

Every read path remains permission-filtered before ranking or context assembly. Every derived capsule, relation edge, summary, score explanation, and maintenance proposal must retain evidence event IDs and honor tombstones.

```text
AgentRuntime
  |
  +--> Runtime Memory Protocol
  +--> Session Capture -> MemoryCandidate proposals
  |
  v
PersonalMemoryService
  |
  +--> Canonical events, permissions, audit, tombstones
  +--> Hybrid retrieval projection
  +--> Relation graph projection
  +--> Maintenance and metrics
  |
  v
Context Assembler
  |
  +--> Retrieval snippets
  +--> Hot memory capsules
```

## Design Inputs

- [OpenClaw-Inspired Memory Optimizations](../tech-debt/openclaw-inspired-memory-optimizations.md)
- [Backend And Runtime Strategy](../../BACKEND.md)
- [Roadmap](../../ROADMAP.md)
- [Python Reference Guide](../../PYTHON_REFERENCE.md)
- [Memory Lifecycle And Data Flow](../../design-docs/memory-lifecycle-and-data-flow.md)
- [Retrieval And Context Assembly](../../design-docs/retrieval-and-context-assembly.md)
- [Python LLM Agent Runtime](../../design-docs/python-llm-agent-runtime.md)
- [Governance, Permissions, And Audit](../../design-docs/governance-permissions-audit.md)
- [Data](../../DATA.md)
- [Security](../../SECURITY.md)

## Out Of Scope

- React Native, TypeScript service implementation, TypeScript boundary files, TypeScript tests, or mobile SQLite adapters.
- Production iOS or Android background services.
- Continuous phone sensor capture, voice capture, camera ingestion, or passive multimodal collection.
- Cloud sync, private-compute execution, provider-side durable memory, or external vector databases.
- Third-party SDK packaging or app marketplace access.
- Silent promotion of inferred semantic or procedural memory without review policy and evidence IDs.

## Files And Responsibilities

- Modify `phone_mem/agent_runtime/prompts.py`: add runtime memory protocol rules for when to search, write candidates, correct, and treat memory as data.
- Modify `phone_mem/agent_runtime/tools.py`: expose governed memory operations needed by the protocol without direct storage access.
- Modify `phone_mem/agent_runtime/runtime.py`: attach session capture hooks after deterministic chat turns.
- Create `phone_mem/agent_runtime/session_capture.py`: convert transcript summaries, tool observations, user corrections, and task state into governed `MemoryCandidate` proposals.
- Modify `phone_mem/personal_memory_service/constructor.py`: support candidate metadata required by session capture while preserving canonical event invariants.
- Create `phone_mem/context/capsules.py`: build compact hot memory capsules from authorized retrieval results.
- Modify `phone_mem/context/assembler.py`: merge retrieval snippets and capsules under explicit budget accounting.
- Modify `phone_mem/personal_memory_service/retrieval.py`: add hybrid ranking orchestration and score explanations after permission filtering.
- Modify `phone_mem/personal_memory_service/storage.py`: add rebuildable FTS5/BM25 and relation projection persistence only after canonical event behavior remains stable.
- Create `phone_mem/personal_memory_service/relations.py`: derive bounded relation graph projections from canonical events and lineage.
- Create `phone_mem/personal_memory_service/maintenance.py`: add dry-run reflection, defrag, schema drift, and projection health workflows.
- Modify `phone_mem/personal_memory_service/metrics.py`: expose capture, retrieval, context, deletion, audit, and maintenance quality metrics.
- Modify focused tests under `tests/`: add deterministic tests for each Stage 1.7 subtrack before implementation.
- Modify affected docs under `docs/`: keep design, roadmap, reference, and execution lifecycle status aligned with implementation.

## Steps

- [x] Promote Stage 1.7 documentation state.
  - Files: `docs/PLANS.md`, `docs/ROADMAP.md`, `docs/BACKEND.md`, `README.md`, `README.zh.md`, `ARCHITECTURE.md`, `AGENTS.md`.
  - Mark Stage 1.7 as active Python-only work.
  - Keep Stage 2 mobile runtime deferred until this plan is completed or explicitly superseded, and do not preserve stale mobile TypeScript boundary files.
  - Validate with `uv run python scripts/validate_docs.py`.

- [x] Add runtime memory protocol.
  - Files: `phone_mem/agent_runtime/prompts.py`, `phone_mem/agent_runtime/tools.py`, `docs/design-docs/python-llm-agent-runtime.md`.
  - Tests: `tests/test_agent_runtime_prompts.py`, `tests/test_agent_runtime_tools.py`.
  - Add prompt rules requiring memory search before answering questions about prior preferences, decisions, dates, people, unresolved tasks, or repeated tool failures.
  - Ensure memory remains data, not instruction, and preserve system instruction priority.
  - Route correction and deletion through governed tools instead of transient chat context.
  - Validate with `uv run python -m unittest tests.test_agent_runtime_prompts tests.test_agent_runtime_tools`.

- [x] Add governed session flush capture.
  - Files: `phone_mem/agent_runtime/session_capture.py`, `phone_mem/agent_runtime/runtime.py`, `phone_mem/personal_memory_service/constructor.py`, `docs/design-docs/memory-lifecycle-and-data-flow.md`.
  - Tests: `tests/test_agent_runtime.py`, `tests/test_memory_constructor.py`.
  - Convert transcript summaries, user corrections, tool observations, and task state into `MemoryCandidate` proposals.
  - Trigger capture on context budget pressure, turn boundaries, task boundaries, user corrections, and tool observations where important state would otherwise remain transient.
  - Classify captures as episodic by default.
  - Require explicit review policy and sufficient confidence before semantic or procedural promotion.
  - Treat auto-capture as a system-level fallback for candidate generation, not automatic durable semantic or procedural memory.
  - Reject empty captures, deduplicate repeated captures, quarantine contradictions, and audit accepted writes.
  - Validate with `uv run python -m unittest tests.test_agent_runtime tests.test_memory_constructor`.

- [x] Add hot memory capsules.
  - Files: `phone_mem/context/capsules.py`, `phone_mem/context/assembler.py`, `docs/design-docs/retrieval-and-context-assembly.md`.
  - Tests: `tests/test_context_assembler.py`.
  - Build compact capsules from permission-authorized retrieval results.
  - Include stable user-confirmed facts, active constraints, recent decisions, procedural candidates, omitted-memory reasons, evidence event IDs, confidence, attribution, and lifecycle state.
  - Enforce a small capsule budget separate from ordinary retrieval snippets.
  - Validate with `uv run python -m unittest tests.test_context_assembler`.

- [x] Upgrade retrieval to hybrid ranking.
  - Files: `phone_mem/personal_memory_service/storage.py`, `phone_mem/personal_memory_service/retrieval.py`, `docs/design-docs/retrieval-and-context-assembly.md`.
  - Tests: `tests/test_retrieval.py`, `tests/test_governance.py`.
  - Add SQLite FTS5/BM25 projection over authorized event text.
  - Keep deterministic lexical and CJK retrieval as fallback.
  - Add replaceable vector-ranking interface after permission filtering.
  - Merge lexical, vector-style, entity, recency, confidence, and importance signals through weighted union.
  - Make score weights configurable; evaluate defaults such as semantic 0.7 and BM25 0.3 through deterministic fixtures instead of treating them as architecture constants.
  - Add MMR diversity and score-component explanation metadata.
  - Validate with `uv run python -m unittest tests.test_retrieval tests.test_governance`.

- [x] Add relation graph projection.
  - Files: `phone_mem/personal_memory_service/relations.py`, `phone_mem/personal_memory_service/storage.py`, `phone_mem/context/assembler.py`, `docs/DATA.md`.
  - Tests: `tests/test_storage.py`, `tests/test_context_assembler.py`.
  - Derive typed relation projections for people, projects, decisions, tasks, tools, errors, and solved-by links from canonical event JSON.
  - Keep relation nodes and edges rebuildable from canonical events and lineage.
  - Invalidate relation paths when source events are deleted, superseded, or quarantined.
  - Track context compression and relation evidence quality before adding heavier ranking strategies such as personalized PageRank.
  - Validate with `uv run python -m unittest tests.test_storage tests.test_context_assembler`.

- [x] Add reflection, defrag, and schema maintenance.
  - Files: `phone_mem/personal_memory_service/maintenance.py`, `phone_mem/personal_memory_service/service.py`, `docs/design-docs/personal-memory-service.md`.
  - Tests: `tests/test_personal_memory_service.py`, `tests/test_memory_maintenance.py`.
  - Implement dry-run `reflect()` proposals for semantic and procedural candidates from eligible episodic clusters.
  - Implement dry-run `defrag()` reports for duplicates, stale superseded chains, missing lineage, and orphaned projections.
  - Implement `schema_diff()` comparing observed event fields and relation types against `docs/DATA.md`.
  - Prevent silent semantic or procedural promotion.
  - Validate with `uv run python -m unittest tests.test_personal_memory_service tests.test_memory_maintenance`.

- [ ] Add quality metrics and fixture refresh.
  - Files: `phone_mem/personal_memory_service/metrics.py`, `docs/PYTHON_REFERENCE.md`, `docs/ROADMAP.md`, `tests/fixtures/memory_service/*.json`.
  - Tests: `tests/test_service_context_metrics.py`, `tests/test_stage2_mobile_contract_fixtures.py`.
  - Track retrieval hit counts, score component distributions, context compression ratio, capsule token use, omitted-memory reasons, capture proposal counts, reflection acceptance rate, deletion propagation coverage, and audit completeness.
  - Use compression metrics to compare flat retrieval, capsule assembly, bounded relation paths, and any later graph-ranking experiments.
  - Refresh future-mobile contract fixtures only after Python behavior stabilizes.
  - Validate with `uv run python -m unittest tests.test_service_context_metrics tests.test_stage2_mobile_contract_fixtures`.

- [ ] Run final verification and close the plan.
  - Commands:
    - `uv run python -m unittest discover -s tests`
    - `uv run python scripts/validate_docs.py`
  - Move this plan to `docs/exec-plans/completed/` only after tests pass and docs reflect the final Stage 1.7 behavior.
  - Keep mobile implementation deferred unless a separate Stage 2 plan is accepted after fixture refresh.

## Validation

- `uv run python -m unittest tests.test_agent_runtime_prompts tests.test_agent_runtime_tools`
- `uv run python -m unittest tests.test_agent_runtime tests.test_memory_constructor`
- `uv run python -m unittest tests.test_context_assembler`
- `uv run python -m unittest tests.test_retrieval tests.test_governance`
- `uv run python -m unittest tests.test_storage tests.test_context_assembler`
- `uv run python -m unittest tests.test_personal_memory_service tests.test_memory_maintenance`
- `uv run python -m unittest tests.test_service_context_metrics tests.test_stage2_mobile_contract_fixtures`
- `uv run python -m unittest discover -s tests`
- `uv run python scripts/validate_docs.py`

## Acceptance

- Python runtime prompts and tools enforce a clear memory protocol without bypassing service permissions.
- Session capture creates governed candidate events instead of raw transcript dumps.
- Hot memory capsules provide compact startup context with evidence IDs, permission filtering, omitted-memory reasons, and budget accounting.
- Hybrid retrieval improves recall while preserving permission-first filtering and score explanations.
- Relation graph context is derived, bounded, auditable, rebuildable, and tombstone-aware.
- Maintenance workflows provide dry-run reflection, defrag, schema drift, and projection health reports before mutation.
- Metrics make capture quality, retrieval quality, context compression, deletion propagation, and audit completeness visible.
- Shared future-mobile fixtures are refreshed from the stabilized Python oracle.
- Stage 2 mobile implementation remains deferred until this Python maturation plan is completed or explicitly superseded.
