from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


CALLER = "daily_planner_agent"
SOURCE_APP = "system_assistant"


def run_demo() -> dict[str, Any]:
    now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
    service = PersonalMemoryService.in_memory(clock=lambda: now)
    transcript: list[str] = []
    try:
        transcript.append("Phone Memory Agent Demo")
        transcript.append("=" * 23)

        service.grant(CALLER, _demo_scope(), duration_seconds=3_600)
        transcript.append(
            "Permission grant: daily_planner_agent can write, read, update, delete, "
            "and build context for personal planning memories."
        )

        user_memory = "I prefer morning planning sessions."
        transcript.append(f"User says: {user_memory}")
        recorded_event_id = service.record(
            _candidate("User prefers morning planning sessions."),
            caller=CALLER,
        )
        transcript.append(
            f"Agent records: {recorded_event_id} as an episodic personal preference."
        )

        task = {"id": "task-plan-monday", "description": "Help plan Monday."}
        task_results = service.search("planning sessions", caller=CALLER, top_k=3)
        task_search_event_ids = [result.event_id for result in task_results]
        transcript.append(
            "Later task: plan Monday -> retrieved memory IDs "
            f"{task_search_event_ids}."
        )

        context_bundle = service.build_context(
            "planning sessions",
            caller=CALLER,
            task=task,
            budget=ContextBudget(
                max_tokens=100,
                safety_reserve_tokens=10,
                output_reserve_tokens=25,
            ),
            top_k=3,
        )
        context_text = (
            context_bundle.snippets[0].text if context_bundle.snippets else "no memory"
        )
        transcript.append(
            "Context bundle: the Agent sees "
            f"{context_bundle.evidence_event_ids} -> \"{context_text}\"."
        )

        transcript.append(
            "User correction: Actually, I prefer afternoon planning sessions."
        )
        corrected_event_id = service.correct(
            recorded_event_id,
            {"semantic_description": "User prefers afternoon planning sessions."},
            caller=CALLER,
        )
        post_correction_results = service.search(
            "afternoon planning",
            caller=CALLER,
            top_k=3,
        )
        post_correction_search_event_ids = [
            result.event_id for result in post_correction_results
        ]
        transcript.append(
            f"Agent updates memory: {recorded_event_id} -> {corrected_event_id}; "
            f"new search returns {post_correction_search_event_ids}."
        )

        original_explanation = service.explain(recorded_event_id, caller=CALLER)
        corrected_explanation = service.explain(corrected_event_id, caller=CALLER)
        original_lifecycle_reason = str(
            original_explanation["lifecycle_explanation"]["reason"]
        )
        corrected_lifecycle_reason = str(
            corrected_explanation["lifecycle_explanation"]["reason"]
        )
        transcript.append(
            "Lifecycle explanation: original is "
            f"'{original_lifecycle_reason}', corrected memory is "
            f"'{corrected_lifecycle_reason}'."
        )

        transcript.append("User deletes: remove that planning preference.")
        deleted_event_ids = service.delete_by_event_id(
            corrected_event_id,
            caller=CALLER,
            reason="user requested deletion in product demo",
        )
        post_delete_results = service.search("afternoon planning", caller=CALLER, top_k=3)
        post_delete_search_event_ids = [result.event_id for result in post_delete_results]
        transcript.append(
            f"Agent deletes: {deleted_event_ids}; later retrieval returns "
            f"{post_delete_search_event_ids}."
        )

        metrics = service.metrics_snapshot()
        transcript.append(
            "Audit and metrics: "
            f"{len(service.audit())} audit records, "
            f"{metrics['deletion']['tombstone_count']} tombstone."
        )

        return {
            "recorded_event_id": recorded_event_id,
            "corrected_event_id": corrected_event_id,
            "task_search_event_ids": task_search_event_ids,
            "context_evidence_event_ids": context_bundle.evidence_event_ids,
            "post_correction_search_event_ids": post_correction_search_event_ids,
            "deleted_event_ids": deleted_event_ids,
            "post_delete_search_event_ids": post_delete_search_event_ids,
            "original_lifecycle_reason": original_lifecycle_reason,
            "corrected_lifecycle_reason": corrected_lifecycle_reason,
            "audit_record_count": len(service.audit()),
            "metrics": metrics,
            "transcript": transcript,
        }
    finally:
        service.close()


def _demo_scope() -> PermissionScope:
    return PermissionScope(
        operations=[
            AuditOperation.WRITE,
            AuditOperation.READ,
            AuditOperation.UPDATE,
            AuditOperation.DELETE,
            AuditOperation.CONTEXT_BUILD,
        ],
        apps=[SOURCE_APP],
        privacy_levels=[PrivacyLevel.PERSONAL],
        memory_layers=[MemoryLayer.EPISODIC],
        entities=["planning"],
    )


def _candidate(description: str) -> MemoryCandidate:
    return MemoryCandidate(
        semantic_description=description,
        source_app=SOURCE_APP,
        actor=Actor.USER,
        modality=[Modality.TEXT],
        attribution=Attribution.USER_STATED,
        entities=["planning"],
    )


if __name__ == "__main__":
    for line in run_demo()["transcript"]:
        print(line)
