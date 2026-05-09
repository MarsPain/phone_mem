from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
import json
import sqlite3
from typing import Any

from phone_mem.governance.models import PermissionGrant, PermissionScope
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    AuditOperation,
    AuditRecord,
    EventSource,
    EventType,
    Lifecycle,
    LifecycleState,
    Lineage,
    MemoryEvent,
    MemoryLayer,
    MemorySelector,
    Modality,
    Privacy,
    PrivacyLevel,
    ProcessingPolicy,
    Quality,
    ValidTime,
)


class StorageError(RuntimeError):
    """Raised when persisted memory state is invalid."""


@dataclass(frozen=True)
class TombstoneRecord:
    tombstone_id: str
    event_id: str
    deleted_at: datetime
    reason: str
    selector: MemorySelector


@dataclass
class SQLiteMemoryStore:
    connection: sqlite3.Connection
    _transaction_depth: int = 0
    _fts_enabled: bool = False

    @classmethod
    def connect(cls, path: str = ":memory:") -> SQLiteMemoryStore:
        connection = sqlite3.connect(path, check_same_thread=False)
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

            create table if not exists lineage_edges (
                child_event_id text not null,
                relation text not null,
                parent_event_id text not null,
                primary key (child_event_id, relation, parent_event_id),
                foreign key (child_event_id) references memory_events(event_id)
            );

            create index if not exists idx_memory_events_lifecycle_app_layer_created
            on memory_events(lifecycle_state, source_app, memory_layer, created_at);

            create index if not exists idx_event_entities_entity_event
            on event_entities(entity, event_id);

            create index if not exists idx_permissions_caller_operation_expiry
            on permissions(caller, operation, expires_at, revoked_at);

            create index if not exists idx_audit_log_caller_operation_time
            on audit_log(caller, operation, occurred_at);

            create index if not exists idx_lineage_edges_parent_relation
            on lineage_edges(parent_event_id, relation, child_event_id);
            """
        )
        self._initialize_fts_projection()
        self._commit_if_needed()

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self._transaction_depth > 0:
            self._transaction_depth += 1
            try:
                yield
            finally:
                self._transaction_depth -= 1
            return

        self.connection.execute("begin")
        self._transaction_depth = 1
        try:
            yield
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()
        finally:
            self._transaction_depth = 0

    def insert_event(self, event: MemoryEvent) -> None:
        data = event.to_dict()
        self.connection.execute(
            """
            insert into memory_events (
                event_id, created_at, valid_start, valid_end, event_type,
                memory_layer, semantic_description, source_app, privacy_level,
                processing_policy, lifecycle_state, event_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.created_at.isoformat(),
                event.valid_time.start.isoformat(),
                event.valid_time.end.isoformat() if event.valid_time.end else None,
                event.event_type.value,
                event.memory_layer.value,
                event.semantic_description,
                event.source.app,
                event.privacy.level.value,
                event.privacy.processing_policy.value,
                event.lifecycle.state.value,
                json.dumps(data, sort_keys=True),
            ),
        )
        for entity in event.entities:
            self.connection.execute("insert or ignore into entities(entity) values (?)", (entity,))
            self.connection.execute(
                "insert or ignore into event_entities(event_id, entity) values (?, ?)",
                (event.event_id, entity),
            )
        self._insert_lineage_edges(event)
        self._upsert_fts_event(event)
        self._commit_if_needed()

    def get_event(self, event_id: str) -> MemoryEvent | None:
        row = self.connection.execute(
            "select event_json from memory_events where event_id = ?",
            (event_id,),
        ).fetchone()
        if row is None:
            return None
        return self._event_from_dict(json.loads(row["event_json"]))

    def query_events(self, selector: MemorySelector | None = None) -> list[MemoryEvent]:
        selector = selector or MemorySelector()
        sql = ["select distinct e.event_json from memory_events e"]
        params: list[str] = []
        if selector.entities:
            sql.append("join event_entities ee on ee.event_id = e.event_id")

        where: list[str] = []
        if selector.event_ids:
            where.append(f"e.event_id in ({self._placeholders(selector.event_ids)})")
            params.extend(selector.event_ids)
        if selector.app is not None:
            where.append("e.source_app = ?")
            params.append(selector.app)
        if selector.entities:
            where.append(f"ee.entity in ({self._placeholders(selector.entities)})")
            params.extend(selector.entities)
        if selector.memory_layers:
            where.append(f"e.memory_layer in ({self._placeholders(selector.memory_layers)})")
            params.extend(item.value for item in selector.memory_layers)
        if selector.privacy_levels:
            where.append(f"e.privacy_level in ({self._placeholders(selector.privacy_levels)})")
            params.extend(item.value for item in selector.privacy_levels)
        if selector.lifecycle_states:
            where.append(f"e.lifecycle_state in ({self._placeholders(selector.lifecycle_states)})")
            params.extend(item.value for item in selector.lifecycle_states)
        if selector.time_start is not None:
            where.append("e.valid_start >= ?")
            params.append(selector.time_start.isoformat())
        if selector.time_end is not None:
            where.append("e.valid_start <= ?")
            params.append(selector.time_end.isoformat())
        if where:
            sql.append("where " + " and ".join(where))
        sql.append("order by e.created_at, e.event_id")

        rows = self.connection.execute(" ".join(sql), params).fetchall()
        return [self._event_from_dict(json.loads(row["event_json"])) for row in rows]

    def bm25_scores(self, query: str, event_ids: list[str]) -> dict[str, float]:
        if not self._fts_enabled or not event_ids:
            return {}
        match_query = self._fts_query(query)
        if not match_query:
            return {}
        placeholders = self._placeholders(event_ids)
        try:
            rows = self.connection.execute(
                f"""
                select event_id, bm25(memory_event_fts) as rank
                from memory_event_fts
                where memory_event_fts match ?
                and event_id in ({placeholders})
                """,
                [match_query, *event_ids],
            ).fetchall()
        except sqlite3.OperationalError:
            return {}
        return {
            row["event_id"]: round(max(-float(row["rank"]), 0.0), 6)
            for row in rows
        }

    def update_lifecycle(self, event_id: str, lifecycle: Lifecycle) -> None:
        event = self.get_event(event_id)
        if event is None:
            raise StorageError(f"memory event not found: {event_id}")
        updated = replace(event, lifecycle=lifecycle)
        data = updated.to_dict()
        self.connection.execute(
            """
            update memory_events
            set lifecycle_state = ?, event_json = ?
            where event_id = ?
            """,
            (
                lifecycle.state.value,
                json.dumps(data, sort_keys=True),
                event_id,
            ),
        )
        self._commit_if_needed()

    def write_tombstone(self, tombstone: TombstoneRecord) -> None:
        self.connection.execute(
            """
            insert into tombstones (
                tombstone_id, event_id, deleted_at, reason, selector_json
            ) values (?, ?, ?, ?, ?)
            """,
            (
                tombstone.tombstone_id,
                tombstone.event_id,
                tombstone.deleted_at.isoformat(),
                tombstone.reason,
                json.dumps(tombstone.selector.to_dict(), sort_keys=True),
            ),
        )
        self._commit_if_needed()

    def list_tombstones(self) -> list[TombstoneRecord]:
        rows = self.connection.execute(
            "select * from tombstones order by deleted_at, tombstone_id"
        ).fetchall()
        return [
            TombstoneRecord(
                tombstone_id=row["tombstone_id"],
                event_id=row["event_id"],
                deleted_at=datetime.fromisoformat(row["deleted_at"]),
                reason=row["reason"],
                selector=self._selector_from_dict(json.loads(row["selector_json"])),
            )
            for row in rows
        ]

    def events_superseding(self, event_id: str) -> list[str]:
        rows = self.connection.execute(
            """
            select child_event_id
            from lineage_edges
            where parent_event_id = ? and relation = 'supersedes'
            order by child_event_id
            """,
            (event_id,),
        ).fetchall()
        return [row["child_event_id"] for row in rows]

    def insert_permission_grant(self, grant: PermissionGrant) -> None:
        operation = self._permission_operation_index_value(grant)
        self.connection.execute(
            """
            insert into permissions (
                grant_id, caller, operation, scope_json, granted_at, expires_at, revoked_at
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                grant.grant_id,
                grant.caller,
                operation,
                json.dumps(grant.scope.to_dict(), sort_keys=True),
                grant.granted_at.isoformat(),
                grant.expires_at.isoformat(),
                grant.revoked_at.isoformat() if grant.revoked_at is not None else None,
            ),
        )
        self._commit_if_needed()

    def update_permission_grant(self, grant: PermissionGrant) -> None:
        self.connection.execute(
            """
            update permissions
            set scope_json = ?, granted_at = ?, expires_at = ?, revoked_at = ?
            where grant_id = ?
            """,
            (
                json.dumps(grant.scope.to_dict(), sort_keys=True),
                grant.granted_at.isoformat(),
                grant.expires_at.isoformat(),
                grant.revoked_at.isoformat() if grant.revoked_at is not None else None,
                grant.grant_id,
            ),
        )
        self._commit_if_needed()

    def list_permission_grants(self, caller: str | None = None) -> list[PermissionGrant]:
        if caller is None:
            rows = self.connection.execute(
                "select * from permissions order by granted_at, grant_id"
            ).fetchall()
        else:
            rows = self.connection.execute(
                "select * from permissions where caller = ? order by granted_at, grant_id",
                (caller,),
            ).fetchall()
        return [self._permission_grant_from_row(row) for row in rows]

    def list_active_permission_grants(
        self,
        caller: str,
        operation: AuditOperation,
        *,
        at: datetime,
    ) -> list[PermissionGrant]:
        checked_at = at.isoformat()
        rows = self.connection.execute(
            """
            select *
            from permissions
            where caller = ?
              and (operation = ? or operation = '*')
              and granted_at <= ?
              and expires_at >= ?
              and revoked_at is null
            order by granted_at, grant_id
            """,
            (caller, operation.value, checked_at, checked_at),
        ).fetchall()
        return [self._permission_grant_from_row(row) for row in rows]

    def insert_audit_record(self, record: AuditRecord) -> None:
        self.connection.execute(
            """
            insert into audit_log (
                operation_id, caller, operation, scope_json,
                affected_event_ids_json, occurred_at, outcome, denial_reason
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.operation_id,
                record.caller,
                record.operation.value,
                json.dumps(record.scope, sort_keys=True),
                json.dumps(record.affected_event_ids, sort_keys=True),
                record.occurred_at.isoformat(),
                record.outcome,
                record.denial_reason,
            ),
        )
        self._commit_if_needed()

    def query_audit_records(self, selector: object | None = None) -> list[AuditRecord]:
        sql = ["select * from audit_log"]
        params: list[str] = []
        where: list[str] = []
        caller = getattr(selector, "caller", None)
        operations = getattr(selector, "operations", []) if selector is not None else []
        if caller is not None:
            where.append("caller = ?")
            params.append(caller)
        if operations:
            where.append(f"operation in ({self._placeholders(operations)})")
            params.extend(operation.value for operation in operations)
        if where:
            sql.append("where " + " and ".join(where))
        sql.append("order by occurred_at, operation_id")
        rows = self.connection.execute(" ".join(sql), params).fetchall()
        return [self._audit_record_from_row(row) for row in rows]

    def _event_from_dict(self, data: dict[str, Any]) -> MemoryEvent:
        return MemoryEvent(
            event_id=data["event_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            valid_time=ValidTime(
                start=datetime.fromisoformat(data["valid_time"]["start"]),
                end=(
                    datetime.fromisoformat(data["valid_time"]["end"])
                    if data["valid_time"]["end"] is not None
                    else None
                ),
            ),
            event_type=EventType(data["event_type"]),
            memory_layer=MemoryLayer(data["memory_layer"]),
            semantic_description=data["semantic_description"],
            entities=list(data["entities"]),
            relations=list(data["relations"]),
            source=EventSource(
                app=data["source"]["app"],
                actor=Actor(data["source"]["actor"]),
                modality=[Modality(item) for item in data["source"]["modality"]],
                attribution=Attribution(data["source"]["attribution"]),
            ),
            privacy=Privacy(
                level=PrivacyLevel(data["privacy"]["level"]),
                allowed_scopes=list(data["privacy"]["allowed_scopes"]),
                processing_policy=ProcessingPolicy(data["privacy"]["processing_policy"]),
            ),
            quality=Quality(
                confidence=data["quality"]["confidence"],
                importance=data["quality"]["importance"],
                freshness_half_life_days=data["quality"]["freshness_half_life_days"],
            ),
            lineage=Lineage(
                parents=list(data["lineage"]["parents"]),
                derived_from=list(data["lineage"]["derived_from"]),
                supersedes=list(data["lineage"]["supersedes"]),
            ),
            lifecycle=Lifecycle(
                state=LifecycleState(data["lifecycle"]["state"]),
                deleted_at=(
                    datetime.fromisoformat(data["lifecycle"]["deleted_at"])
                    if data["lifecycle"]["deleted_at"] is not None
                    else None
                ),
                delete_reason=data["lifecycle"]["delete_reason"],
            ),
        )

    def _commit_if_needed(self) -> None:
        if self._transaction_depth == 0:
            self.connection.commit()

    def _initialize_fts_projection(self) -> None:
        try:
            self.connection.execute(
                """
                create virtual table if not exists memory_event_fts
                using fts5(event_id unindexed, semantic_description, entities)
                """
            )
        except sqlite3.OperationalError:
            self._fts_enabled = False
            return
        self._fts_enabled = True

    def _upsert_fts_event(self, event: MemoryEvent) -> None:
        if not self._fts_enabled:
            return
        self.connection.execute(
            "delete from memory_event_fts where event_id = ?",
            (event.event_id,),
        )
        self.connection.execute(
            """
            insert into memory_event_fts(event_id, semantic_description, entities)
            values (?, ?, ?)
            """,
            (event.event_id, event.semantic_description, " ".join(event.entities)),
        )

    def _fts_query(self, query: str) -> str:
        terms: list[str] = []
        for raw_term in query.lower().replace('"', " ").split():
            term = "".join(character for character in raw_term if character.isalnum())
            if term:
                terms.append(term)
        return " ".join(terms)

    def _insert_lineage_edges(self, event: MemoryEvent) -> None:
        for relation, parent_event_ids in (
            ("parent", event.lineage.parents),
            ("derived_from", event.lineage.derived_from),
            ("supersedes", event.lineage.supersedes),
        ):
            for parent_event_id in parent_event_ids:
                self.connection.execute(
                    """
                    insert or ignore into lineage_edges (
                        child_event_id, relation, parent_event_id
                    ) values (?, ?, ?)
                    """,
                    (event.event_id, relation, parent_event_id),
                )

    def _permission_operation_index_value(self, grant: PermissionGrant) -> str:
        if len(grant.scope.operations) == 1:
            return grant.scope.operations[0].value
        return "*"

    def _placeholders(self, values: list[object]) -> str:
        return ",".join("?" for _ in values)

    def _selector_from_dict(self, data: dict[str, Any]) -> MemorySelector:
        return MemorySelector(
            event_ids=list(data.get("event_ids", [])),
            app=data.get("app"),
            entities=list(data.get("entities", [])),
            topics=list(data.get("topics", [])),
            memory_layers=[MemoryLayer(item) for item in data.get("memory_layers", [])],
            privacy_levels=[PrivacyLevel(item) for item in data.get("privacy_levels", [])],
            lifecycle_states=[
                LifecycleState(item) for item in data.get("lifecycle_states", [])
            ],
            time_start=(
                datetime.fromisoformat(data["time_start"])
                if data.get("time_start") is not None
                else None
            ),
            time_end=(
                datetime.fromisoformat(data["time_end"])
                if data.get("time_end") is not None
                else None
            ),
        )

    def _permission_grant_from_row(self, row: sqlite3.Row) -> PermissionGrant:
        return PermissionGrant(
            grant_id=row["grant_id"],
            caller=row["caller"],
            scope=PermissionScope.from_dict(json.loads(row["scope_json"])),
            granted_at=datetime.fromisoformat(row["granted_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            revoked_at=(
                datetime.fromisoformat(row["revoked_at"])
                if row["revoked_at"] is not None
                else None
            ),
        )

    def _audit_record_from_row(self, row: sqlite3.Row) -> AuditRecord:
        return AuditRecord(
            operation_id=row["operation_id"],
            caller=row["caller"],
            operation=AuditOperation(row["operation"]),
            scope=json.loads(row["scope_json"]),
            affected_event_ids=list(json.loads(row["affected_event_ids_json"])),
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
            outcome=row["outcome"],
            denial_reason=row["denial_reason"],
        )
