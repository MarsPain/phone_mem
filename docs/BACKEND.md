# Backend

## Current State

The repository currently contains only a placeholder Python entrypoint. The backend should grow around a local Personal Memory Service before introducing model-runtime integrations, cloud sync, or third-party SDK access.

## Suggested Python Package Boundaries

```text
phone_mem/
├── personal_memory_service/
│   ├── events.py
│   ├── constructor.py
│   ├── storage.py
│   ├── retrieval.py
│   ├── lifecycle.py
│   └── service.py
├── governance/
│   ├── permissions.py
│   ├── audit.py
│   └── views.py
├── context/
│   ├── assembler.py
│   ├── budgets.py
│   └── snippets.py
├── runtime_adapters/
│   ├── base.py
│   └── local_stub.py
├── app_gateway/
│   ├── query.py
│   ├── write.py
│   └── subscriptions.py
└── sync/
    ├── tombstones.py
    └── cloud_client.py
```

## Implementation Rules

- Start with SQLite and deterministic Python interfaces before adding vector database or cloud dependencies.
- Keep event construction separate from storage so ingestion can be tested without persistence.
- Keep permission filtering inside the retrieval path before ranking output is returned to callers.
- Keep context assembly separate from model execution. The service emits context bundles; runtime adapters execute prompts.
- Treat embeddings as replaceable indexes, not canonical memory.
- Implement deletion before implementing cloud sync.
- Add tests for permission denial, delete propagation, deduplication, contradiction handling, audit creation, and context budget adherence.

## Model Runtime Boundary

The MVP should not depend on a specific LLM provider. Define a runtime-neutral `ContextBundle` containing:

- selected memory snippets;
- event IDs and evidence lineage;
- confidence and attribution;
- token budget accounting;
- safety and system-priority metadata.

Runtime adapters may later target Apple Foundation Models, Android AICore/Gemini Nano, local open-weight models, or private-compute backends. Those adapters must not bypass memory service permissions.

## Cloud Boundary

Cloud sync should be introduced only after local invariants are stable. The sync protocol must support:

- append-only event upload for allowed privacy classes;
- tombstone propagation;
- client-side encryption metadata;
- private-compute policy metadata for eligible high-compute inference;
- idempotent replay;
- conflict resolution based on event lineage and updated timestamps.
