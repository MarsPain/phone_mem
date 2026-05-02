# Research Review 2026

This review upgrades the repository from a PDF-derived design to a research-backed v2 architecture. It is not a full academic survey; it is a focused engineering review of sources that materially change the system design.

## Sources Reviewed

- Source PDF: [手机端Agent_Memory架构设计方案.pdf](../../手机端Agent_Memory架构设计方案.pdf)
- MemGPT: OS-style virtual context and memory hierarchy for LLM agents. [arXiv:2310.08560](https://arxiv.org/abs/2310.08560)
- Mem0: production-oriented long-term memory extraction, consolidation, graph memory, latency, and token-cost evaluation. [arXiv:2504.19413](https://arxiv.org/abs/2504.19413)
- CAMPHOR: on-device SLM multi-agent architecture for personal context retrieval, tool interaction, dynamic planning, parameter sharing, and prompt compression. [arXiv:2410.09407](https://arxiv.org/abs/2410.09407)
- LLM as a System Service on Mobile Devices: OS-level LLMaaS, persistent state, KV-cache compression, swapping, and context-switch latency. [arXiv:2403.11805](https://arxiv.org/abs/2403.11805)
- Elastic On-Device LLM Service: latency-SLO-aware on-device model and prompt elasticity for mobile agents. [arXiv:2409.09071](https://arxiv.org/abs/2409.09071)
- On-device LLM personalization with smartphone sensing: privacy, latency, cost, battery, and context-aware sensing tradeoffs. [arXiv:2407.04418](https://arxiv.org/abs/2407.04418)
- Apple Foundation Models framework: on-device model access, offline privacy-preserving app intelligence, guided generation, and tool calling. [Apple Newsroom](https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/)
- Apple Private Cloud Compute: cloud AI privacy boundary with verifiable private compute goals. [Apple Security Research](https://security.apple.com/com/blog/private-cloud-compute/)
- Android Gemini Nano/AICore: system service for on-device inference, local processing, safety, isolation, and no direct cloud dependency for prompts. [Android Developers](https://developer.android.com/ai/gemini-nano)

## What The PDF Got Right

- A phone memory system must be local-first because the phone holds the densest personal context.
- Four memory layers remain useful: working, episodic, semantic, and procedural.
- Unified event abstraction is the right ingestion target for multimodal and app signals.
- Hybrid retrieval is required; semantic search alone is not enough.
- Permissioned SDK/API access is necessary for cross-app memory.
- Lifecycle management matters as much as storage: filtering, normalization, consolidation, contradiction detection, deletion, and audit are core behavior.

## What v2 Changes

### 1. Memory Is An OS-Level Service, Not Just An SDK

The PDF treats Memory SDK as the ecosystem interface. Research on mobile LLM system services shows the platform also needs an OS-level memory and model-runtime boundary. Memory should be owned by a service that manages canonical events, permissions, audit, retrieval, context assembly, and deletion. Apps and agents should never share a database directly.

Design implication: implement `PersonalMemoryService` before broad SDK exposure.

### 2. Separate Memory Service From Model Runtime

MemGPT motivates virtual context management, but mobile systems add KV-cache lifecycle, context switching, SLO, prompt compression, and model elasticity. These are runtime concerns, not memory-store concerns.

Design implication: memory retrieval returns traceable, scoped snippets and metadata. A separate context assembler decides what enters the model prompt under token, latency, and safety budgets.

### 3. Use On-Device Small-Model Agents Before Cloud Reasoning

CAMPHOR suggests a stronger local architecture than the PDF's simple "edge real-time plus cloud deep" split: an on-device coordinator can route work to specialized agents for personal context retrieval, tool interaction, and planning, using prompt compression and shared parameters.

Design implication: cloud should not be the default deep reasoning layer. The first advanced runtime should be local coordinator plus specialist modules, with cloud only for eligible, high-latency, user-approved tasks.

### 4. Treat Private Cloud As A Different Trust Boundary

Apple PCC-style systems make "cloud" too broad as an architecture word. There are at least three cloud classes: ordinary backend, client-encrypted archive, and verifiable private compute. They have different privacy promises and allowable data.

Design implication: docs must distinguish `device_only`, `client_encrypted_sync`, `private_compute`, and `cloud_indexable` policies.

### 5. Make Platform Reality A First-Class Constraint

Apple Foundation Models and Android AICore/Gemini Nano show that on-device LLM access is becoming a platform primitive. The memory architecture should integrate with OS-provided model services, guided generation, tool calling, app intents/entities, safety filters, and model update mechanisms instead of assuming a custom model stack.

Design implication: the prototype can be Python, but the architecture should avoid baking in assumptions that fight iOS/Android service boundaries.

### 6. Add Quantitative Acceptance Criteria

Mem0 reports memory quality, latency, and token-cost benefits, while mobile LLM service papers evaluate context-switch latency and device constraints. The PDF gives architecture but few measurable gates.

Design implication: roadmaps and execution plans need explicit metrics: p95 retrieval latency, permission denial correctness, deletion propagation correctness, token budget adherence, audit completeness, and memory quality evaluation.

## v2 Architecture Thesis

Build an OS-level Personal Memory Service with:

- local canonical memory store;
- permissioned memory views;
- audit and deletion propagation;
- hybrid retrieval and evidence lineage;
- model-runtime-independent context assembly;
- optional on-device specialist agents for planning/retrieval/tool use;
- optional privacy-compute/cloud components only behind explicit data policies.

The cloud is an accelerator. The phone is the trust root and interaction root.

## Recommended MVP Change

The previous MVP, "local memory core," was directionally right but too storage-centric. The v2 MVP should prove service boundaries:

- `PersonalMemoryService.record()`
- `PersonalMemoryService.search()`
- `PersonalMemoryService.explain()`
- `PersonalMemoryService.correct()`
- `PersonalMemoryService.delete()`
- `ContextAssembler.build_context()`
- `PermissionService.grant()/revoke()`
- `AuditLog.list()`

No always-on sensing, third-party marketplace, graph database, cloud sync, or learned forgetting should enter the MVP.

## Open Questions

- Which mobile platform is the first real target: iOS, Android, or platform-neutral research prototype?
- Should the first runtime integrate a local model provider or only expose model-runtime-neutral context assembly?
- What benchmark set should represent memory quality: synthetic personal tasks, LOCOMO-style long conversation QA, or custom smartphone task traces?
- What is the minimum user-facing governance UI needed before testing with realistic personal data?
