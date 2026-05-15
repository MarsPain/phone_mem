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
from phone_mem.phone_tools.models import Contact, MessageThread
from phone_mem.phone_tools.registry import PhoneToolRegistry
from phone_mem.phone_tools.seed import seed_research_phone_state


CALLER = "runtime_agent"
SOURCE_APP = "system_assistant"


class AgentRuntimeCombinedToolsTest(unittest.TestCase):
    def test_combined_provider_exposes_memory_and_phone_tools(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        provider = CombinedToolProvider(
            memory_tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
            phone_tools=PhoneToolRegistry(_seeded_phone_store()),
        )

        names = {definition.name for definition in provider.tool_definitions()}

        self.assertIn("search_memory", names)
        self.assertIn("create_calendar_event", names)

    def test_phone_action_observation_is_captured_as_governed_memory(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        provider = CombinedToolProvider(
            memory_tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
            phone_tools=PhoneToolRegistry(_seeded_phone_store()),
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

    def test_runtime_executes_follow_up_phone_tool_calls_until_final_answer(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        phone_store = InMemoryPhoneToolStore()
        phone_store.add_contact(
            Contact(
                contact_id="contact-alice",
                display_name="Alice Chen",
                aliases=["Alice"],
            )
        )
        phone_store.add_message_thread(
            MessageThread(
                thread_id="thread-alice",
                participant_contact_ids=["contact-alice", "self"],
            )
        )
        provider = CombinedToolProvider(
            memory_tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
            phone_tools=PhoneToolRegistry(phone_store),
        )
        runtime = AgentRuntime(
            client=FakeLLMClient(
                [
                    LLMResponse(
                        text="",
                        tool_calls=[
                            ToolCall(
                                call_id="call-1",
                                name="search_contacts",
                                arguments={"query": "Alice"},
                            )
                        ],
                    ),
                    LLMResponse(
                        text="",
                        tool_calls=[
                            ToolCall(
                                call_id="call-2",
                                name="draft_message",
                                arguments={
                                    "thread_id": "thread-alice",
                                    "recipient_contact_ids": ["contact-alice"],
                                    "text": "Friday afternoon works.",
                                },
                            )
                        ],
                    ),
                    LLMResponse(text="I drafted the message."),
                ]
            ),
            model="fake-model",
            tools=provider,
        )

        response = runtime.run_turn("Find Alice and draft a reply.")

        self.assertEqual(response.text, "I drafted the message.")
        self.assertEqual([result["name"] for result in response.tool_results], ["search_contacts", "draft_message"])
        self.assertEqual(response.tool_results[0]["provider"], "phone")
        self.assertEqual(response.tool_results[1]["provider"], "phone")
        self.assertEqual(phone_store.list_message_drafts()[0].text, "Friday afternoon works.")

    def test_tool_execution_errors_are_returned_as_tool_results(self) -> None:
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
                                arguments={"title": "Broken event", "start_at": "not-a-date"},
                            )
                        ],
                    ),
                    LLMResponse(text="I need a valid start and end time."),
                ]
            ),
            model="fake-model",
            tools=provider,
        )

        response = runtime.run_turn("Schedule this.")

        self.assertEqual(response.text, "I need a valid start and end time.")
        self.assertEqual(response.tool_results[0]["provider"], "error")
        self.assertIn("error", response.tool_results[0]["result"])


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


def _seeded_phone_store() -> InMemoryPhoneToolStore:
    store = InMemoryPhoneToolStore()
    seed_research_phone_state(store)
    return store
