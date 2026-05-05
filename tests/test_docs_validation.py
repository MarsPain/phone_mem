from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import validate_docs


class DocumentationValidationTest(unittest.TestCase):
    def test_docs_validation_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_docs.py"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_active_plan_bucket_may_be_empty_after_all_plans_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for bucket in ["active", "completed", "tech-debt"]:
                (root / "docs" / "exec-plans" / bucket).mkdir(parents=True)
            (root / "docs" / "exec-plans" / "completed" / "done.md").write_text(
                "Status: completed\n",
                encoding="utf-8",
            )
            (root / "docs" / "exec-plans" / "tech-debt" / "debt.md").write_text(
                "Status: deferred\n",
                encoding="utf-8",
            )

            original_root = validate_docs.ROOT
            validate_docs.ROOT = root
            try:
                errors: list[str] = []
                validate_docs.validate_plan_buckets(errors)
            finally:
                validate_docs.ROOT = original_root

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
