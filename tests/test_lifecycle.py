from __future__ import annotations

import unittest

from phone_mem.personal_memory_service.events import LifecycleState, MemoryLayer, MemorySelector
from phone_mem.personal_memory_service.lifecycle import MemoryLifecycleValidator
from tests.test_storage import make_event


class RecordingStore:
    def __init__(self) -> None:
        self.selectors: list[MemorySelector] = []

    def query_events(self, selector: MemorySelector) -> list[object]:
        self.selectors.append(selector)
        return []


class MemoryLifecycleValidatorTest(unittest.TestCase):
    def test_duplicate_lookup_queries_only_same_app_layer_entity_active_candidates(self) -> None:
        store = RecordingStore()
        validator = MemoryLifecycleValidator(store)
        event = make_event("event-1", app="system_assistant", entity="planning")

        validator.find_duplicate(event)

        self.assertEqual(len(store.selectors), 1)
        selector = store.selectors[0]
        self.assertEqual(selector.app, "system_assistant")
        self.assertEqual(selector.entities, ["planning"])
        self.assertEqual(selector.memory_layers, [MemoryLayer.EPISODIC])
        self.assertEqual(selector.lifecycle_states, [LifecycleState.ACTIVE])


if __name__ == "__main__":
    unittest.main()
