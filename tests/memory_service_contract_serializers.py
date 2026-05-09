from __future__ import annotations


def retrieval_result_to_dict(result: object) -> dict[str, object]:
    return {
        "event_id": result.event_id,
        "score": _stable_retrieval_score(result),
        "snippet": snippet_to_dict(result.snippet),
        "explanation": _stable_retrieval_explanation(result.explanation),
    }


def context_bundle_to_dict(bundle: object) -> dict[str, object]:
    return {
        "task": bundle.task,
        "snippets": [snippet_to_dict(snippet) for snippet in bundle.snippets],
        "hot_memory_capsules": [
            hot_memory_capsule_to_dict(capsule)
            for capsule in bundle.hot_memory_capsules
        ],
        "relation_paths": [
            {
                "nodes": path.nodes,
                "edge_types": path.edge_types,
                "evidence_event_ids": path.evidence_event_ids,
                "compression_score": path.compression_score,
            }
            for path in bundle.relation_paths
        ],
        "evidence_event_ids": bundle.evidence_event_ids,
        "token_budget": {
            "max_tokens": bundle.token_budget.max_tokens,
            "safety_reserve_tokens": bundle.token_budget.safety_reserve_tokens,
            "output_reserve_tokens": bundle.token_budget.output_reserve_tokens,
            "tool_reserve_tokens": bundle.token_budget.tool_reserve_tokens,
            "available_memory_tokens": bundle.token_budget.available_memory_tokens,
            "used_tokens": bundle.token_budget.used_tokens,
        },
        "omitted_memory": bundle.omitted_memory,
        "safety_metadata": _stable_context_safety_metadata(bundle.safety_metadata),
    }


def service_error_to_dict(error_type: str, error: object) -> dict[str, object]:
    return {
        "type": error_type,
        "operation": error.operation.value,
        "caller": error.caller,
        "affected_event_ids": error.affected_event_ids,
        "event_id": getattr(error, "event_id", None),
        "selector": getattr(error, "selector", None),
        "denial_reason": error.denial_reason,
        "message": str(error),
    }


def snippet_to_dict(snippet: object) -> dict[str, object]:
    return {
        "event_id": snippet.event_id,
        "text": snippet.text,
        "source_app": snippet.source_app,
        "attribution": snippet.attribution,
        "confidence": snippet.confidence,
        "memory_layer": snippet.memory_layer,
        "privacy_level": snippet.privacy_level,
        "evidence_event_ids": snippet.evidence_event_ids,
    }


def hot_memory_capsule_to_dict(capsule: object) -> dict[str, object]:
    return {
        "category": capsule.category,
        "text": capsule.text,
        "evidence_event_ids": capsule.evidence_event_ids,
        "confidence": capsule.confidence,
        "attribution": capsule.attribution,
        "lifecycle_state": capsule.lifecycle_state,
        "omitted_memory": capsule.omitted_memory,
    }


def _stable_context_safety_metadata(safety_metadata: dict[str, object]) -> dict[str, object]:
    return {
        key: safety_metadata[key]
        for key in [
            "memory_is_data_not_instruction",
            "runtime_neutral",
            "capsule_budget",
            "relation_projection",
        ]
        if key in safety_metadata
    }


def _stable_retrieval_score(result: object) -> float:
    components = result.explanation.get("score_components")
    if not components:
        return result.score
    return round(
        components["lexical"] * 10.0
        + components["entity"] * 3.0
        + components["confidence"] * 2.0
        + components["importance"] * 2.0
        + components["recency"],
        6,
    )


def _stable_retrieval_explanation(explanation: dict[str, object]) -> dict[str, object]:
    return {
        key: explanation[key]
        for key in [
            "expanded_terms",
            "lexical_score",
            "matched_entities",
            "matched_terms",
            "recency_score",
        ]
        if key in explanation
    }
