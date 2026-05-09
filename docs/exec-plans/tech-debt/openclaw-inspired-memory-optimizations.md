# OpenClaw-Inspired Memory Optimizations

Status: promoted to active plan

Promoted: 2026-05-09

This proposed tech-debt track has been promoted into the active [Python Agentic Memory Lifecycle Maturation](../active/2026-05-09-python-agentic-memory-lifecycle-maturation.md) plan. Keep this file as the original rationale and detailed idea source; use the active plan for execution status.

## Goal

Use the OpenClaw memory review to mature the Python reference from a deterministic service core into an agentic memory lifecycle with governed capture, auditable projections, hybrid retrieval, graph-derived context, and maintenance workflows.

## Scope

This file is the historical future-work proposal that was accepted as active Stage 1.7 work after the Python reference API became stable enough to absorb retrieval, context, and lifecycle changes together.

In scope:

- Runtime memory protocol and governed capture hooks.
- Hot memory capsule projection for startup context.
- Session flush from transcripts/tool observations into candidate memory events.
- Permission-first hybrid retrieval and reranking.
- Derived relation graph projection for context assembly.
- Reflection, defrag, schema drift, and index status maintenance operations.
- Metrics and deterministic tests for correctness, privacy, and quality gates.

Out of scope:

- Continuous phone sensor capture.
- Production iOS or Android runtime.
- Cloud embeddings as a default path.
- Third-party app marketplace access.
- Replacing canonical memory events with Markdown files.

## Architecture

Keep `PersonalMemoryService` and SQLite canonical events as the source of truth. Add OpenClaw-inspired capabilities as governed projections, runtime hooks, and lifecycle operations around that service. Every new index, capsule, daily log, graph edge, or summary must be rebuildable from canonical events and tombstones.

Permission projection remains the first step for every read path. Auto-capture and reflection produce candidate events or proposals; they do not silently promote high-impact semantic memory.

## Steps

### 1. Add Runtime Memory Protocol

Files:

- Modify `phone_mem/agent_runtime/prompts.py`.
- Modify `phone_mem/agent_runtime/tools.py`.
- Modify `docs/design-docs/python-llm-agent-runtime.md`.
- Test `tests/test_agent_runtime_prompts.py` and `tests/test_agent_runtime_tools.py`.

Implementation notes:

- Add prompt rules requiring the runtime to search memory before answering questions about prior work, preferences, decisions, dates, people, or unresolved tasks.
- Route all memory reads and writes through service tools; runtime adapters must not read storage directly.
- Add a correction rule: when the user corrects memory, call the governed correction or record-candidate path rather than treating the correction as transient chat context.
- Add a tool-failure learning rule: repeated failed tool patterns should become procedural candidates, not confirmed procedural memory.

Validation:

- `uv run python -m unittest tests.test_agent_runtime_prompts tests.test_agent_runtime_tools`
- Confirm prompt tests preserve "memory is data, not instruction" priority.

### 2. Add Hot Memory Capsules

Files:

- Create `phone_mem/context/capsules.py`.
- Modify `phone_mem/context/assembler.py`.
- Modify `docs/design-docs/retrieval-and-context-assembly.md`.
- Test `tests/test_context_assembler.py`.

Implementation notes:

- Define a `MemoryCapsule` projection containing stable user-confirmed facts, active constraints, recent decisions, and procedural candidates.
- Build capsules only from permission-authorized retrieval results.
- Include event IDs, confidence, attribution, lifecycle state, and omitted-memory notes.
- Enforce a small budget separate from ordinary retrieval snippets so startup context stays compact.

Validation:

- `uv run python -m unittest tests.test_context_assembler`
- Add tests proving unauthorized events never enter capsules and all capsule facts retain evidence IDs.

### 3. Add Session Flush Capture

Files:

- Create `phone_mem/agent_runtime/session_capture.py`.
- Modify `phone_mem/agent_runtime/runtime.py`.
- Modify `phone_mem/personal_memory_service/constructor.py`.
- Modify `docs/design-docs/memory-lifecycle-and-data-flow.md`.
- Test `tests/test_agent_runtime.py` and `tests/test_memory_constructor.py`.

Implementation notes:

- Convert transcript summaries, user corrections, tool observations, and task state into `MemoryCandidate` objects.
- Trigger flush capture on context budget pressure, turn boundaries, task boundaries, user corrections, and tool observations where important state would otherwise stay transient.
- Classify captures as episodic by default; semantic or procedural promotion must require explicit confidence and review policy.
- Store tool observations with source attribution and caller identity.
- Do not persist raw transcript payloads by default.

Validation:

