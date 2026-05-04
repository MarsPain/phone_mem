import type { AuditRecord } from "../governance/audit";
import type { PermissionGrant } from "../governance/permissions";
import type { MemoryEvent } from "../memory_core/events";

export interface TombstoneRecord {
  tombstone_id: string;
  event_id: string;
  deleted_at: string;
  reason: string;
  selector: Record<string, unknown>;
}

export interface MemoryStore {
  insertEvent(event: MemoryEvent): Promise<void>;
  getEvent(eventId: string): Promise<MemoryEvent | null>;
  listPermissionGrants(caller?: string): Promise<PermissionGrant[]>;
  listTombstones(): Promise<TombstoneRecord[]>;
  queryAuditRecords(): Promise<AuditRecord[]>;
}
