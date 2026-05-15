from __future__ import annotations

from datetime import datetime
from typing import Protocol

from phone_mem.phone_tools.models import (
    CalendarEvent,
    Contact,
    Message,
    MessageDraft,
    MessageThread,
)


class PhoneToolStore(Protocol):
    def add_contact(self, contact: Contact) -> None: ...

    def get_contact(self, contact_id: str) -> Contact | None: ...

    def search_contacts(self, query: str) -> list[Contact]: ...

    def add_calendar_event(self, event: CalendarEvent) -> None: ...

    def get_calendar_event(self, event_id: str) -> CalendarEvent | None: ...

    def search_calendar(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        keyword: str | None = None,
    ) -> list[CalendarEvent]: ...

    def create_calendar_event(
        self,
        *,
        title: str,
        start_at: datetime,
        end_at: datetime,
        participant_contact_ids: list[str] | None = None,
        location: str = "",
        notes: str = "",
    ) -> CalendarEvent: ...

    def add_message_thread(self, thread: MessageThread) -> None: ...

    def get_message_thread(self, thread_id: str) -> MessageThread | None: ...

    def search_messages(
        self,
        *,
        keyword: str | None = None,
        contact_id: str | None = None,
    ) -> list[Message]: ...

    def draft_message(
        self,
        *,
        thread_id: str,
        recipient_contact_ids: list[str],
        text: str,
        created_at: datetime | None = None,
    ) -> MessageDraft: ...

    def list_message_threads(self) -> list[MessageThread]: ...

    def list_message_drafts(self) -> list[MessageDraft]: ...