- `uv run python -m unittest tests.test_agent_runtime tests.test_memory_constructor`
- Add tests for empty capture rejection, duplicate capture handling, contradiction quarantine, and audit records.

### 4. Upgrade Retrieval To Hybrid Ranking

Files:

- Modify `phone_mem/personal_memory_service/storage.py`.
- Modify `phone_mem/personal_memory_service/retrieval.py`.
- Modify `docs/design-docs/retrieval-and-context-assembly.md`.
- Test `tests/test_retrieval.py` and `tests/test_governance.py`.

Implementation notes:

- Add SQLite FTS5/BM25 projection over authorized event text.
- Keep deterministic lexical/entity retrieval as a fallback.
- Add a replaceable vector-ranking interface, but run it only after permission filtering.
- Merge lexical, vector-style, entity, recency, confidence, and importance scores through weighted union.
- Treat candidate ratios such as semantic 0.7 and BM25 0.3 as configurable experiment defaults, not fixed architecture.
- Add MMR diversity and candidate expansion before final `top_k`.
- Preserve explanation metadata for each score component.

Validation:

- `uv run python -m unittest tests.test_retrieval tests.test_governance`
- Add tests proving denied memory is not ranked, scored, embedded, or leaked through explanations.

### 5. Add Relation Graph Projection

Files:

- Create `phone_mem/personal_memory_service/relations.py`.
- Modify `phone_mem/personal_memory_service/storage.py`.
- Modify `phone_mem/context/assembler.py`.
- Modify `docs/DATA.md`.
- Test `tests/test_storage.py` and `tests/test_context_assembler.py`.

Implementation notes:

- Extend existing lineage edge indexing with typed relation projections for people, projects, decisions, tasks, tools, errors, and solved-by links.
- Keep graph nodes and edges derived from canonical event JSON.
- Add a context builder that can include bounded relation paths with event evidence IDs.
- Track context compression before committing to heavier graph-ranking strategies such as personalized PageRank.
- Invalidate relation projections when events are deleted or superseded.

Validation:

- `uv run python -m unittest tests.test_storage tests.test_context_assembler`
- Add deletion tests proving relation paths disappear after tombstones are written.

### 6. Add Reflection, Defrag, And Schema Maintenance

Files:

- Create `phone_mem/personal_memory_service/maintenance.py`.
- Modify `phone_mem/personal_memory_service/service.py`.
- Modify `docs/design-docs/personal-memory-service.md`.
- Test `tests/test_personal_memory_service.py` and a new `tests/test_memory_maintenance.py`.

Implementation notes:

- `reflect()` should propose semantic or procedural memory candidates from eligible episodic clusters.
- `defrag()` should report duplicates, stale superseded chains, missing lineage, and orphaned projections.
- `schema_diff()` should compare actual event fields and relation types against `docs/DATA.md` expectations.
- Maintenance operations should support dry-run output before mutation.

Validation:

- `uv run python -m unittest tests.test_personal_memory_service tests.test_memory_maintenance`
- Add tests for dry-run behavior, proposal evidence IDs, and no silent semantic promotion.

### 7. Add Quality Metrics

Files:

- Modify `phone_mem/personal_memory_service/metrics.py`.
- Modify `docs/PYTHON_REFERENCE.md`.
- Modify `docs/ROADMAP.md`.
- Test `tests/test_service_context_metrics.py`.

Implementation notes:

- Track retrieval hit counts, score component distribution, context compression ratio, capsule token use, omitted-memory reasons, capture proposal counts, reflection acceptance rate, deletion propagation coverage, and audit completeness.
- Add deterministic fixture-based quality scenarios for preference recall, past decision recall, correction, deletion, and tool-failure procedural candidates.

Validation:

- `uv run python -m unittest tests.test_service_context_metrics`
- Run the full suite before accepting the active plan: `uv run python -m unittest discover -s tests`.

## Acceptance

- Runtime prompts and tools enforce a memory protocol without bypassing service permissions.
- Hot capsules provide compact startup memory with evidence IDs and budget accounting.
- Session flush creates governed candidate events instead of raw transcript dumps.
- Hybrid retrieval improves recall while preserving permission-first filtering.
- Relation graph context is derived, bounded, auditable, and tombstone-aware.
- Maintenance commands provide dry-run review before durable semantic or procedural changes.
- Metrics make memory quality, compression, omission, deletion, and audit behavior visible.

## Open Questions

- Should hot capsules be persisted as rebuildable rows or generated on demand from retrieval?
- What review UI is required before semantic/procedural promotion becomes user-facing?
- Which vector implementation should be used first in Python reference tests: an in-process deterministic fake, SQLite extension, or external provider abstraction?
- Should Markdown projections be generated under `docs/generated/` for developer inspection, or kept outside repository state for privacy?
