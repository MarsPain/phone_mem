from __future__ import annotations

from datetime import UTC, datetime
import sqlite3
import unittest

from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
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
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore
from phone_mem.personal_memory_service.storage import TombstoneRecord


class SQLiteSchemaTest(unittest.TestCase):
    def test_initialize_schema_creates_mvp_tables(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()

        table_names = {
            row[0]
            for row in store.connection.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

        self.assertIn("memory_events", table_names)
        self.assertIn("entities", table_names)
        self.assertIn("event_entities", table_names)
        self.assertIn("permissions", table_names)
        self.assertIn("audit_log", table_names)
        self.assertIn("tombstones", table_names)

    def test_connection_uses_row_factory(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")

        self.assertIs(store.connection.row_factory, sqlite3.Row)

    def test_close_closes_connection(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")

        store.close()

        with self.assertRaises(sqlite3.ProgrammingError):
            store.connection.execute("select 1")


def make_event(event_id: str, *, app: str = "system_assistant", entity: str = "user") -> MemoryEvent:
    created_at = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
    return MemoryEvent(
        event_id=event_id,
        created_at=created_at,
        valid_time=ValidTime(start=created_at),
        event_type=EventType.USER_UTTERANCE,
        memory_layer=MemoryLayer.EPISODIC,
        semantic_description=f"{entity} prefers morning planning sessions.",
        entities=[entity],
        relations=[],
        source=EventSource(
            app=app,
            actor=Actor.USER,
            modality=[Modality.TEXT],
            attribution=Attribution.USER_STATED,
        ),
        privacy=Privacy(
            level=PrivacyLevel.PERSONAL,
            allowed_scopes=[app],
            processing_policy=ProcessingPolicy.CLIENT_ENCRYPTED_SYNC,
        ),
        quality=Quality(confidence=0.95, importance=0.7, freshness_half_life_days=30),
        lineage=Lineage(),
        lifecycle=Lifecycle(),
    )


class SQLiteEventPersistenceTest(unittest.TestCase):
    def test_insert_and_get_event_round_trips_canonical_data(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        event = make_event("event-1")

        store.insert_event(event)

        loaded = store.get_event("event-1")
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.event_id, "event-1")
        self.assertEqual(loaded.source.app, "system_assistant")
        self.assertEqual(loaded.privacy.level, PrivacyLevel.PERSONAL)
        self.assertEqual(loaded.entities, ["user"])

    def test_query_events_applies_selector_filters(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        store.insert_event(make_event("event-1", app="system_assistant", entity="user"))
        store.insert_event(make_event("event-2", app="calendar", entity="calendar"))

        results = store.query_events(
            MemorySelector(
                app="system_assistant",
                entities=["user"],
                memory_layers=[MemoryLayer.EPISODIC],
                privacy_levels=[PrivacyLevel.PERSONAL],
                lifecycle_states=[LifecycleState.ACTIVE],
            )
        )

        self.assertEqual([event.event_id for event in results], ["event-1"])


class SQLiteLifecycleAndTombstoneTest(unittest.TestCase):
    def test_update_lifecycle_hides_deleted_event_from_active_selector(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        event = make_event("event-1")
        store.insert_event(event)
        deleted_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)

        store.update_lifecycle(
            "event-1",
            Lifecycle().mark_deleted(deleted_at=deleted_at, reason="user requested deletion"),
        )

        active = store.query_events(MemorySelector(lifecycle_states=[LifecycleState.ACTIVE]))
        deleted = store.get_event("event-1")
        self.assertEqual(active, [])
        self.assertIsNotNone(deleted)
        assert deleted is not None
        self.assertEqual(deleted.lifecycle.state, LifecycleState.DELETED)

    def test_write_tombstone_records_deleted_event_and_selector(self) -> None:
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        deleted_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
        tombstone = TombstoneRecord(
            tombstone_id="tombstone-1",
            event_id="event-1",
            deleted_at=deleted_at,
            reason="user requested deletion",
            selector=MemorySelector(event_ids=["event-1"]),
        )

        store.write_tombstone(tombstone)

        self.assertEqual(store.list_tombstones(), [tombstone])


if __name__ == "__main__":
    unittest.main()
