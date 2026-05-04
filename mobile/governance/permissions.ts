import type { MemoryLayer, PrivacyLevel, ProcessingPolicy } from "../memory_core/events";

export type AuditOperation =
  | "read"
  | "write"
  | "update"
  | "delete"
  | "grant"
  | "revoke"
  | "projection"
  | "context_build";

export interface PermissionScope {
  operations?: AuditOperation[];
  memory_layers?: MemoryLayer[];
  privacy_levels?: PrivacyLevel[];
  apps?: string[];
  entities?: string[];
  time_start?: string;
  time_end?: string;
  processing_policies?: ProcessingPolicy[];
}

export interface PermissionGrant {
  grant_id: string;
  caller: string;
  scope: PermissionScope;
  granted_at: string;
  expires_at: string;
  revoked_at: string | null;
}
