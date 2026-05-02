# Memory SDK Product Spec

## Goal

Expose smartphone Agent Memory as a governed platform capability. The core product is the Personal Memory Service; the SDK is the facade that lets apps and agents request scoped memory views instead of accessing the global store.

## Interface Layers

- L1 System: full local memory administration, sync, consolidation, and deletion propagation. OS and system assistant only.
- L2 Profile: read and update app-relevant semantic profile dimensions. Requires user authorization and app identity verification.
- L3 Episodic: read and write authorized event memories by topic, app, entity, and time range. Requires explicit grant.
- L4 Trigger: subscribe to context or memory changes inside a bounded scope. Requires user-visible enablement.

## Service Boundary

Apps call SDK APIs. SDK APIs call the Personal Memory Service. Model runtimes consume `ContextBundle` outputs from the Context Assembler. No app, agent, or runtime adapter may read the canonical memory store directly.

## Query API

```typescript
search(query: string, options: {
  memoryTypes?: ("episodic" | "semantic" | "procedural")[];
  timeRange?: { start: Date; end: Date };
  entities?: string[];
  topics?: string[];
  modalities?: ("voice" | "visual" | "text" | "sensor" | "app")[];
  topK?: number;
  minScore?: number;
}): Promise<MemoryResult[]>
```

Rules:

- Permission projection is applied before ranking.
- Results include event IDs, confidence, source attribution, and explanation metadata.
- Raw sensitive content is never returned to third-party callers.

## Write API

```typescript
record(event: ApplicationEvent): Promise<MemoryEventId>
correct(eventId: string, patch: MemoryPatch): Promise<MemoryEventId>
delete(selector: MemorySelector, reason: string): Promise<DeleteResult>
```

Rules:

- Third-party writes are app-scoped by default.
- Profile updates become proposals unless the caller owns the profile dimension and has an active grant.
- Deletes create tombstones and must propagate to derived data.

## Governance API

```typescript
requestPermission(scope: MemoryScope, duration: Duration): Promise<PermissionGrant>
queryGrantedScopes(): Promise<MemoryScope[]>
revokePermission(grantId: string): Promise<void>
explainUsage(eventId: string): Promise<MemoryExplanation>
subscribe(filter: MemoryFilter, callback: ChangeHandler): Subscription
```

## Context Assembly API

```typescript
buildContext(task: AgentTask, options: {
  maxTokens: number;
  caller: string;
  requiredScopes: MemoryScope[];
  safetyReserveTokens?: number;
}): Promise<ContextBundle>
```

Rules:

- Context assembly runs after permissioned retrieval.
- The bundle includes evidence event IDs and attribution metadata.
- System constraints and user-confirmed facts outrank inferred preferences.
- The API is model-runtime-neutral.

## Required UX Contracts

- Permission prompts must name memory layer, topic/entity scope, time range, and operation type.
- Users can inspect what was read or written by an app.
- Users can revoke grants and delete app-contributed memory.
- Inferred memories are labeled as inferred, not user-stated.
- Memory use explanations must show which event IDs influenced a response or action.
