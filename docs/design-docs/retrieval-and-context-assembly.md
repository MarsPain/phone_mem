# Retrieval And Context Assembly

## Purpose

Retrieval finds relevant memory only inside the caller's authorized memory view. Context assembly turns those authorized results into a model-runtime-neutral bundle with token budget accounting, source evidence, and safety metadata.

The Stage 1 implementation built deterministic local retrieval and context assembly in Python as a reference behavior. The completed Stage 1.5 Python LLM Agent Runtime consumes these runtime-neutral bundles for real provider-backed chat demos, while real phone runtime adapters remain a later mobile track.

## Retrieval Pipeline

1. Authenticate the caller and requested operation.
2. Resolve active permission grants into a memory view.
3. Apply privacy, app, topic, entity, layer, lifecycle, and time filters.
4. Search eligible local events using lexical, entity, recency, and metadata signals.
5. Optionally call a replaceable vector-style ranking interface after filtering.
6. Deduplicate, rerank, and apply `top_k`.
7. Shape snippets with event IDs, attribution, confidence, and explanation metadata.
8. Write an audit record for the read.

Unauthorized memory must not be scored, ranked, embedded on demand, or leaked through aggregate explanations.

## MVP Retrieval

The first implementation should use deterministic local retrieval:

- normalized text matching over `semantic_description`, using English/digit terms and CJK character n-grams for deterministic multilingual recall;
- deterministic query expansion for a small built-in preference vocabulary, with the retrieval explanation preserving expanded terms;
- entity and source filters;
- recency and confidence scoring;
- lifecycle exclusion for deleted and superseded events;
- explicit audit output.

The retrieval interface should leave room for embeddings, but embeddings are not canonical memory and should not be required for MVP correctness.

## Hybrid Ranking Projection

Stage 1.7 upgrades retrieval to a hybrid ranking pipeline while preserving the permission-first boundary. Candidate events are still selected and projected through the caller's authorized memory view before ranking-specific signals are used. SQLite FTS5/BM25 is maintained as a rebuildable projection over canonical event text and entities; deterministic lexical and CJK n-gram scoring remain the fallback when FTS does not match or is unavailable.

The Python retriever now merges lexical, BM25, replaceable vector-style, entity, recency, confidence, and importance signals through configurable weights. Defaults are runtime/reference choices, not architecture constants. Vector-style ranking is an injected interface that receives only authorized events, so unauthorized memory is never embedded, scored, or leaked through rank explanations. Final `top_k` selection applies bounded MMR diversity and records score components, weights, BM25/vector contributions, and diversity penalties in explanation metadata.

## Context Bundle

```python
class ContextAssembler:
    def build_context(self, retrieval_results: list[dict], *, task: dict, budget: dict) -> dict:
        ...
```

A `ContextBundle` contains:

- selected memory snippets;
- hot memory capsules derived only from selected authorized snippets;
- source event IDs;
- confidence and attribution;
- evidence lineage when available;
- token budget accounting;
- safety and system-priority metadata;
- omitted-memory notes when budget limits require dropping otherwise relevant results.

Hot memory capsules are compact startup projections for stable user-confirmed facts, active constraints, recent decisions, and procedural candidates. They preserve evidence event IDs, confidence, attribution, lifecycle state, and omitted-memory reasons. Capsule construction runs after permission-filtered retrieval and snippet selection, and uses a small budget recorded separately from ordinary retrieval snippet budget so capsules cannot hide context-window pressure.

## Budget Policy

The assembler reserves budget for:

- system constraints and safety policy;
- current user task and recent local interaction;
- retrieved memory snippets;
- source and confidence metadata;
- margin for tool calls and model output.

Token counting is provider-adapter pluggable. When a runtime has an exact tokenizer or reliable usage accounting, the adapter should inject that counter. When only a remote model URL is known, the reference service uses a conservative fallback based on ASCII characters, non-ASCII characters, per-snippet overhead, and a safety multiplier. The fallback intentionally prefers omitting lower-ranked memory over risking context-window overflow.

Priority order:

1. system and safety constraints;
2. user-confirmed facts and explicit task requirements;
3. recent high-confidence episodic events;
4. semantic facts with evidence lineage;
5. inferred preferences;
6. procedural suggestions that still require confirmation.

## Compression Rules

- User-confirmed constraints outrank inferred preferences.
- Recent episodic memories may keep concrete detail.
- Older episodic memories should be summarized when possible.
- Semantic facts must include evidence IDs.
- Procedural suggestions are described as candidates unless confirmed.

## Runtime Boundary

The Context Assembler does not execute prompts. Runtime adapters may target an OpenAI-compatible Python demo adapter, on-device models, local open-weight models, Apple or Android model APIs, or private-compute backends later. Those adapters receive bundles and must not query the memory store directly.

## MVP Test Coverage

- Retrieval applies permission projection before ranking.
- Deleted and superseded events are excluded.
- Search returns event IDs and explanation metadata.
- Context assembly respects token budgets.
- Context bundles preserve evidence IDs for every memory snippet.
- Context assembly creates an audit record or is traceable to audited retrieval records.
