from __future__ import annotations

import json
from pathlib import Path
import unittest

from tests.memory_service_contract_outputs import reference_outputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "memory_service"


class Stage2MobileWorkspaceBoundaryTest(unittest.TestCase):
    def test_mobile_workspace_is_not_a_stale_implementation_boundary(self) -> None:
        stale_files = [
            "mobile/README.md",
            "mobile/memory_core/events.ts",
            "mobile/governance/permissions.ts",
            "mobile/governance/audit.ts",
            "mobile/storage/storage.ts",
            "mobile/retrieval/retrieval.ts",
            "mobile/context/context.ts",
            "mobile/service/personal_memory_service.ts",
        ]

        for relative_path in stale_files:
            self.assertFalse((ROOT / relative_path).exists(), relative_path)

        self.assertFalse((ROOT / "mobile" / "package.json").exists())

    def test_stage2_plan_explains_future_mobile_restart(self) -> None:
        plan = ROOT / "docs" / "exec-plans" / "tech-debt" / "deferred-stage2-mobile-runtime-prototype.md"
        text = plan.read_text(encoding="utf-8")

        for expected in [
            "Status: deferred",
            "Stage 1.7",
            "recreated",
            "No TypeScript boundary files are retained",
        ]:
            self.assertIn(expected, text)


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
            "metrics_snapshot.json",
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
