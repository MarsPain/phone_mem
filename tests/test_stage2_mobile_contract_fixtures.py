from __future__ import annotations

import json
from pathlib import Path
import unittest

from tests.memory_service_contract_outputs import reference_outputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "memory_service"


class Stage2MobileWorkspaceBoundaryTest(unittest.TestCase):
    def test_mobile_workspace_documents_reference_service_domains(self) -> None:
        readme = ROOT / "mobile" / "README.md"
        self.assertTrue(readme.exists(), "mobile/README.md should describe Stage 2 scope")
        text = readme.read_text(encoding="utf-8")

        for expected in [
            "memory_core",
            "governance",
            "storage",
            "retrieval",
            "context",
            "service",
            "Python reference",
        ]:
            self.assertIn(expected, text)

    def test_mobile_type_boundaries_exist_without_toolchain_lock_in(self) -> None:
        expected_files = [
            "mobile/memory_core/events.ts",
            "mobile/governance/permissions.ts",
            "mobile/governance/audit.ts",
            "mobile/storage/storage.ts",
            "mobile/retrieval/retrieval.ts",
            "mobile/context/context.ts",
            "mobile/service/personal_memory_service.ts",
        ]

        for relative_path in expected_files:
            self.assertTrue((ROOT / relative_path).exists(), relative_path)

        self.assertFalse((ROOT / "mobile" / "package.json").exists())

    def test_mobile_service_contract_names_stabilized_python_api_shapes(self) -> None:
        service_contract = (ROOT / "mobile" / "service" / "personal_memory_service.ts").read_text(
            encoding="utf-8"
        )
        event_contract = (ROOT / "mobile" / "memory_core" / "events.ts").read_text(
            encoding="utf-8"
        )

        for expected in [
            "MemoryExplanation",
            "ServiceErrorContract",
            "SearchOptions",
            "BuildContextOptions",
            "delete(selector: MemorySelector",
        ]:
            self.assertIn(expected, service_contract)

        for expected in [
            "interface MemorySelector",
            "interface LifecycleExplanation",
            "interface MemoryExplanation",
        ]:
            self.assertIn(expected, event_contract)


class MemoryServiceFixtureContractTest(unittest.TestCase):
    def test_required_fixture_files_exist(self) -> None:
        expected_files = [
            "canonical_event.json",
            "permission_grant.json",
            "search_result.json",
            "context_bundle.json",
            "delete_tombstone.json",
            "audit_records.json",
            "lifecycle_explanations.json",
            "service_errors.json",
        ]

        for file_name in expected_files:
            with self.subTest(file_name=file_name):
                self.assertTrue((FIXTURE_DIR / file_name).exists())

    def test_fixtures_match_python_reference_service_output(self) -> None:
        actual = reference_outputs()

        for name, expected in actual.items():
            path = FIXTURE_DIR / f"{name}.json"
            with self.subTest(path=path):
                loaded = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(loaded, expected)


if __name__ == "__main__":
    unittest.main()
