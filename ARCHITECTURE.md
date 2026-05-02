# Architecture

`phone-mem` targets a local-first OS-level Personal Memory Service for smartphone agents. The phone owns durable personal memory, permission enforcement, audit, deletion, fast retrieval, and context assembly. On-device model runtimes consume scoped memory views through service APIs. Cloud systems are optional privacy-compute accelerators, not the default source of truth.

## Top-Level Domains

- Memory ingestion: turns authorized app, voice, visual, and sensor signals into normalized memory events.
- Memory service: owns canonical events, projections, permissions, audit, tombstones, and retrieval APIs.
- Model runtime boundary: assembles token-budgeted context for on-device or private-cloud models without exposing the global memory store.
- Retrieval and routing: fuses semantic, lexical, entity, metadata, context, and recency signals after permission projection.
- Governance: enforces consent, memory views, source attribution, audit logs, deletion, and explanation.
- SDK surface: exposes scoped read, write, subscription, and governance APIs for system agents first and third-party apps later.

## Canonical Design Docs

- [docs/DESIGN.md](docs/DESIGN.md): system overview and key contracts.
- [docs/design-docs/smartphone-agent-memory.md](docs/design-docs/smartphone-agent-memory.md): detailed architecture and development guidance.
- [docs/design-docs/personal-memory-service.md](docs/design-docs/personal-memory-service.md): local service boundary and MVP operations.
- [docs/design-docs/memory-lifecycle-and-data-flow.md](docs/design-docs/memory-lifecycle-and-data-flow.md): memory event lifecycle and data flow.
- [docs/design-docs/retrieval-and-context-assembly.md](docs/design-docs/retrieval-and-context-assembly.md): retrieval and context assembly boundary.
- [docs/design-docs/governance-permissions-audit.md](docs/design-docs/governance-permissions-audit.md): permissions, memory views, audit, and explanation.
- [docs/DATA.md](docs/DATA.md): canonical memory event model, lifecycle, and storage rules.
- [docs/SECURITY.md](docs/SECURITY.md): privacy, permission, sync, deletion, and abuse boundaries.
- [docs/BACKEND.md](docs/BACKEND.md): service and SDK implementation boundaries.
- [docs/product-specs/memory-sdk.md](docs/product-specs/memory-sdk.md): SDK product/API spec.
- [docs/references/research-review-2026.md](docs/references/research-review-2026.md): evidence and rationale for the v2 architecture.

## Current Code State

The runtime is not implemented yet. `main.py` is a placeholder, and the first engineering milestone should create the Python reference Personal Memory Service described in [docs/exec-plans/active/mvp-local-memory-core.md](docs/exec-plans/active/mvp-local-memory-core.md). The first real iPhone and Android runtime should mirror that service boundary in React Native, TypeScript, and on-device SQLite.
