export type EventType =
  | "user_utterance"
  | "app_action"
  | "visual_scene"
  | "sensor_snapshot"
  | "derived_summary"
  | "procedural_skill";

export type MemoryLayer = "working" | "episodic" | "semantic" | "procedural";
export type LifecycleState = "active" | "superseded" | "deleted" | "quarantined";
export type PrivacyLevel = "sensitive" | "personal" | "public";
export type ProcessingPolicy =
  | "device_only"
  | "client_encrypted_sync"
  | "private_compute"
  | "cloud_indexable";

export interface MemoryEvent {
  event_id: string;
  created_at: string;
  valid_time: { start: string; end: string | null };
  event_type: EventType;
  memory_layer: MemoryLayer;
  semantic_description: string;
  entities: string[];
  relations: Record<string, unknown>[];
  source: {
    app: string;
    actor: "user" | "agent" | "app" | "cloud_consolidator";
    modality: string[];
    attribution: "user_stated" | "agent_inferred" | "app_synced" | "derived";
  };
  privacy: {
    level: PrivacyLevel;
    allowed_scopes: string[];
    processing_policy: ProcessingPolicy;
  };
  quality: {
    confidence: number;
    importance: number;
    freshness_half_life_days: number;
  };
  lineage: { parents: string[]; derived_from: string[]; supersedes: string[] };
  lifecycle: { state: LifecycleState; deleted_at: string | null; delete_reason: string | null };
}

export interface MemorySelector {
  event_ids?: string[];
  app?: string;
  entities?: string[];
  topics?: string[];
  memory_layers?: MemoryLayer[];
  privacy_levels?: PrivacyLevel[];
  lifecycle_states?: LifecycleState[];
  time_start?: string;
  time_end?: string;
}

export interface LifecycleExplanation {
  state: LifecycleState;
  reason: string;
  related_event_ids: string[];
}

export interface MemoryExplanation {
  event_id: string;
  source: MemoryEvent["source"];
  memory_layer: MemoryLayer;
  privacy: MemoryEvent["privacy"];
  quality: MemoryEvent["quality"];
  lineage: MemoryEvent["lineage"];
  lifecycle: MemoryEvent["lifecycle"];
  lifecycle_explanation: LifecycleExplanation;
}
