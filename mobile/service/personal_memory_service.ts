import type { ContextBundle } from "../context/context";
import type { AuditRecord } from "../governance/audit";
import type { AuditOperation, PermissionGrant, PermissionScope } from "../governance/permissions";
import type { MemoryEvent, MemoryExplanation, MemorySelector } from "../memory_core/events";
import type { RetrievalResult } from "../retrieval/retrieval";

export interface SearchOptions {
  scope?: MemorySelector;
  topK?: number;
}

export interface BuildContextOptions {
  scope?: MemorySelector;
  topK?: number;
}

export type ServiceErrorType = "permission_denied" | "not_found";

export interface ServiceErrorContract {
  type: ServiceErrorType;
  operation: AuditOperation;
  caller: string;
  affected_event_ids: string[];
  event_id: string | null;
  selector: Record<string, unknown> | null;
  denial_reason: string;
  message: string;
}

export interface PersonalMemoryService {
  record(event: MemoryEvent, caller: string): Promise<string>;
  search(query: string, caller: string, options?: SearchOptions): Promise<RetrievalResult[]>;
  explain(eventId: string, caller: string): Promise<MemoryExplanation>;
  correct(eventId: string, patch: Record<string, unknown>, caller: string): Promise<string>;
  delete(selector: MemorySelector, caller: string, reason: string): Promise<string[]>;
  deleteByEventId(eventId: string, caller: string, reason: string): Promise<string[]>;
  grant(caller: string, scope: PermissionScope, durationSeconds: number): Promise<PermissionGrant>;
  revoke(grantId: string): Promise<void>;
  audit(): Promise<AuditRecord[]>;
  buildContext(
    query: string,
    caller: string,
    task: Record<string, unknown>,
    budget: Record<string, number>,
    options?: BuildContextOptions,
  ): Promise<ContextBundle>;
}
