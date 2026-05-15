from __future__ import annotations

import unittest

from phone_mem.phone_tools.in_memory_store import InMemoryPhoneToolStore
from phone_mem.phone_tools.registry import PhoneToolRegistry
from phone_mem.phone_tools.seed import seed_research_phone_state


class PhoneToolRegistryTest(unittest.TestCase):
    def test_tool_definitions_expose_expected_phone_tools(self) -> None:
        registry = PhoneToolRegistry(InMemoryPhoneToolStore())
        definitions = {definition.name: definition for definition in registry.tool_definitions()}

        self.assertIn("search_contacts", definitions)
        self.assertIn("get_contact", definitions)
        self.assertIn("search_calendar", definitions)
        self.assertIn("create_calendar_event", definitions)
        self.assertIn("search_messages", definitions)
        self.assertIn("get_message_thread", definitions)
        self.assertIn("draft_message", definitions)
        self.assertEqual(definitions["draft_message"].parameters["type"], "object")

    def test_read_tools_are_trace_only(self) -> None:
        store = InMemoryPhoneToolStore()
        seed_research_phone_state(store)
        registry = PhoneToolRegistry(store)

        result = registry.execute("search_contacts", {"query": "Alice"})

        self.assertFalse(result.observation.capture_worthy)
        self.assertEqual(result.result["contacts"][0]["display_name"], "Alice Chen")

    def test_create_calendar_event_is_capture_worthy(self) -> None:
        registry = PhoneToolRegistry(InMemoryPhoneToolStore())

        result = registry.execute(
            "create_calendar_event",
            {
                "title": "Review mock phone tools",
                "start_at": "2026-05-15T15:00:00+00:00",
                "end_at": "2026-05-15T16:00:00+00:00",
                "participant_contact_ids": ["contact-alice"],
                "location": "Office",
                "notes": "Discuss tool capture policy.",
            },
        )

        self.assertTrue(result.observation.capture_worthy)
        self.assertIn("created a calendar event", result.observation.text)
        self.assertEqual(result.result["event"]["title"], "Review mock phone tools")

    def test_draft_message_is_capture_worthy(self) -> None:
        registry = PhoneToolRegistry(InMemoryPhoneToolStore())

        result = registry.execute(
            "draft_message",
            {
                "thread_id": "thread-alice",
                "recipient_contact_ids": ["contact-alice"],
                "text": "Friday afternoon works.",
            },
        )

        self.assertTrue(result.observation.capture_worthy)
        self.assertIn("drafted a message", result.observation.text)
        self.assertEqual(result.result["draft"]["text"], "Friday afternoon works.")


if __name__ == "__main__":
    unittest.main()
