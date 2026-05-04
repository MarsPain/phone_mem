from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    AuditOperation,
    LifecycleState,
    MemoryLayer,
    MemorySelector,
    Modality,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService


class PersonalMemoryServiceTest(unittest.TestCase):
    def test_record_search_explain_delete_and_audit_flow(self) -> None:
        now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        service = PersonalMemoryService.in_memory(clock=lambda: now)
        self.addCleanup(service.close)
        service.grant(
            "calendar_agent",
            PermissionScope(
                operations=[
                    AuditOperation.WRITE,
                    AuditOperation.READ,
                    AuditOperation.DELETE,
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
        results = service.search("morning planning", caller="calendar_agent")
        explanation = service.explain(event_id, caller="calendar_agent")
        deleted_event_ids = service.delete(
            MemorySelector(event_ids=[event_id]),
            caller="calendar_agent",
            reason="user requested deletion",
        )
        after_delete = service.search("morning planning", caller="calendar_agent")

        self.assertEqual([result.event_id for result in results], [event_id])
        self.assertEqual(explanation["event_id"], event_id)
        self.assertEqual(explanation["source"]["attribution"], "user_stated")
        self.assertEqual(deleted_event_ids, [event_id])
        self.assertEqual(after_delete, [])
        self.assertEqual([tombstone.event_id for tombstone in service.store.list_tombstones()], [event_id])
        audit_operations = [record.operation for record in service.audit()]
        self.assertIn(AuditOperation.GRANT, audit_operations)
        self.assertIn(AuditOperation.WRITE, audit_operations)
        self.assertIn(AuditOperation.READ, audit_operations)
        self.assertIn(AuditOperation.DELETE, audit_operations)

    def test_explain_denies_unauthorized_caller_without_leaking_event(self) -> None:
        now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        service = PersonalMemoryService.in_memory(clock=lambda: now)
        self.addCleanup(service.close)
        service.grant(
            "calendar_agent",
            PermissionScope(
                operations=[AuditOperation.WRITE, AuditOperation.READ],
                apps=["system_assistant"],
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

        with self.assertRaises(PermissionError):
            service.explain(event_id, caller="health_agent")

        denied = [
            record
            for record in service.audit()
            if record.caller == "health_agent" and record.outcome == "denied"
        ]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0].affected_event_ids, [event_id])

    def test_duplicate_record_returns_existing_event_id_without_new_row(self) -> None:
        now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        service = PersonalMemoryService.in_memory(clock=lambda: now)
        self.addCleanup(service.close)
        service.grant(
            "calendar_agent",
            PermissionScope(
                operations=[AuditOperation.WRITE],
                apps=["system_assistant"],
            ),
            duration_seconds=60,
        )
        candidate = MemoryCandidate(
            semantic_description="User prefers morning planning sessions.",
            source_app="system_assistant",
            actor=Actor.USER,
            modality=[Modality.TEXT],
            attribution=Attribution.USER_STATED,
            entities=["planning"],
        )

        first_id = service.record(candidate, caller="calendar_agent")
        second_id = service.record(candidate, caller="calendar_agent")

        self.assertEqual(second_id, first_id)
        self.assertEqual(len(service.store.query_events()), 1)

    def test_contradictory_preference_is_quarantined_not_silently_overwritten(self) -> None:
        now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        service = PersonalMemoryService.in_memory(clock=lambda: now)
        self.addCleanup(service.close)
        service.grant(
            "travel_agent",
            PermissionScope(
                operations=[AuditOperation.WRITE, AuditOperation.READ],
                apps=["system_assistant"],
                entities=["travel"],
            ),
            duration_seconds=60,
        )

        active_id = service.record(
            MemoryCandidate(
                semantic_description="User prefers aisle seats for flights.",
                source_app="system_assistant",
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=Attribution.USER_STATED,
                entities=["travel"],
            ),
            caller="travel_agent",
        )
        quarantined_id = service.record(
            MemoryCandidate(
                semantic_description="User prefers window seats for flights.",
                source_app="system_assistant",
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=Attribution.USER_STATED,
                entities=["travel"],
            ),
            caller="travel_agent",
        )

        active = service.store.get_event(active_id)
        quarantined = service.store.get_event(quarantined_id)
        self.assertIsNotNone(active)
        self.assertIsNotNone(quarantined)
        assert active is not None
        assert quarantined is not None
        self.assertEqual(active.lifecycle.state, LifecycleState.ACTIVE)
        self.assertEqual(quarantined.lifecycle.state, LifecycleState.QUARANTINED)
        result_ids = [result.event_id for result in service.search("window seats", caller="travel_agent")]
        self.assertNotIn(quarantined_id, result_ids)

    def test_correct_creates_new_event_and_supersedes_original(self) -> None:
        now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        service = PersonalMemoryService.in_memory(clock=lambda: now)
        self.addCleanup(service.close)
        service.grant(
            "calendar_agent",
            PermissionScope(
                operations=[AuditOperation.WRITE, AuditOperation.READ, AuditOperation.UPDATE],
                apps=["system_assistant"],
            ),
            duration_seconds=60,
        )
        original_id = service.record(
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

        corrected_id = service.correct(
            original_id,
            {"semantic_description": "User prefers afternoon planning sessions."},
            caller="calendar_agent",
        )

        original = service.store.get_event(original_id)
        corrected = service.store.get_event(corrected_id)
        self.assertIsNotNone(original)
        self.assertIsNotNone(corrected)
        assert original is not None
        assert corrected is not None
        self.assertNotEqual(corrected_id, original_id)
        self.assertEqual(original.lifecycle.state, LifecycleState.SUPERSEDED)
        self.assertEqual(corrected.lineage.supersedes, [original_id])
        self.assertEqual(service.search("afternoon planning", caller="calendar_agent")[0].event_id, corrected_id)


if __name__ == "__main__":
    unittest.main()
