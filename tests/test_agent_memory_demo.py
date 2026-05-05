from __future__ import annotations

import unittest

from examples.agent_memory_demo import run_demo


class AgentMemoryDemoTest(unittest.TestCase):
    def test_demo_tells_product_story_for_memory_lifecycle(self) -> None:
        result = run_demo()

        self.assertEqual(result["recorded_event_id"], "event-1")
        self.assertEqual(result["corrected_event_id"], "event-2")
        self.assertEqual(result["task_search_event_ids"], ["event-1"])
        self.assertEqual(result["post_correction_search_event_ids"], ["event-2"])
        self.assertEqual(result["deleted_event_ids"], ["event-2"])
        self.assertEqual(result["post_delete_search_event_ids"], [])
        self.assertIn("superseded by correction", result["original_lifecycle_reason"])
        self.assertIn("corrects previous memory", result["corrected_lifecycle_reason"])

        transcript = "\n".join(result["transcript"])
        for expected in [
            "Phone Memory Agent Demo",
            "User says",
            "Agent records",
            "Later task",
            "Context bundle",
            "User correction",
            "Lifecycle explanation",
            "User deletes",
        ]:
            self.assertIn(expected, transcript)


if __name__ == "__main__":
    unittest.main()
