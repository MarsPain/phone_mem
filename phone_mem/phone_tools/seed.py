from __future__ import annotations

from datetime import UTC, datetime

from phone_mem.phone_tools.models import CalendarEvent, Contact, Message, MessageThread
from phone_mem.phone_tools.store import PhoneToolStore


def seed_research_phone_state(store: PhoneToolStore) -> None:
    """Insert deterministic fixture data for local research harness."""
    store.add_contact(
        Contact(
            contact_id="contact-alice",
            display_name="Alice Chen",
            aliases=["Alice"],
            phones=["+1-555-0100"],
            emails=["alice@example.com"],
            company="Atlas",
            relationship="friend",
            notes="Prefers afternoon appointments.",
        )
    )

    store.add_calendar_event(
        CalendarEvent(
            event_id="cal-dentist-1",
            title="Dentist appointment",
            start_at=datetime(2026, 5, 15, 15, 0, tzinfo=UTC),
            end_at=datetime(2026, 5, 15, 16, 0, tzinfo=UTC),
            participant_contact_ids=["contact-alice"],
            location="Downtown Dental Clinic",
            notes="Regular checkup.",
            created_by_tool=False,
        )
    )

    store.add_message_thread(
        MessageThread(
            thread_id="thread-dinner-1",
            participant_contact_ids=["contact-alice", "self"],
            messages=[
                Message(
                    message_id="msg-dinner-1",
                    thread_id="thread-dinner-1",
                    sender_contact_id="contact-alice",
                    sent_at=datetime(2026, 5, 14, 18, 30, tzinfo=UTC),
                    text="Can we reschedule dinner to Friday?",
                )
            ],
        )
    )
