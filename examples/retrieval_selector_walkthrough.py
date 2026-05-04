from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from pprint import pprint
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    AuditOperation,
    EventType,
    MemoryLayer,
    MemorySelector,
    Modality,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService


def run_walkthrough() -> dict[str, Any]:
    now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
    service = PersonalMemoryService.in_memory(clock=lambda: now)
    try:
        service.grant(
            "daily_agent",
            PermissionScope(
                operations=[
                    AuditOperation.WRITE,
                    AuditOperation.READ,
                    AuditOperation.DELETE,
                ],
                apps=["system_assistant", "calendar"],
                privacy_levels=[PrivacyLevel.PERSONAL],
                memory_layers=[MemoryLayer.EPISODIC],
                entities=["planning", "travel"],
            ),
            duration_seconds=60,
        )

        assistant_planning_id = service.record(
            MemoryCandidate(
                semantic_description="User prefers morning planning sessions.",
                source_app="system_assistant",
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=Attribution.USER_STATED,
                entities=["planning"],
            ),
            caller="daily_agent",
        )
        calendar_planning_id = service.record(
            MemoryCandidate(
                semantic_description="Calendar shows morning planning block.",
                source_app="calendar",
                actor=Actor.APP,
                modality=[Modality.APP_EVENT],
                attribution=Attribution.APP_SYNCED,
                event_type=EventType.APP_ACTION,
                entities=["planning"],
            ),
            caller="daily_agent",
        )
        travel_id = service.record(
            MemoryCandidate(
                semantic_description="User prefers aisle seats for flights.",
                source_app="system_assistant",
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=Attribution.USER_STATED,
                entities=["travel"],
            ),
            caller="daily_agent",
        )

        all_planning = service.search(
            "planning",
            caller="daily_agent",
            scope=MemorySelector(entities=["planning"]),
            top_k=5,
        )
        calendar_planning = service.search(
            "planning",
            caller="daily_agent",
            scope=MemorySelector(app="system_assistant", entities=["planning"]),
            top_k=5,
        )
        app_action = service.search(
            "calendar planning",
            caller="daily_agent",
            scope=MemorySelector(memory_layers=[MemoryLayer.EPISODIC], app="calendar"),
            top_k=5,
        )
        travel = service.search(
            "flights",
            caller="daily_agent",
            scope=MemorySelector(entities=["travel"]),
            top_k=5,
        )
        deleted_travel_event_ids = service.delete(
            MemorySelector(entities=["travel"]),
            caller="daily_agent",
            reason="selector walkthrough cleanup",
        )
        post_delete_travel = service.search(
            "flights",
            caller="daily_agent",
            scope=MemorySelector(entities=["travel"]),
            top_k=5,
        )

        return {
            "all_planning_event_ids": [result.event_id for result in all_planning],
            "calendar_planning_event_ids": [
                result.event_id for result in calendar_planning
            ],
            "app_action_event_ids": [result.event_id for result in app_action],
            "travel_event_ids": [result.event_id for result in travel],
            "deleted_travel_event_ids": deleted_travel_event_ids,
            "post_delete_travel_event_ids": [
                result.event_id for result in post_delete_travel
            ],
            "created_event_ids": [
                assistant_planning_id,
                calendar_planning_id,
                travel_id,
            ],
        }
    finally:
        service.close()


if __name__ == "__main__":
    pprint(run_walkthrough())
