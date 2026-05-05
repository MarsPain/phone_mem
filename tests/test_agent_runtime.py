from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.agent_runtime.client import FakeLLMClient, LLMResponse, ToolCall
from phone_mem.agent_runtime.runtime import AgentRuntime
from phone_mem.agent_runtime.tools import MemoryToolRegistry
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    AuditOperation,
    MemoryLayer,
    Modality,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService


CALLER = "runtime_agent"
SOURCE_APP = "system_assistant"


class AgentRuntimeTest(unittest.TestCase):
    def test_chat_turn_uses_authorized_memory_context(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        service.record(
            MemoryCandidate(
                semantic_description="User prefers morning planning sessions.",
                source_app=SOURCE_APP,
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=Attribution.USER_STATED,
                entities=["planning"],
            ),
            caller=CALLER,
        )
        client = FakeLLMClient(
            [
                LLMResponse(
                    text="Schedule planning in the morning. [memory: event-1]",
                    evidence_event_ids=["event-1"],
                )
            ]
        )
        runtime = AgentRuntime(
            client=client,
            model="fake-memory-model",
            tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
        )

        response = runtime.run_turn("Plan my morning planning session.")

        self.assertEqual(response.text, "Schedule planning in the morning. [memory: event-1]")
        self.assertEqual(response.evidence_event_ids, ["event-1"])
        self.assertEqual(len(client.requests), 1)
        request_text = "\n".join(message.content for message in client.requests[0].messages)
        self.assertIn("User prefers morning planning sessions.", request_text)
        self.assertIn("event-1", request_text)

    def test_chat_turn_executes_memory_tool_then_requests_final_answer(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        client = FakeLLMClient(
            [
                LLMResponse(
                    text="",
                    tool_calls=[
                        ToolCall(
                            call_id="call-1",
                            name="remember",
                            arguments={
                                "text": "User prefers Friday retrospectives.",
                                "entities": ["planning"],
                            },
                        )
                    ],
                ),
                LLMResponse(
                    text="I will remember that preference. [memory: event-1]",
                    evidence_event_ids=["event-1"],
                ),
            ]
        )
        runtime = AgentRuntime(
            client=client,
            model="fake-memory-model",
            tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
        )

        response = runtime.run_turn("Remember that I prefer Friday retrospectives.")

        self.assertEqual(response.text, "I will remember that preference. [memory: event-1]")
        self.assertEqual(response.tool_results[0]["result"]["event_id"], "event-1")
        self.assertEqual(service.search("Friday retrospectives", caller=CALLER)[0].event_id, "event-1")
        self.assertEqual(len(client.requests), 2)
        final_request_text = "\n".join(message.content for message in client.requests[1].messages)
        self.assertIn("Tool results:", final_request_text)
        self.assertIn("event-1", final_request_text)


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
