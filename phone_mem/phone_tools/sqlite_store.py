from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from phone_mem.phone_tools.models import (
    CalendarEvent,
    Contact,
    Message,
    MessageDraft,
    MessageThread,
)


class SQLitePhoneToolStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._next_cal_id: int = 1
        self._next_draft_id: int = 1

    @classmethod
    def connect(cls, path: str) -> SQLitePhoneToolStore:
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return cls(conn)

    def initialize_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS phone_contacts (
                contact_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                aliases TEXT,
                phones TEXT,
                emails TEXT,
                company TEXT,
                relationship TEXT,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS phone_calendar_events (
                event_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                participant_contact_ids TEXT,
                location TEXT,
                notes TEXT,
                created_by_tool INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS phone_message_threads (
                thread_id TEXT PRIMARY KEY,
                participant_contact_ids TEXT
            );

            CREATE TABLE IF NOT EXISTS phone_messages (
                message_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                sender_contact_id TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                text TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS phone_message_drafts (
                draft_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                recipient_contact_ids TEXT,
                text TEXT NOT NULL,
                created_at TEXT
            );
            """
        )
        self._conn.commit()
        self._load_next_ids()

    def close(self) -> None:
        self._conn.close()

    def _load_next_ids(self) -> None:
        self._next_cal_id = self._max_numeric_id("phone_calendar_events", "event_id", "cal-") + 1
        self._next_draft_id = self._max_numeric_id("phone_message_drafts", "draft_id", "draft-") + 1

    def _max_numeric_id(self, table: str, id_column: str, prefix: str) -> int:
        rows = self._conn.execute(
            f"SELECT {id_column} FROM {table} WHERE {id_column} LIKE ?",
            (prefix + "%",),
        ).fetchall()
        max_id = 0
        prefix_len = len(prefix)
        for (value,) in rows:
            try:
                num = int(value[prefix_len:])
                max_id = max(max_id, num)
            except (ValueError, IndexError):
                pass
        return max_id

    def _to_json(self, value: list[Any]) -> str:
        return json.dumps(value, sort_keys=True)

    def _from_json(self, value: str | None) -> list[Any]:
        if value is None or value == "":
            return []
        return json.loads(value)

    def _iso(self, dt: datetime) -> str:
        return dt.isoformat()

    def _parse_iso(self, value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)

    # Contacts

    def add_contact(self, contact: Contact) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO phone_contacts
            (contact_id, display_name, aliases, phones, emails, company, relationship, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contact.contact_id,
                contact.display_name,
                self._to_json(contact.aliases),
                self._to_json(contact.phones),
                self._to_json(contact.emails),
                contact.company,
                contact.relationship,
                contact.notes,
            ),
        )
        self._conn.commit()

    def get_contact(self, contact_id: str) -> Contact | None:
        row = self._conn.execute(
            "SELECT * FROM phone_contacts WHERE contact_id = ?",
            (contact_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_contact(row)

    def search_contacts(self, query: str) -> list[Contact]:
        lower = f"%{query}%"
        rows = self._conn.execute(
            """
            SELECT * FROM phone_contacts
            WHERE LOWER(display_name) LIKE LOWER(?)
               OR LOWER(aliases) LIKE LOWER(?)
            """,
            (lower, lower),
        ).fetchall()
        return [self._row_to_contact(row) for row in rows]

    def _row_to_contact(self, row: sqlite3.Row) -> Contact:
        return Contact(
            contact_id=row["contact_id"],
            display_name=row["display_name"],
            aliases=self._from_json(row["aliases"]),
            phones=self._from_json(row["phones"]),
            emails=self._from_json(row["emails"]),
            company=row["company"] or "",
            relationship=row["relationship"] or "",
            notes=row["notes"] or "",
        )

    # Calendar

    def add_calendar_event(self, event: CalendarEvent) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO phone_calendar_events
            (event_id, title, start_at, end_at, participant_contact_ids, location, notes, created_by_tool)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.title,
                self._iso(event.start_at),
                self._iso(event.end_at),
                self._to_json(event.participant_contact_ids),
                event.location,
                event.notes,
                1 if event.created_by_tool else 0,
            ),
        )
        self._conn.commit()

    def get_calendar_event(self, event_id: str) -> CalendarEvent | None:
        row = self._conn.execute(
            "SELECT * FROM phone_calendar_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_calendar_event(row)

    def search_calendar(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        keyword: str | None = None,
    ) -> list[CalendarEvent]:
        sql = "SELECT * FROM phone_calendar_events WHERE 1=1"
        params: list[Any] = []
        if start_at is not None:
            sql += " AND start_at >= ?"
            params.append(self._iso(start_at))
        if end_at is not None:
            sql += " AND end_at <= ?"
            params.append(self._iso(end_at))
        if keyword is not None:
            sql += " AND (LOWER(title) LIKE LOWER(?) OR LOWER(notes) LIKE LOWER(?))"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_calendar_event(row) for row in rows]

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
        self.add_calendar_event(event)
        return event

    def _row_to_calendar_event(self, row: sqlite3.Row) -> CalendarEvent:
        return CalendarEvent(
            event_id=row["event_id"],
            title=row["title"],
            start_at=datetime.fromisoformat(row["start_at"]),
            end_at=datetime.fromisoformat(row["end_at"]),
            participant_contact_ids=self._from_json(row["participant_contact_ids"]),
            location=row["location"] or "",
            notes=row["notes"] or "",
            created_by_tool=bool(row["created_by_tool"]),
        )

    # Messages

    def add_message_thread(self, thread: MessageThread) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO phone_message_threads (thread_id, participant_contact_ids) VALUES (?, ?)",
            (thread.thread_id, self._to_json(thread.participant_contact_ids)),
        )
        for message in thread.messages:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO phone_messages
                (message_id, thread_id, sender_contact_id, sent_at, text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.thread_id,
                    message.sender_contact_id,
                    self._iso(message.sent_at),
                    message.text,
                ),
            )
        self._conn.commit()

    def get_message_thread(self, thread_id: str) -> MessageThread | None:
        row = self._conn.execute(
            "SELECT * FROM phone_message_threads WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_message_thread(row)

    def search_messages(
        self,
        *,
        keyword: str | None = None,
        contact_id: str | None = None,
    ) -> list[Message]:
        sql = "SELECT * FROM phone_messages WHERE 1=1"
        params: list[Any] = []
        if contact_id is not None:
            sql += " AND sender_contact_id = ?"
            params.append(contact_id)
        if keyword is not None:
            sql += " AND LOWER(text) LIKE LOWER(?)"
            params.append(f"%{keyword}%")
        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_message(row) for row in rows]

    def list_message_threads(self) -> list[MessageThread]:
        rows = self._conn.execute("SELECT * FROM phone_message_threads").fetchall()
        return [self._row_to_message_thread(row) for row in rows]

    def _row_to_message_thread(self, row: sqlite3.Row) -> MessageThread:
        thread_id = row["thread_id"]
        message_rows = self._conn.execute(
            "SELECT * FROM phone_messages WHERE thread_id = ? ORDER BY sent_at",
            (thread_id,),
        ).fetchall()
        return MessageThread(
            thread_id=thread_id,
            participant_contact_ids=self._from_json(row["participant_contact_ids"]),
            messages=[self._row_to_message(mrow) for mrow in message_rows],
        )

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        return Message(
            message_id=row["message_id"],
            thread_id=row["thread_id"],
            sender_contact_id=row["sender_contact_id"],
            sent_at=datetime.fromisoformat(row["sent_at"]),
            text=row["text"],
        )

    # Drafts

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
        self._conn.execute(
            """
            INSERT INTO phone_message_drafts
            (draft_id, thread_id, recipient_contact_ids, text, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                draft.draft_id,
                draft.thread_id,
                self._to_json(draft.recipient_contact_ids),
                draft.text,
                self._iso(draft.created_at) if draft.created_at else None,
            ),
        )
        self._conn.commit()
        return draft

    def list_message_drafts(self) -> list[MessageDraft]:
        rows = self._conn.execute(
            "SELECT * FROM phone_message_drafts ORDER BY created_at"
        ).fetchall()
        return [self._row_to_draft(row) for row in rows]

    def _row_to_draft(self, row: sqlite3.Row) -> MessageDraft:
        return MessageDraft(
            draft_id=row["draft_id"],
            thread_id=row["thread_id"],
            recipient_contact_ids=self._from_json(row["recipient_contact_ids"]),
            text=row["text"],
            created_at=self._parse_iso(row["created_at"]),
        )
