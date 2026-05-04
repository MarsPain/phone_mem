from __future__ import annotations

import unittest

from examples.python_reference_walkthrough import run_walkthrough


class PythonReferenceWalkthroughTest(unittest.TestCase):
    def test_walkthrough_demonstrates_core_lifecycle(self) -> None:
        result = run_walkthrough()

        self.assertEqual(result["event_id"], "event-1")
        self.assertEqual(result["search_event_ids"], ["event-1"])
        self.assertEqual(result["context_evidence_event_ids"], ["event-1"])
        self.assertEqual(result["deleted_event_ids"], ["event-1"])
        self.assertEqual(result["post_delete_search_event_ids"], [])
        self.assertGreaterEqual(result["audit_record_count"], 6)
        self.assertEqual(result["metrics"]["deletion"]["tombstone_count"], 1)


if __name__ == "__main__":
    unittest.main()
