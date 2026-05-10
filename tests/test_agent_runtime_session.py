from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.agent_runtime.client import FakeLLMClient, LLMResponse
from phone_mem.agent_runtime.runtime import AgentRuntime
from phone_mem.agent_runtime.session import AgentSession
from phone_mem.agent_runtime.tools import MemoryToolRegistry
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.events import AuditOperation, MemoryLayer, PrivacyLevel
from phone_mem.personal_memory_service.service import PersonalMemoryService


CALLER = "session_agent"
SOURCE_APP = "system_assistant"


class AgentRuntimeSessionTest(unittest.TestCase):
    def test_first_turn_sends_no_transient_conversation_context(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        client = FakeLLMClient([LLMResponse(text="First answer.")])
        session = AgentSession(_runtime(client, service))

        session.run_turn("Start a launch plan.")

        request_text = "\n".join(message.content for message in client.requests[0].messages)
        self.assertNotIn("Transient conversation context", request_text)

    def test_second_turn_sends_previous_user_and_assistant_messages(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        client = FakeLLMClient(
            [
                LLMResponse(text="We can prepare a checklist first."),
                LLMResponse(text="Continuing from the checklist."),
            ]
        )
        session = AgentSession(_runtime(client, service))

        session.run_turn("Let's plan the launch review.")
        session.run_turn("Continue that.")

        request_text = "\n".join(message.content for message in client.requests[1].messages)
        self.assertIn("Transient conversation context", request_text)
        self.assertIn("user: Let's plan the launch review.", request_text)
        self.assertIn("assistant: We can prepare a checklist first.", request_text)

    def test_session_history_window_keeps_recent_messages_only(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        client = FakeLLMClient(
            [
                LLMResponse(text="Answer one."),
                LLMResponse(text="Answer two."),
                LLMResponse(text="Answer three."),
            ]
        )
        session = AgentSession(_runtime(client, service), max_history_messages=2)

        session.run_turn("Question one.")
        session.run_turn("Question two.")
        session.run_turn("Question three.")

        request_text = "\n".join(message.content for message in client.requests[2].messages)
        self.assertNotIn("Question one.", request_text)
        self.assertNotIn("Answer one.", request_text)
        self.assertIn("user: Question two.", request_text)
        self.assertIn("assistant: Answer two.", request_text)


def _runtime(client: FakeLLMClient, service: PersonalMemoryService) -> AgentRuntime:
    return AgentRuntime(
        client=client,
        model="fake-memory-model",
        tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
    )


def _service_with_grant() -> PersonalMemoryService:
    service = PersonalMemoryService.in_memory(clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC))
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


if __name__ == "__main__":
    unittest.main()
