# Backend And Runtime Strategy

## Current State

The repository contains a completed deterministic Python reference implementation of the Personal Memory Service under `phone_mem/`. `main.py` remains a placeholder entrypoint, but the reference package, examples, tests, and contract fixtures are the current executable specification. The completed Stage 1.5 track adds a real LLM-backed Python Agent runtime around this service without moving provider concerns into the memory core.

The product target is still a phone-local Personal Memory Service. Python is not the intended production mobile runtime. It is the fastest way to make the architecture executable, prove lifecycle invariants, and create a test oracle that the mobile runtime can follow.

The Python reference covers the Stage 1 memory core and the completed maturation track: canonical event construction, SQLite persistence, scoped permissions, audit records, governed retrieval, runtime-neutral context assembly, correction, deletion tombstones, lifecycle explanations, structured service errors, mobile contract fixtures, and MVP metrics hooks. It remains a reference implementation rather than the production mobile runtime.

## Runtime Tracks

### Track 1: Python Reference Implementation

Use Python on the development machine as the completed executable specification for the memory core:

- canonical event model;
- local SQLite persistence;
- permission-scoped retrieval;
- audit records;
- correction and deletion tombstones;
- context bundle assembly;
- deterministic lifecycle tests.

This track is complete as an implementation track. Continue to keep it correct, deterministic, and aligned with contract fixtures when bugs or mobile parity questions reveal a necessary reference change. It should not depend on iOS or Android runtime assumptions.

### Track 2: Python LLM Agent Runtime Spike

Use Python on the development machine to prove the real Agent loop before mobile runtime work resumes. This spike is complete and includes:

- provider-neutral `LLMClient` interface;
- fake deterministic client for tests;
- OpenAI-compatible adapter for local real-provider use;
- runtime orchestration over governed retrieval, context assembly, model calls, memory tools, and response evidence;
- interactive chat example under `examples/`.

This track may import the memory service, but the memory service must not import provider adapters. The first implementation lives under `phone_mem/agent_runtime/` and is exercised by fake-client and injected-transport tests so default verification stays network-free. It is documented in [design-docs/python-llm-agent-runtime.md](design-docs/python-llm-agent-runtime.md) and tracked by [PLANS.md](PLANS.md).

### Track 3: Real Mobile Runtime Prototype

Use React Native, TypeScript, and on-device SQLite for the first iPhone and Android runtime prototype. In this stage, "service" means an app-internal local service module with clear APIs, not a background daemon.

The TypeScript mobile runtime should mirror the Python reference boundaries:

```text
mobile/
├── memory_core/
│   ├── events.ts
│   ├── constructor.ts
│   ├── lifecycle.ts
│   └── service.ts
├── governance/
│   ├── permissions.ts
│   ├── audit.ts
│   └── views.ts
├── storage/
│   └── sqlite.ts
├── retrieval/
│   └── local_retrieval.ts
├── context/
│   └── assembler.ts
└── ui/
```

If later stages require deeper platform integration, performance-sensitive or system-facing modules can move into Swift, Kotlin, Kotlin Multiplatform, or Rust native modules without changing the Personal Memory Service contract.

## Reference Python Package Boundaries

```text
phone_mem/
├── agent_runtime/
│   ├── client.py
│   ├── openai_client.py
│   ├── prompts.py
│   ├── runtime.py
│   └── tools.py
├── personal_memory_service/
│   ├── events.py
│   ├── constructor.py
│   ├── storage.py
│   ├── retrieval.py
│   ├── lifecycle.py
│   ├── metrics.py
│   └── service.py
├── governance/
│   ├── permissions.py
│   ├── audit.py
│   └── views.py
├── context/
│   ├── assembler.py
│   ├── budgets.py
│   └── snippets.py
├── app_gateway/
│   ├── query.py
│   ├── write.py
│   └── subscriptions.py
└── sync/
    ├── tombstones.py
    └── cloud_client.py
```

## Implementation Rules

- Keep SQLite and deterministic Python interfaces as the reference baseline before adding vector database or cloud dependencies in later tracks.
- Treat Python as the reference implementation and test oracle, not the final phone runtime.
- Keep Python and TypeScript API contracts aligned around the same domain operations: record, search, explain, correct, delete, grant, revoke, audit, and build context.
- Avoid Python-only architectural assumptions that would fight iOS or Android app lifecycles.
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

The Stage 1.5 Python runtime includes an OpenAI-compatible adapter for developer-machine chat demos. That adapter is an outer runtime concern and uses runtime-neutral context bundles plus memory service tools instead of direct storage access.

## Cloud Boundary

Cloud sync should be introduced only after local invariants are stable. The sync protocol must support:

- append-only event upload for allowed privacy classes;
- tombstone propagation;
- client-side encryption metadata;
- private-compute policy metadata for eligible high-compute inference;
- idempotent replay;
- conflict resolution based on event lineage and updated timestamps.
