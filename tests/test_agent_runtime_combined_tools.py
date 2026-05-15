from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.agent_runtime.client import FakeLLMClient, LLMResponse, ToolCall
from phone_mem.agent_runtime.runtime import AgentRuntime
from phone_mem.agent_runtime.tool_provider import CombinedToolProvider
from phone_mem.agent_runtime.tools import MemoryToolRegistry
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.events import AuditOperation, MemoryLayer, PrivacyLevel
from phone_mem.personal_memory_service.service import PersonalMemoryService
from phone_mem.phone_tools.in_memory_store import InMemoryPhoneToolStore
from phone_mem.phone_tools.registry import PhoneToolRegistry


CALLER = "runtime_agent"
SOURCE_APP = "system_assistant"


class AgentRuntimeCombinedToolsTest(unittest.TestCase):
    def test_combined_provider_exposes_memory_and_phone_tools(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        provider = CombinedToolProvider(
            memory_tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
            phone_tools=PhoneToolRegistry(InMemoryPhoneToolStore()),
        )

        names = {definition.name for definition in provider.tool_definitions()}

        self.assertIn("search_memory", names)
        self.assertIn("create_calendar_event", names)

    def test_phone_action_observation_is_captured_as_governed_memory(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        provider = CombinedToolProvider(
            memory_tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
            phone_tools=PhoneToolRegistry(InMemoryPhoneToolStore()),
        )
        runtime = AgentRuntime(
            client=FakeLLMClient(
                [
                    LLMResponse(
                        text="",
                        tool_calls=[
                            ToolCall(
                                call_id="call-1",
                                name="create_calendar_event",
                                arguments={
                                    "title": "Dentist appointment",
                                    "start_at": "2026-05-15T15:00:00+00:00",
                                    "end_at": "2026-05-15T16:00:00+00:00",
                                    "participant_contact_ids": ["contact-alice"],
                                    "location": "Clinic",
                                    "notes": "Bring insurance card.",
                                },
                            )
                        ],
                    ),
                    LLMResponse(text="I created the calendar event."),
                ]
            ),
            model="fake-model",
            tools=provider,
        )

        response = runtime.run_turn("Schedule my dentist appointment for Friday at 3 PM.")

        self.assertEqual(response.tool_results[0]["name"], "create_calendar_event")
        self.assertEqual(response.captured_event_ids, ["event-1"])
        search = provider.memory_tools.search_memory("dentist appointment", top_k=3)
        self.assertEqual(search["results"][0]["event_id"], "event-1")


def _service_with_grant() -> PersonalMemoryService:
    service = PersonalMemoryService.in_memory(clock=lambda: datetime(2026, 5, 14, 9, 0, tzinfo=UTC))
    service.grant(
        CALLER,
        PermissionScope(
            operations=[
                AuditOperation.WRITE,
                AuditOperation.READ,
                AuditOperation.UPDATE,
                AuditOperation.DELETE,
                AuditOperation.CONTEXT_BUILD,
            ],
            apps=[SOURCE_APP],
            privacy_levels=[PrivacyLevel.PERSONAL],
            memory_layers=[MemoryLayer.EPISODIC],
        ),
        duration_seconds=3_600,
    )
    return service
