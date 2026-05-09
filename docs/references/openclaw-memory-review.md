# OpenClaw Memory Review

## Source Resolution

- Source: [OpenClaw及其Memory.pdf](../../OpenClaw及其Memory.pdf)
- Coverage: full local PDF text was extracted and reviewed, 17 pages.
- Ambiguity: this is a secondary research document, not a primary OpenClaw specification. Its implementation claims should be treated as design inspiration unless later verified against primary OpenClaw source code or documentation.
- Task type: single-document deep read plus architecture transfer for Smartphone Agent Memory.

## What The Document Says

OpenClaw frames memory as part of the Agent runtime rather than a passive vector database. Its memory system combines four layers:

- Ephemeral session memory in the active context window plus JSONL transcripts.
- Short-term daily logs in append-only Markdown files.
- Curated long-term memory in compact bootstrap files such as `MEMORY.md`.
- Semantic memory through SQLite-backed text, vector, and optional graph indexes.

The design repeatedly emphasizes human-auditable memory. Markdown files are treated as the primary operator-facing medium because they are readable, editable, diffable, and easy to review with Git. SQLite and vector indexes are positioned as rebuildable acceleration layers rather than the human trust surface.

OpenClaw also treats memory as an active lifecycle. Important mechanisms include session compaction, silent memory flushes before context overflow, periodic reflection from short-term notes into long-term memory, defragmentation of stale or duplicate memories, schema validation, and maintenance commands such as recall, remember, reflect, defrag, and schema diff.

Retrieval is described as hybrid and iterative. The document highlights weighted union of semantic vector search and BM25 or full-text search, maximum marginal relevance for diversity, temporal decay for recency-sensitive ranking, candidate expansion before reranking, and graph-based recall through entity links, community summaries, and personalized PageRank. Retrieval can be exposed as a tool in the ReAct loop, while some systems also auto-inject relevant memory into context.

The Agent execution model is intentionally simple: single-session serialization, ReAct loops, tool execution feedback, compact skill lists with lazy loading, and bootstrap files that give the model stable behavior. The complexity is pushed into context assembly, memory indexing, lifecycle maintenance, and operator-visible files instead of explicit multi-agent state machines.

## What Matters For This Project

The strongest transfer is not "use Markdown as the database." Smartphone Agent Memory has stricter privacy, schema, deletion, and permission requirements, so the canonical source of truth should remain the local Personal Memory Service and its structured event store. The OpenClaw lesson is that the service also needs operator-facing projections and lifecycle ergonomics. Users and developers need to inspect, edit, diff, repair, and understand memory without reverse-engineering raw SQLite rows.

OpenClaw's bootstrap memory maps well to a governed "hot memory capsule" in this project: a small, permission-filtered, token-budgeted projection of stable user facts, active constraints, recent decisions, and procedural hints. It should be generated from canonical events, preserve evidence IDs, and never bypass read permissions.

OpenClaw's daily logs and flush mechanism map to session-to-episodic capture. For this project, a flush should not silently write raw transcripts. It should summarize current interaction state into candidate memory events when context budget pressure, turn boundaries, task boundaries, tool observations, or user corrections make loss likely. The capture path should apply read-before-write validation, classify privacy, and record audit entries. User correction and high-impact semantic promotion should remain reviewable.

The retrieval guidance is directly useful. The current reference retriever is deterministic lexical/entity/recency scoring. A next version can add permission-first FTS5/BM25, a replaceable embedding projection, weighted union, MMR diversity, temporal decay, and candidate expansion, while preserving the invariant that unauthorized memory is never scored or embedded on demand. Ratios such as semantic 0.7 and BM25 0.3 are useful experiment defaults, not architectural invariants; the reference should expose weights as configuration and validate them with deterministic fixtures.

Graph memory should be a projection, not canonical state. The repository already has lineage edges; OpenClaw suggests extending this into typed relation projections for tasks, skills, people, projects, decisions, errors, and solved-by links. This would improve context assembly for relational questions without weakening deletion propagation, because graph nodes and edges can be rebuilt or invalidated from canonical event lineage and tombstones. Personalized PageRank and community summaries are promising ranking strategies for later experiments, but Stage 1.7 should first make relation evidence, invalidation, and context compression metrics reliable.

OpenClaw's skills and memory protocols are also relevant. This project's agent runtime should learn operational rules such as: search memory before answering past-work questions, record user corrections as candidate memory, record repeated tool failures as procedural candidates, and explain which memory influenced an answer. These rules belong at the runtime/prompt/tool boundary, while actual writes remain governed service operations.

## Adopt, Adapt, Avoid

Adopt:

- Memory as an Agent lifecycle, not a storage feature.
- Explicit memory protocol for runtime behavior.
- Human-auditable memory projections and review workflows.
- Hybrid retrieval with lexical, vector-style, recency, diversity, and entity signals.
- Maintenance operations for reflection, defrag, schema drift, and index status.
- Task and procedural memory that survives context compaction.

Adapt:

- Markdown should be an export and review surface, not the canonical phone memory store.
- Auto-capture should be a system-level fallback that produces candidate events with permissions, privacy classification, audit, and review gates; it should not automatically promote high-impact semantic or procedural memory.
- Bootstrap memory should become permission-scoped hot capsules with evidence IDs, not raw global memory injection.
- Graph memory should remain a derived projection tied to tombstone propagation.
- Retrieval-as-tool should coexist with system-triggered recall, both mediated by permissioned service APIs.

Avoid:

- Loading long-term memory wholesale into all sessions.
- Letting Agent self-writes bypass validation or user correction flows.
- Treating cloud embedding fallback as a default path for personal or sensitive memory.
- Making graph or vector indexes source-of-truth stores.
- Letting external agents consume raw global memory instead of governed views.

## Design Implications

The next architecture improvement should add a layer of "agentic memory operations" above the current deterministic reference core:

1. Session memory capture and flush creates candidate episodic events from runtime summaries and tool observations when context pressure, turn boundaries, task boundaries, corrections, or tool feedback make memory loss likely.
2. Hot memory capsules provide compact startup context for allowed callers.
3. Hybrid retrieval improves recall without relaxing permission-first filtering, with configurable score weights and deterministic quality fixtures.
4. Relation projections and graph context builders support multi-hop context assembly before adding heavier graph-ranking strategies such as personalized PageRank.
5. Reflection and defrag commands produce auditable proposals before changing durable semantic or procedural memory.
6. Metrics track retrieval quality, context compression, capture precision, deletion propagation, and audit completeness.

These changes preserve the project's thesis: the phone-owned Personal Memory Service remains the trust root, and broader agents consume governed views rather than the raw store.
