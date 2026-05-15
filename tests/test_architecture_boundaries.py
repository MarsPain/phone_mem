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

    def test_phone_tools_do_not_import_agent_runtime(self) -> None:
        phone_tools_dir = ROOT / "phone_mem" / "phone_tools"
        sources = {
            path: path.read_text(encoding="utf-8")
            for path in phone_tools_dir.glob("*.py")
        }

        offenders = [
            str(path.relative_to(ROOT))
            for path, source in sources.items()
            if "phone_mem.agent_runtime" in source
        ]

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
