import type { AuditOperation } from "./permissions";

export interface AuditRecord {
  operation_id: string;
  caller: string;
  operation: AuditOperation;
  scope: Record<string, unknown>;
  affected_event_ids: string[];
  occurred_at: string;
  outcome: "allowed" | "denied";
  denial_reason: string | null;
}
