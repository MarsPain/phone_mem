from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.phone_tools.in_memory_store import InMemoryPhoneToolStore
from phone_mem.phone_tools.seed import seed_research_phone_state


class InMemoryPhoneToolStoreTest(unittest.TestCase):
    def test_seeded_contacts_calendar_and_messages_are_searchable(self) -> None:
        store = InMemoryPhoneToolStore()
        seed_research_phone_state(store)

        self.assertEqual(store.search_contacts("alice")[0].display_name, "Alice Chen")
        self.assertTrue(store.search_calendar(keyword="dentist"))
        self.assertTrue(store.search_messages(keyword="dinner"))

    def test_create_calendar_event_persists_event(self) -> None:
        store = InMemoryPhoneToolStore()
        event = store.create_calendar_event(
            title="Review mock phone tools",
            start_at=datetime(2026, 5, 15, 15, 0, tzinfo=UTC),
            end_at=datetime(2026, 5, 15, 16, 0, tzinfo=UTC),
            participant_contact_ids=["contact-alice"],
            location="Office",
            notes="Discuss tool capture policy.",
        )

        self.assertTrue(event.event_id.startswith("cal-"))
        self.assertEqual(store.get_calendar_event(event.event_id).title, "Review mock phone tools")

    def test_draft_message_persists_draft(self) -> None:
        store = InMemoryPhoneToolStore()
        draft = store.draft_message(
            thread_id="thread-alice",
            recipient_contact_ids=["contact-alice"],
            text="Friday afternoon works.",
            created_at=datetime(2026, 5, 14, 9, 0, tzinfo=UTC),
        )

        self.assertTrue(draft.draft_id.startswith("draft-"))
        self.assertEqual(store.list_message_drafts()[0].text, "Friday afternoon works.")


if __name__ == "__main__":
    unittest.main()
