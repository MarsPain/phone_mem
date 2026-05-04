from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.governance.audit import AuditSelector
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    AuditOperation,
    LifecycleState,
    Modality,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService


def make_candidate(description: str, *, entity: str) -> MemoryCandidate:
    return MemoryCandidate(
        semantic_description=description,
        source_app="system_assistant",
        actor=Actor.USER,
        modality=[Modality.TEXT],
        attribution=Attribution.USER_STATED,
        entities=[entity],
    )


class LifecycleExplainabilityTest(unittest.TestCase):
    def test_rejected_write_does_not_persist_event_and_audits_denial(self) -> None:
        service = PersonalMemoryService.in_memory(
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        )
        self.addCleanup(service.close)

        with self.assertRaises(PermissionError):
            service.record(
                make_candidate("User prefers morning planning sessions.", entity="planning"),
                caller="calendar_agent",
            )

        self.assertEqual(service.store.query_events(), [])
        denied_records = service.audit(AuditSelector(caller="calendar_agent"))
        self.assertEqual(len(denied_records), 1)
        self.assertEqual(denied_records[0].operation, AuditOperation.WRITE)
        self.assertEqual(denied_records[0].outcome, "denied")

    def test_quarantined_memory_explains_contradiction_parent(self) -> None:
        service = PersonalMemoryService.in_memory(
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        )
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
            make_candidate("User prefers aisle seats for flights.", entity="travel"),
            caller="travel_agent",
        )
        quarantined_id = service.record(
            make_candidate("User prefers window seats for flights.", entity="travel"),
            caller="travel_agent",
        )

        explanation = service.explain(quarantined_id, caller="travel_agent")

        self.assertEqual(explanation["lifecycle"]["state"], LifecycleState.QUARANTINED.value)
        self.assertEqual(
            explanation["lifecycle_explanation"],
            {
                "state": "quarantined",
                "reason": "contradicts active memory",
                "related_event_ids": [active_id],
            },
        )

    def test_correction_explains_superseded_and_corrected_events(self) -> None:
        service = PersonalMemoryService.in_memory(
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        )
        self.addCleanup(service.close)
        service.grant(
            "calendar_agent",
            PermissionScope(
                operations=[
                    AuditOperation.WRITE,
                    AuditOperation.READ,
                    AuditOperation.UPDATE,
                ],
                apps=["system_assistant"],
                entities=["planning"],
            ),
            duration_seconds=60,
        )
        original_id = service.record(
            make_candidate("User prefers morning planning sessions.", entity="planning"),
            caller="calendar_agent",
        )
        corrected_id = service.correct(
            original_id,
            {"semantic_description": "User prefers afternoon planning sessions."},
            caller="calendar_agent",
        )

        original_explanation = service.explain(original_id, caller="calendar_agent")
        corrected_explanation = service.explain(corrected_id, caller="calendar_agent")

        self.assertEqual(
            original_explanation["lifecycle_explanation"],
            {
                "state": "superseded",
                "reason": "superseded by correction",
                "related_event_ids": [corrected_id],
            },
        )
        self.assertEqual(
            corrected_explanation["lifecycle_explanation"],
            {
                "state": "active",
                "reason": "corrects previous memory",
                "related_event_ids": [original_id],
            },
        )


if __name__ == "__main__":
    unittest.main()
