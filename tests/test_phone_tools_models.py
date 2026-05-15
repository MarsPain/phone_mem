from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.phone_tools.models import CalendarEvent, Contact, Message, MessageDraft, MessageThread
from phone_mem.phone_tools.observations import ToolObservation


class PhoneToolModelsTest(unittest.TestCase):
    def test_contact_serializes_stable_fields(self) -> None:
        contact = Contact(
            contact_id="contact-1",
            display_name="Alice Chen",
            aliases=["Alice"],
            phones=["+1-555-0100"],
            emails=["alice@example.com"],
            company="Atlas",
            relationship="dentist",
            notes="Prefers afternoon appointments.",
        )

        self.assertEqual(contact.to_dict()["display_name"], "Alice Chen")
        self.assertEqual(contact.to_dict()["aliases"], ["Alice"])
        self.assertEqual(contact.to_dict()["relationship"], "dentist")

    def test_calendar_event_serializes_iso_times(self) -> None:
        event = CalendarEvent(
            event_id="cal-1",
            title="Dentist appointment",
            start_at=datetime(2026, 5, 15, 15, 0, tzinfo=UTC),
            end_at=datetime(2026, 5, 15, 16, 0, tzinfo=UTC),
            participant_contact_ids=["contact-1"],
            location="Clinic",
            notes="Bring insurance card.",
            created_by_tool=True,
        )

        self.assertEqual(event.to_dict()["start_at"], "2026-05-15T15:00:00+00:00")
        self.assertTrue(event.to_dict()["created_by_tool"])

    def test_message_thread_and_draft_serialize(self) -> None:
        message = Message(
            message_id="msg-1",
            thread_id="thread-1",
            sender_contact_id="contact-1",
            sent_at=datetime(2026, 5, 14, 9, 0, tzinfo=UTC),
            text="Can we reschedule dinner?",
        )
        thread = MessageThread(
            thread_id="thread-1",
            participant_contact_ids=["contact-1", "self"],
            messages=[message],
        )
        draft = MessageDraft(
            draft_id="draft-1",
            thread_id="thread-1",
            recipient_contact_ids=["contact-1"],
            text="How about Friday?",
            created_at=datetime(2026, 5, 14, 9, 5, tzinfo=UTC),
        )

        self.assertEqual(thread.to_dict()["messages"][0]["text"], "Can we reschedule dinner?")
        self.assertEqual(draft.to_dict()["recipient_contact_ids"], ["contact-1"])

    def test_tool_observation_marks_capture_policy(self) -> None:
        observation = ToolObservation(
            tool_name="create_calendar_event",
            text="Agent created a calendar event with Alice.",
            capture_worthy=True,
        )

        self.assertTrue(observation.capture_worthy)
        self.assertEqual(observation.to_dict()["tool_name"], "create_calendar_event")


if __name__ == "__main__":
    unittest.main()
