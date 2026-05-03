from __future__ import annotations

import sqlite3
import unittest

from phone_mem.personal_memory_service.storage import SQLiteMemoryStore


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


if __name__ == "__main__":
    unittest.main()
