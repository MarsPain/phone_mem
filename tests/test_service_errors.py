from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.governance.audit import AuditSelector
from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.errors import (
    MemoryEventNotFound,
    MemoryPermissionDenied,
)
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    AuditOperation,
    Modality,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService


def make_candidate() -> MemoryCandidate:
    return MemoryCandidate(
        semantic_description="User prefers morning planning sessions.",
        source_app="system_assistant",
        actor=Actor.USER,
        modality=[Modality.TEXT],
        attribution=Attribution.USER_STATED,
        entities=["planning"],
    )


class PersonalMemoryServiceErrorTest(unittest.TestCase):
    def test_record_denial_raises_permission_error_with_operation_context(self) -> None:
        service = PersonalMemoryService.in_memory(
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        )
        self.addCleanup(service.close)

        with self.assertRaises(MemoryPermissionDenied) as raised:
            service.record(make_candidate(), caller="calendar_agent")

        error = raised.exception
        self.assertIsInstance(error, PermissionError)
        self.assertEqual(error.operation, AuditOperation.WRITE)
        self.assertEqual(error.caller, "calendar_agent")
        self.assertEqual(error.affected_event_ids, ["event-1"])
        self.assertEqual(error.denial_reason, "no active grant matched")
        self.assertEqual(
            str(error),
            "write denied for calendar_agent: no active grant matched",
        )

        denied_records = service.audit(AuditSelector(caller="calendar_agent"))
        self.assertEqual(len(denied_records), 1)
        self.assertEqual(denied_records[0].operation, AuditOperation.WRITE)
        self.assertEqual(denied_records[0].outcome, "denied")
        self.assertEqual(denied_records[0].denial_reason, "no active grant matched")

    def test_explain_missing_event_raises_not_found_error_and_audits_denial(self) -> None:
        service = PersonalMemoryService.in_memory(
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        )
        self.addCleanup(service.close)

        with self.assertRaises(MemoryEventNotFound) as raised:
            service.explain("missing-event", caller="calendar_agent")

        error = raised.exception
        self.assertIsInstance(error, KeyError)
        self.assertEqual(error.operation, AuditOperation.READ)
        self.assertEqual(error.caller, "calendar_agent")
        self.assertEqual(error.event_id, "missing-event")
        self.assertEqual(str(error), "read failed for calendar_agent: memory event not found")

        denied_records = service.audit(AuditSelector(caller="calendar_agent"))
        self.assertEqual(len(denied_records), 1)
        self.assertEqual(denied_records[0].operation, AuditOperation.READ)
        self.assertEqual(denied_records[0].affected_event_ids, ["missing-event"])
        self.assertEqual(denied_records[0].outcome, "denied")
        self.assertEqual(denied_records[0].denial_reason, "memory event not found")


if __name__ == "__main__":
    unittest.main()
