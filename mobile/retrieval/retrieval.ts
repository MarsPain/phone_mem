export interface MemorySnippet {
  event_id: string;
  text: string;
  source_app: string;
  attribution: string;
  confidence: number;
  memory_layer: string;
  privacy_level: string;
  evidence_event_ids: string[];
}

export interface RetrievalResult {
  event_id: string;
  score: number;
  snippet: MemorySnippet;
  explanation: Record<string, unknown>;
}
