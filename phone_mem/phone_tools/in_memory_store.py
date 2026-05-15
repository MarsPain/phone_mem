from __future__ import annotations

from datetime import datetime
from typing import Any

from phone_mem.phone_tools.models import (
    CalendarEvent,
    Contact,
    Message,
    MessageDraft,
    MessageThread,
)


class InMemoryPhoneToolStore:
    def __init__(self) -> None:
        self._contacts: dict[str, Contact] = {}
        self._calendar_events: dict[str, CalendarEvent] = {}
        self._message_threads: dict[str, MessageThread] = {}
        self._message_drafts: dict[str, MessageDraft] = {}
        self._next_cal_id: int = 1
        self._next_draft_id: int = 1

    def add_contact(self, contact: Contact) -> None:
        self._contacts[contact.contact_id] = contact

    def get_contact(self, contact_id: str) -> Contact | None:
        return self._contacts.get(contact_id)

    def search_contacts(self, query: str) -> list[Contact]:
        lower = query.lower()
        results: list[Contact] = []
        for contact in self._contacts.values():
            if lower in contact.display_name.lower():
                results.append(contact)
                continue
            for alias in contact.aliases:
                if lower in alias.lower():
                    results.append(contact)
                    break
        return results

    def add_calendar_event(self, event: CalendarEvent) -> None:
        self._calendar_events[event.event_id] = event

    def get_calendar_event(self, event_id: str) -> CalendarEvent | None:
        return self._calendar_events.get(event_id)

    def search_calendar(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        keyword: str | None = None,
    ) -> list[CalendarEvent]:
        results: list[CalendarEvent] = []
        for event in self._calendar_events.values():
            if start_at is not None and event.start_at < start_at:
                continue
            if end_at is not None and event.end_at > end_at:
                continue
            if keyword is not None:
                lower = keyword.lower()
                if lower not in event.title.lower() and lower not in event.notes.lower():
                    continue
            results.append(event)
        return results

    def create_calendar_event(
        self,
        *,
        title: str,
        start_at: datetime,
        end_at: datetime,
        participant_contact_ids: list[str] | None = None,
        location: str = "",
        notes: str = "",
    ) -> CalendarEvent:
        event_id = f"cal-{self._next_cal_id}"
        self._next_cal_id += 1
        event = CalendarEvent(
            event_id=event_id,
            title=title,
            start_at=start_at,
            end_at=end_at,
            participant_contact_ids=list(participant_contact_ids or []),
            location=location,
            notes=notes,
            created_by_tool=True,
        )
        self._calendar_events[event_id] = event
        return event

    def add_message_thread(self, thread: MessageThread) -> None:
        self._message_threads[thread.thread_id] = thread

    def get_message_thread(self, thread_id: str) -> MessageThread | None:
        return self._message_threads.get(thread_id)

    def search_messages(
        self,
        *,
        keyword: str | None = None,
        contact_id: str | None = None,
    ) -> list[Message]:
        results: list[Message] = []
        for thread in self._message_threads.values():
            for message in thread.messages:
                if contact_id is not None and message.sender_contact_id != contact_id:
                    continue
                if keyword is not None:
                    lower = keyword.lower()
                    if lower not in message.text.lower():
                        continue
                results.append(message)
        return results

    def draft_message(
        self,
        *,
        thread_id: str,
        recipient_contact_ids: list[str],
        text: str,
        created_at: datetime | None = None,
    ) -> MessageDraft:
        draft_id = f"draft-{self._next_draft_id}"
        self._next_draft_id += 1
        draft = MessageDraft(
            draft_id=draft_id,
            thread_id=thread_id,
            recipient_contact_ids=list(recipient_contact_ids),
            text=text,
            created_at=created_at,
        )
        self._message_drafts[draft_id] = draft
        return draft

    def list_message_drafts(self) -> list[MessageDraft]:
        return list(self._message_drafts.values())
