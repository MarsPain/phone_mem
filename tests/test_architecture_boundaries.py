from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ArchitectureBoundaryTest(unittest.TestCase):
    def test_storage_does_not_import_permission_service_module(self) -> None:
        storage_source = (ROOT / "phone_mem" / "personal_memory_service" / "storage.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("phone_mem.governance.permissions", storage_source)


if __name__ == "__main__":
    unittest.main()
