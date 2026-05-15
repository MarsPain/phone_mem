from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from phone_mem.phone_tools.models import Contact
from phone_mem.phone_tools.sqlite_store import SQLitePhoneToolStore


class SQLitePhoneToolStoreTest(unittest.TestCase):
    def test_persists_contacts_events_and_drafts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "phone.sqlite3"
            store = SQLitePhoneToolStore.connect(str(db_path))
            store.initialize_schema()
            store.add_contact(
                Contact(
                    contact_id="contact-alice",
                    display_name="Alice Chen",
                    aliases=["Alice"],
                    phones=[],
                    emails=["alice@example.com"],
                    company="Atlas",
                    relationship="friend",
                    notes="",
                )
            )
            event = store.create_calendar_event(
                title="Planning",
                start_at=datetime(2026, 5, 15, 15, 0, tzinfo=UTC),
                end_at=datetime(2026, 5, 15, 16, 0, tzinfo=UTC),
                participant_contact_ids=["contact-alice"],
                location="Office",
                notes="",
            )
            draft = store.draft_message(
                thread_id="thread-alice",
                recipient_contact_ids=["contact-alice"],
                text="Friday works.",
                created_at=datetime(2026, 5, 14, 9, 0, tzinfo=UTC),
            )
            store.close()

            reopened = SQLitePhoneToolStore.connect(str(db_path))
            reopened.initialize_schema()
            self.addCleanup(reopened.close)

            self.assertEqual(reopened.get_contact("contact-alice").display_name, "Alice Chen")
            self.assertEqual(reopened.get_calendar_event(event.event_id).title, "Planning")
            self.assertEqual(reopened.list_message_drafts()[0].draft_id, draft.draft_id)


if __name__ == "__main__":
    unittest.main()
