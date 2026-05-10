from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phone_mem.agent_runtime.client import ToolDefinition
from phone_mem.context.budgets import ContextBudget
from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    MemoryLayer,
    Modality,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService


@dataclass(frozen=True)
class MemoryToolRegistry:
    service: PersonalMemoryService
    caller: str
    source_app: str

    def search_memory(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        results = self.service.search(query, caller=self.caller, top_k=top_k)
        return {
            "query": query,
            "results": [
                {
                    "event_id": result.event_id,
                    "score": result.score,
                    "text": result.snippet.text,
                    "evidence_event_ids": list(result.snippet.evidence_event_ids),
                    "explanation": dict(result.explanation),
                }
                for result in results
            ],
        }

    def build_memory_context(self, query: str, *, max_tokens: int = 160) -> dict[str, Any]:
        bundle = self.service.build_context(
            query,
            caller=self.caller,
            task={"id": "agent-runtime-turn", "description": query},
            budget=ContextBudget(
                max_tokens=max_tokens,
                safety_reserve_tokens=10,
                output_reserve_tokens=30,
                tool_reserve_tokens=10,
            ),
            top_k=5,
        )
        return _serialize_context_bundle(query, bundle)

    def remember(
        self,
        text: str,
        *,
        entities: list[str] | None = None,
        privacy_level: str = "personal",
        memory_layer: str = "episodic",
    ) -> dict[str, str]:
        event_id = self.service.record(
            MemoryCandidate(
                semantic_description=text,
                source_app=self.source_app,
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=Attribution.USER_STATED,
                entities=list(entities or []),
                privacy_level=PrivacyLevel(privacy_level),
                memory_layer=MemoryLayer(memory_layer),
            ),
            caller=self.caller,
        )
        return {"event_id": event_id}

    def record_candidate(self, candidate: MemoryCandidate) -> dict[str, str]:
        event_id = self.service.record(candidate, caller=self.caller)
        return {"event_id": event_id}

    def explain_memory(self, event_id: str) -> dict[str, Any]:
        return self.service.explain(event_id, caller=self.caller)

    def correct_memory(self, event_id: str, replacement_text: str) -> dict[str, str]:
        corrected_id = self.service.correct(
            event_id,
            {"semantic_description": replacement_text},
            caller=self.caller,
        )
        return {"event_id": corrected_id}

    def delete_memory(self, event_id: str, *, reason: str) -> dict[str, list[str]]:
        deleted_event_ids = self.service.delete_by_event_id(
            event_id,
            caller=self.caller,
            reason=reason,
        )
        return {"deleted_event_ids": deleted_event_ids}

    def tool_definitions(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="search_memory",
                description="Search authorized memory for task-relevant snippets.",
                parameters=_object_schema(
                    {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    ["query"],
                ),
            ),
            ToolDefinition(
                name="build_memory_context",
                description="Build a token-budgeted context bundle from authorized memory.",
                parameters=_object_schema(
                    {
                        "query": {"type": "string"},
                        "max_tokens": {"type": "integer"},
                    },
                    ["query"],
                ),
            ),
            ToolDefinition(
                name="remember",
                description="Record a user-stated memory through the governed memory service with explicit classification.",
                parameters=_object_schema(
                    {
                        "text": {"type": "string"},
                        "entities": {"type": "array", "items": {"type": "string"}},
                        "privacy_level": {
                            "type": "string",
                            "enum": [level.value for level in PrivacyLevel],
                        },
                        "memory_layer": {
                            "type": "string",
                            "enum": [layer.value for layer in MemoryLayer],
                        },
                    },
                    ["text"],
                ),
            ),
            ToolDefinition(
                name="explain_memory",
                description="Explain source, lifecycle, confidence, and policy metadata for a memory.",
                parameters=_object_schema({"event_id": {"type": "string"}}, ["event_id"]),
            ),
            ToolDefinition(
                name="correct_memory",
                description="Correct an existing memory by creating a superseding event.",
                parameters=_object_schema(
                    {
                        "event_id": {"type": "string"},
                        "replacement_text": {"type": "string"},
                    },
                    ["event_id", "replacement_text"],
                ),
            ),
            ToolDefinition(
                name="delete_memory",
                description="Delete a memory through tombstoned service lifecycle operations.",
                parameters=_object_schema(
                    {
                        "event_id": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    ["event_id", "reason"],
                ),
            ),
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "search_memory":
            return self.search_memory(
                str(arguments["query"]),
                top_k=int(arguments.get("top_k", 5)),
            )
        if name == "build_memory_context":
            return self.build_memory_context(
                str(arguments["query"]),
                max_tokens=int(arguments.get("max_tokens", 160)),
            )
        if name == "remember":
            return self.remember(
                str(arguments["text"]),
                entities=list(arguments.get("entities", [])),
                privacy_level=str(arguments.get("privacy_level", "personal")),
                memory_layer=str(arguments.get("memory_layer", "episodic")),
            )
        if name == "explain_memory":
            return self.explain_memory(str(arguments["event_id"]))
        if name == "correct_memory":
            return self.correct_memory(
                str(arguments["event_id"]),
                str(arguments["replacement_text"]),
            )
        if name == "delete_memory":
            return self.delete_memory(
                str(arguments["event_id"]),
                reason=str(arguments["reason"]),
            )
        raise ValueError(f"unknown memory tool: {name}")


def _serialize_context_bundle(query: str, bundle: Any) -> dict[str, Any]:
    return {
        "query": query,
        "evidence_event_ids": list(bundle.evidence_event_ids),
        "snippets": [
            {
                "event_id": snippet.event_id,
                "text": snippet.text,
                "evidence_event_ids": list(snippet.evidence_event_ids),
            }
            for snippet in bundle.snippets
        ],
        "hot_memory_capsules": [
            {
                "category": capsule.category,
                "text": capsule.text,
                "evidence_event_ids": list(capsule.evidence_event_ids),
                "confidence": capsule.confidence,
                "attribution": capsule.attribution,
                "lifecycle_state": capsule.lifecycle_state,
                "omitted_memory": list(capsule.omitted_memory),
            }
            for capsule in bundle.hot_memory_capsules
        ],
        "relation_paths": [_serialize_relation_path(path) for path in bundle.relation_paths],
        "omitted_memory": list(bundle.omitted_memory),
        "safety_metadata": dict(bundle.safety_metadata),
        "token_budget": {
            "max_tokens": bundle.token_budget.max_tokens,
            "safety_reserve_tokens": bundle.token_budget.safety_reserve_tokens,
            "output_reserve_tokens": bundle.token_budget.output_reserve_tokens,
            "tool_reserve_tokens": bundle.token_budget.tool_reserve_tokens,
            "available_memory_tokens": bundle.token_budget.available_memory_tokens,
            "used_tokens": bundle.token_budget.used_tokens,
        },
    }


def _serialize_relation_path(path: Any) -> dict[str, Any]:
    nodes = list(path.nodes)
    relation_types = list(path.edge_types)
    return {
        "nodes": nodes,
        "relation_types": relation_types,
        "edge_types": relation_types,
        "source_label": nodes[0] if nodes else None,
        "target_label": nodes[-1] if nodes else None,
        "evidence_event_ids": list(path.evidence_event_ids),
        "compression_score": path.compression_score,
        "path_metadata": {
            "node_count": len(nodes),
            "edge_count": len(relation_types),
        },
    }


def _object_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }
