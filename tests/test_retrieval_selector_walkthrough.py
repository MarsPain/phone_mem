from __future__ import annotations

import unittest

from examples.retrieval_selector_walkthrough import run_walkthrough


class RetrievalSelectorWalkthroughTest(unittest.TestCase):
    def test_walkthrough_demonstrates_scoped_selector_queries(self) -> None:
        result = run_walkthrough()

        self.assertEqual(result["all_planning_event_ids"], ["event-1", "event-2"])
        self.assertEqual(result["calendar_planning_event_ids"], ["event-1"])
        self.assertEqual(result["app_action_event_ids"], ["event-2"])
        self.assertEqual(result["travel_event_ids"], ["event-3"])
        self.assertEqual(result["deleted_travel_event_ids"], ["event-3"])
        self.assertEqual(result["post_delete_travel_event_ids"], [])


if __name__ == "__main__":
    unittest.main()
