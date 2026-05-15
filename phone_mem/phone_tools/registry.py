from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from phone_mem.phone_tools.models import CalendarEvent, Contact, MessageDraft, MessageThread
from phone_mem.phone_tools.observations import ToolObservation
from phone_mem.phone_tools.store import PhoneToolStore
from phone_mem.tool_schema import ToolDefinition


def _object_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _parse_iso(value: str) -> datetime:
    # Python 3.11+ supports fromisoformat with Z suffix, but we normalize anyway.
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid ISO datetime: {value}") from exc


def _required_str(arguments: dict[str, Any], name: str) -> str:
    value = arguments.get(name)
    if value is None:
        raise ValueError(f"{name} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("expected a list of strings")
    return [str(item) for item in value]


@dataclass(frozen=True)
class PhoneToolResult:
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    observation: ToolObservation


class PhoneToolRegistry:
    def __init__(self, store: PhoneToolStore) -> None:
        self._store = store

    def tool_definitions(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="search_contacts",
                description="Search contacts by name or alias.",
                parameters=_object_schema(
                    {
                        "query": {"type": "string"},
                    },
                    ["query"],
                ),
            ),
            ToolDefinition(
                name="get_contact",
                description="Get a single contact by its contact_id.",
                parameters=_object_schema(
                    {
                        "contact_id": {"type": "string"},
                    },
                    ["contact_id"],
                ),
            ),
            ToolDefinition(
                name="search_calendar",
                description="Search calendar events by keyword or date range.",
                parameters=_object_schema(
                    {
                        "keyword": {"type": "string"},
                        "start_at": {"type": "string"},
                        "end_at": {"type": "string"},
                    },
                    [],
                ),
            ),
            ToolDefinition(
                name="create_calendar_event",
                description="Create a new calendar event.",
                parameters=_object_schema(
                    {
                        "title": {"type": "string"},
                        "start_at": {"type": "string"},
                        "end_at": {"type": "string"},
                        "participant_contact_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "location": {"type": "string"},
                        "notes": {"type": "string"},
                    },
                    ["title", "start_at", "end_at"],
                ),
            ),
            ToolDefinition(
                name="search_messages",
                description="Search messages by keyword or sender contact_id.",
                parameters=_object_schema(
                    {
                        "keyword": {"type": "string"},
                        "contact_id": {"type": "string"},
                    },
                    [],
                ),
            ),
            ToolDefinition(
                name="get_message_thread",
                description="Get a message thread by its thread_id.",
                parameters=_object_schema(
                    {
                        "thread_id": {"type": "string"},
                    },
                    ["thread_id"],
                ),
            ),
            ToolDefinition(
                name="draft_message",
                description="Draft a new message in a thread.",
                parameters=_object_schema(
                    {
                        "thread_id": {"type": "string"},
                        "recipient_contact_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "text": {"type": "string"},
                    },
                    ["thread_id", "recipient_contact_ids", "text"],
                ),
            ),
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> PhoneToolResult:
        if name == "search_contacts":
            return self._search_contacts(arguments)
        if name == "get_contact":
            return self._get_contact(arguments)
        if name == "search_calendar":
            return self._search_calendar(arguments)
        if name == "create_calendar_event":
            return self._create_calendar_event(arguments)
        if name == "search_messages":
            return self._search_messages(arguments)
        if name == "get_message_thread":
            return self._get_message_thread(arguments)
        if name == "draft_message":
            return self._draft_message(arguments)
        raise ValueError(f"unknown phone tool: {name}")

    def _search_contacts(self, arguments: dict[str, Any]) -> PhoneToolResult:
        query = str(arguments.get("query", ""))
        contacts = self._store.search_contacts(query)
        result = {"contacts": [contact.to_dict() for contact in contacts]}
        observation = ToolObservation(
            tool_name="search_contacts",
            text=f"Searched contacts for '{query}' and found {len(contacts)} result(s).",
            capture_worthy=False,
        )
        return PhoneToolResult(name="search_contacts", arguments=arguments, result=result, observation=observation)

    def _get_contact(self, arguments: dict[str, Any]) -> PhoneToolResult:
        contact_id = str(arguments.get("contact_id", ""))
        contact = self._store.get_contact(contact_id)
        result: dict[str, Any]
        if contact is None:
            result = {"contact": None, "error": f"Contact not found: {contact_id}"}
        else:
            result = {"contact": contact.to_dict()}
        observation = ToolObservation(
            tool_name="get_contact",
            text=f"Retrieved contact {contact_id}." if contact else f"Contact {contact_id} not found.",
            capture_worthy=False,
        )
        return PhoneToolResult(name="get_contact", arguments=arguments, result=result, observation=observation)

    def _search_calendar(self, arguments: dict[str, Any]) -> PhoneToolResult:
        keyword = arguments.get("keyword")
        start_at_str = arguments.get("start_at")
        end_at_str = arguments.get("end_at")
        start_at = _parse_iso(start_at_str) if start_at_str else None
        end_at = _parse_iso(end_at_str) if end_at_str else None
        keyword_str = str(keyword) if keyword else None
        events = self._store.search_calendar(
            start_at=start_at,
            end_at=end_at,
            keyword=keyword_str,
        )
        result = {"events": [event.to_dict() for event in events]}
        observation = ToolObservation(
            tool_name="search_calendar",
            text=f"Searched calendar and found {len(events)} event(s).",
            capture_worthy=False,
        )
        return PhoneToolResult(name="search_calendar", arguments=arguments, result=result, observation=observation)

    def _create_calendar_event(self, arguments: dict[str, Any]) -> PhoneToolResult:
        title = _required_str(arguments, "title")
        start_at = _parse_iso(_required_str(arguments, "start_at"))
        end_at = _parse_iso(_required_str(arguments, "end_at"))
        if end_at <= start_at:
            raise ValueError("end_at must be after start_at")
        participant_contact_ids = _string_list(arguments.get("participant_contact_ids", []))
        self._require_contacts(participant_contact_ids, label="Participant")
        location = str(arguments.get("location", ""))
        notes = str(arguments.get("notes", ""))
        event = self._store.create_calendar_event(
            title=title,
            start_at=start_at,
            end_at=end_at,
            participant_contact_ids=participant_contact_ids,
            location=location,
            notes=notes,
        )
        result = {"event": event.to_dict()}
        observation = ToolObservation(
            tool_name="create_calendar_event",
            text=f"Agent created a calendar event '{title}' from {event.start_at.isoformat()} to {event.end_at.isoformat()}.",
            capture_worthy=True,
        )
        return PhoneToolResult(
            name="create_calendar_event",
            arguments=arguments,
            result=result,
            observation=observation,
        )

    def _search_messages(self, arguments: dict[str, Any]) -> PhoneToolResult:
        keyword = arguments.get("keyword")
        contact_id = arguments.get("contact_id")
        keyword_str = str(keyword) if keyword else None
        contact_id_str = str(contact_id) if contact_id else None
        messages = self._store.search_messages(
            keyword=keyword_str,
            contact_id=contact_id_str,
        )
        result = {"messages": [message.to_dict() for message in messages]}
        observation = ToolObservation(
            tool_name="search_messages",
            text=f"Searched messages and found {len(messages)} message(s).",
            capture_worthy=False,
        )
        return PhoneToolResult(name="search_messages", arguments=arguments, result=result, observation=observation)

    def _get_message_thread(self, arguments: dict[str, Any]) -> PhoneToolResult:
        thread_id = str(arguments.get("thread_id", ""))
        thread = self._store.get_message_thread(thread_id)
        result: dict[str, Any]
        if thread is None:
            result = {"thread": None, "error": f"Thread not found: {thread_id}"}
        else:
            result = {"thread": thread.to_dict()}
        observation = ToolObservation(
            tool_name="get_message_thread",
            text=f"Retrieved message thread {thread_id}." if thread else f"Thread {thread_id} not found.",
            capture_worthy=False,
        )
        return PhoneToolResult(
            name="get_message_thread",
            arguments=arguments,
            result=result,
            observation=observation,
        )

    def _draft_message(self, arguments: dict[str, Any]) -> PhoneToolResult:
        thread_id = _required_str(arguments, "thread_id")
        if self._store.get_message_thread(thread_id) is None:
            raise ValueError(f"Thread not found: {thread_id}")
        recipient_contact_ids = _string_list(arguments.get("recipient_contact_ids", []))
        if not recipient_contact_ids:
            raise ValueError("recipient_contact_ids is required")
        self._require_contacts(recipient_contact_ids, label="Recipient")
        text = _required_str(arguments, "text")
        draft = self._store.draft_message(
            thread_id=thread_id,
            recipient_contact_ids=recipient_contact_ids,
            text=text,
        )
        result = {"draft": draft.to_dict()}
        observation = ToolObservation(
            tool_name="draft_message",
            text=f"Agent drafted a message to {', '.join(recipient_contact_ids)}: '{text}'.",
            capture_worthy=True,
        )
        return PhoneToolResult(name="draft_message", arguments=arguments, result=result, observation=observation)

    def _require_contacts(self, contact_ids: list[str], *, label: str) -> None:
        for contact_id in contact_ids:
            if contact_id == "self":
                continue
            if self._store.get_contact(contact_id) is None:
                raise ValueError(f"{label} not found: {contact_id}")
