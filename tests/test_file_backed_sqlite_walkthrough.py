from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from examples.file_backed_sqlite_walkthrough import run_walkthrough
from phone_mem.personal_memory_service.events import AuditOperation


class FileBackedSQLiteWalkthroughTest(unittest.TestCase):
    def test_walkthrough_persists_service_state_across_reopens(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "memory.sqlite3"

            result = run_walkthrough(db_path)

        event_id = result["event_id"]
        self.assertEqual(result["db_path"], str(db_path))
        self.assertEqual(result["after_reopen_search_event_ids"], [event_id])
        self.assertIn(AuditOperation.GRANT.value, result["after_reopen_audit_operations"])
        self.assertIn(AuditOperation.WRITE.value, result["after_reopen_audit_operations"])
        self.assertEqual(result["after_reopen_tombstone_event_ids"], [])
        self.assertEqual(result["deleted_event_ids"], [event_id])
        self.assertEqual(result["after_delete_reopen_search_event_ids"], [])
        self.assertEqual(result["after_delete_reopen_tombstone_event_ids"], [event_id])
        self.assertIn(AuditOperation.DELETE.value, result["after_delete_reopen_audit_operations"])

    def test_walkthrough_script_runs_directly_with_db_path(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "memory.sqlite3"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(project_root / "examples" / "file_backed_sqlite_walkthrough.py"),
                    str(db_path),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
