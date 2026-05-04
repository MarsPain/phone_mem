from __future__ import annotations

from datetime import UTC, datetime
from pprint import pprint
from typing import Any

from phone_mem.context.budgets import ContextBudget
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    AuditOperation,
    MemoryLayer,
    Modality,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService


def run_walkthrough() -> dict[str, Any]:
    now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
    service = PersonalMemoryService.in_memory(clock=lambda: now)
    try:
        service.grant(
            "calendar_agent",
            PermissionScope(
                operations=[
                    AuditOperation.WRITE,
                    AuditOperation.READ,
                    AuditOperation.DELETE,
                    AuditOperation.CONTEXT_BUILD,
                ],
                apps=["system_assistant"],
                privacy_levels=[PrivacyLevel.PERSONAL],
                memory_layers=[MemoryLayer.EPISODIC],
            ),
            duration_seconds=60,
        )

        event_id = service.record(
            MemoryCandidate(
                semantic_description="User prefers morning planning sessions.",
                source_app="system_assistant",
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=Attribution.USER_STATED,
                entities=["planning"],
            ),
            caller="calendar_agent",
        )
        search_results = service.search("morning planning", caller="calendar_agent", top_k=3)
        context_bundle = service.build_context(
            "morning planning",
            caller="calendar_agent",
            task={"id": "task-1", "description": "Plan tomorrow morning."},
            budget=ContextBudget(max_tokens=80, safety_reserve_tokens=10, output_reserve_tokens=20),
            top_k=3,
        )
        deleted_event_ids = service.delete_by_event_id(
            event_id,
            caller="calendar_agent",
            reason="user requested deletion",
        )
        post_delete_search = service.search(
            "morning planning",
            caller="calendar_agent",
            top_k=3,
        )

        return {
            "event_id": event_id,
            "search_event_ids": [result.event_id for result in search_results],
            "context_evidence_event_ids": context_bundle.evidence_event_ids,
            "deleted_event_ids": deleted_event_ids,
            "post_delete_search_event_ids": [result.event_id for result in post_delete_search],
            "audit_record_count": len(service.audit()),
            "metrics": service.metrics_snapshot(),
        }
    finally:
        service.close()


if __name__ == "__main__":
    pprint(run_walkthrough())
