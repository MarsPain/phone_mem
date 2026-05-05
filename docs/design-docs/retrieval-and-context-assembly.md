# Retrieval And Context Assembly

## Purpose

Retrieval finds relevant memory only inside the caller's authorized memory view. Context assembly turns those authorized results into a model-runtime-neutral bundle with token budget accounting, source evidence, and safety metadata.

The Stage 1 implementation built deterministic local retrieval and context assembly in Python as a reference behavior. The active Stage 1.5 Python LLM Agent Runtime may consume these runtime-neutral bundles for real provider-backed chat demos, while real phone runtime adapters remain a later mobile track.

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

- normalized text matching over `semantic_description`;
- entity and source filters;
- recency and confidence scoring;
- lifecycle exclusion for deleted and superseded events;
- explicit audit output.

The retrieval interface should leave room for embeddings, but embeddings are not canonical memory and should not be required for MVP correctness.

## Context Bundle

```python
class ContextAssembler:
    def build_context(self, retrieval_results: list[dict], *, task: dict, budget: dict) -> dict:
        ...
```

A `ContextBundle` contains:

- selected memory snippets;
- source event IDs;
- confidence and attribution;
- evidence lineage when available;
- token budget accounting;
- safety and system-priority metadata;
- omitted-memory notes when budget limits require dropping otherwise relevant results.

## Budget Policy

The assembler reserves budget for:

- system constraints and safety policy;
- current user task and recent local interaction;
- retrieved memory snippets;
- source and confidence metadata;
- margin for tool calls and model output.

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
