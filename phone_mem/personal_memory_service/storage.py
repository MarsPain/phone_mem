from __future__ import annotations

from dataclasses import dataclass
import sqlite3


class StorageError(RuntimeError):
    """Raised when persisted memory state is invalid."""


@dataclass(frozen=True)
class SQLiteMemoryStore:
    connection: sqlite3.Connection

    @classmethod
    def connect(cls, path: str = ":memory:") -> SQLiteMemoryStore:
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        return cls(connection=connection)

    def initialize_schema(self) -> None:
        self.connection.executescript(
            """
            create table if not exists memory_events (
                event_id text primary key,
                created_at text not null,
                valid_start text not null,
                valid_end text,
                event_type text not null,
                memory_layer text not null,
                semantic_description text not null,
                source_app text not null,
                privacy_level text not null,
                processing_policy text not null,
                lifecycle_state text not null,
                event_json text not null
            );

            create table if not exists entities (
                entity text primary key
            );

            create table if not exists event_entities (
                event_id text not null,
                entity text not null,
                primary key (event_id, entity),
                foreign key (event_id) references memory_events(event_id)
            );

            create table if not exists permissions (
                grant_id text primary key,
                caller text not null,
                operation text not null,
                scope_json text not null,
                granted_at text not null,
                expires_at text not null,
                revoked_at text
            );

            create table if not exists audit_log (
                operation_id text primary key,
                caller text not null,
                operation text not null,
                scope_json text not null,
                affected_event_ids_json text not null,
                occurred_at text not null,
                outcome text not null,
                denial_reason text
            );

            create table if not exists tombstones (
                tombstone_id text primary key,
                event_id text not null,
                deleted_at text not null,
                reason text not null,
                selector_json text not null
            );
            """
        )
        self.connection.commit()
