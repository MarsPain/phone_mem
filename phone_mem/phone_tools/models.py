from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _iso(dt: datetime) -> str:
    return dt.isoformat()


@dataclass(frozen=True)
class Contact:
    contact_id: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    company: str = ""
    relationship: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "contact_id": self.contact_id,
            "display_name": self.display_name,
            "aliases": list(self.aliases),
            "phones": list(self.phones),
            "emails": list(self.emails),
            "company": self.company,
            "relationship": self.relationship,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CalendarEvent:
    event_id: str
    title: str
    start_at: datetime
    end_at: datetime
    participant_contact_ids: list[str] = field(default_factory=list)
    location: str = ""
    notes: str = ""
    created_by_tool: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "start_at": _iso(self.start_at),
            "end_at": _iso(self.end_at),
            "participant_contact_ids": list(self.participant_contact_ids),
            "location": self.location,
            "notes": self.notes,
            "created_by_tool": self.created_by_tool,
        }


@dataclass(frozen=True)
class Message:
    message_id: str
    thread_id: str
    sender_contact_id: str
    sent_at: datetime
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "sender_contact_id": self.sender_contact_id,
            "sent_at": _iso(self.sent_at),
            "text": self.text,
        }


@dataclass(frozen=True)
class MessageThread:
    thread_id: str
    participant_contact_ids: list[str] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "participant_contact_ids": list(self.participant_contact_ids),
            "messages": [message.to_dict() for message in self.messages],
        }


@dataclass(frozen=True)
class MessageDraft:
    draft_id: str
    thread_id: str
    recipient_contact_ids: list[str] = field(default_factory=list)
    text: str = ""
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "draft_id": self.draft_id,
            "thread_id": self.thread_id,
            "recipient_contact_ids": list(self.recipient_contact_ids),
            "text": self.text,
        }
        if self.created_at is not None:
            result["created_at"] = _iso(self.created_at)
        return result
