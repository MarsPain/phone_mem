import type { ContextBundle } from "../context/context";
import type { AuditRecord } from "../governance/audit";
import type { PermissionGrant, PermissionScope } from "../governance/permissions";
import type { MemoryEvent } from "../memory_core/events";
import type { RetrievalResult } from "../retrieval/retrieval";

export interface PersonalMemoryService {
  record(event: MemoryEvent, caller: string): Promise<string>;
  search(query: string, caller: string, topK?: number): Promise<RetrievalResult[]>;
  explain(eventId: string, caller: string): Promise<Record<string, unknown>>;
  correct(eventId: string, patch: Record<string, unknown>, caller: string): Promise<string>;
  deleteByEventId(eventId: string, caller: string, reason: string): Promise<string[]>;
  grant(caller: string, scope: PermissionScope, durationSeconds: number): Promise<PermissionGrant>;
  revoke(grantId: string): Promise<void>;
  audit(): Promise<AuditRecord[]>;
  buildContext(
    query: string,
    caller: string,
    task: Record<string, unknown>,
    budget: Record<string, number>,
    topK?: number,
  ): Promise<ContextBundle>;
}
