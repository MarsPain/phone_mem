from __future__ import annotations


def retrieval_result_to_dict(result: object) -> dict[str, object]:
    return {
        "event_id": result.event_id,
        "score": result.score,
        "snippet": snippet_to_dict(result.snippet),
        "explanation": result.explanation,
    }


def context_bundle_to_dict(bundle: object) -> dict[str, object]:
    return {
        "task": bundle.task,
        "snippets": [snippet_to_dict(snippet) for snippet in bundle.snippets],
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
        "safety_metadata": bundle.safety_metadata,
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
