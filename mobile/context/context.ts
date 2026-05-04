import type { MemorySnippet } from "../retrieval/retrieval";

export interface ContextTokenBudget {
  max_tokens: number;
  safety_reserve_tokens: number;
  output_reserve_tokens: number;
  tool_reserve_tokens: number;
  available_memory_tokens: number;
  used_tokens: number;
}

export interface ContextBundle {
  task: Record<string, unknown>;
  snippets: MemorySnippet[];
  evidence_event_ids: string[];
  token_budget: ContextTokenBudget;
  omitted_memory: Record<string, string>[];
  safety_metadata: Record<string, unknown>;
}
