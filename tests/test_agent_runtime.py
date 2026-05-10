from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.agent_runtime.client import FakeLLMClient, LLMMessage, LLMResponse, ToolCall
from phone_mem.agent_runtime.runtime import AgentRuntime
from phone_mem.agent_runtime.session_capture import SessionCapture, SessionCaptureInput
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
        self.assertIsNotNone(response.memory_context)
        assert response.memory_context is not None
        self.assertEqual(response.memory_context["evidence_event_ids"], ["event-1"])
        self.assertEqual(
            response.memory_context["snippets"][0]["text"],
            "User prefers morning planning sessions.",
        )
        self.assertEqual(len(client.requests), 1)
        request_text = "\n".join(message.content for message in client.requests[0].messages)
        self.assertIn("User prefers morning planning sessions.", request_text)
        self.assertIn("event-1", request_text)

    def test_chat_turn_forwards_thinking_config_to_llm_requests(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        client = FakeLLMClient([LLMResponse(text="Done.")])
        runtime = AgentRuntime(
            client=client,
            model="fake-memory-model",
            thinking={"type": "disabled"},
            tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
        )

        runtime.run_turn("Plan my day.")

        self.assertEqual(client.requests[0].thinking, {"type": "disabled"})

    def test_chat_turn_forwards_recent_conversation_to_llm_request(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        client = FakeLLMClient([LLMResponse(text="Continue from the checklist.")])
        runtime = AgentRuntime(
            client=client,
            model="fake-memory-model",
            tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
        )

        runtime.run_turn(
            "Continue that.",
            conversation_messages=[
                LLMMessage(role="user", content="Let's plan the launch review."),
                LLMMessage(role="assistant", content="We can prepare a checklist first."),
            ],
        )

        request_text = "\n".join(message.content for message in client.requests[0].messages)
        self.assertIn("Transient conversation context", request_text)
        self.assertIn("user: Let's plan the launch review.", request_text)
        self.assertIn("assistant: We can prepare a checklist first.", request_text)

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
        self.assertIsNotNone(response.memory_context)
        assert response.memory_context is not None
        self.assertEqual(response.memory_context["evidence_event_ids"], [])
        self.assertEqual(response.memory_context["snippets"], [])
        self.assertEqual(response.tool_results[0]["result"]["event_id"], "event-1")
        self.assertEqual(service.search("Friday retrospectives", caller=CALLER)[0].event_id, "event-1")
        self.assertEqual(len(client.requests), 2)
        final_request_text = "\n".join(message.content for message in client.requests[1].messages)
        self.assertIn("Tool results:", final_request_text)
        self.assertIn("event-1", final_request_text)

    def test_session_capture_flushes_user_correction_as_governed_episodic_memory(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        client = FakeLLMClient([LLMResponse(text="I updated that preference.")])
        runtime = AgentRuntime(
            client=client,
            model="fake-memory-model",
            tools=MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP),
            session_capture=SessionCapture(),
        )

        response = runtime.run_turn("Actually, I prefer afternoon planning sessions.")

        self.assertEqual(response.captured_event_ids, ["event-1"])
        captured_event = service.store.get_event("event-1")
        assert captured_event is not None
        self.assertEqual(captured_event.memory_layer, MemoryLayer.EPISODIC)
        self.assertIn(
            {"type": "capture_trigger", "value": "user_correction"},
            captured_event.relations,
        )
        audit_operations = [record.operation for record in service.audit()]
        self.assertIn(AuditOperation.WRITE, audit_operations)

    def test_session_capture_rejects_empty_inputs_and_deduplicates_repeated_captures(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        tools = MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP)
        capture = SessionCapture()

        empty = capture.flush(
            SessionCaptureInput(trigger="turn_boundary", transcript_summary="  "),
            tools=tools,
        )
        first = capture.flush(
            SessionCaptureInput(
                trigger="task_boundary",
                transcript_summary="User decided to move the launch review to Friday.",
                task_state={"project": "launch review"},
            ),
            tools=tools,
        )
        duplicate = capture.flush(
            SessionCaptureInput(
                trigger="task_boundary",
                transcript_summary="User decided to move the launch review to Friday.",
                task_state={"project": "launch review"},
            ),
            tools=tools,
        )

        self.assertEqual(empty, [])
        self.assertEqual(first, ["event-1"])
        self.assertEqual(duplicate, [])
        self.assertEqual(len(service.search("launch review Friday", caller=CALLER)), 1)

    def test_session_capture_quarantines_contradictory_corrections_through_service_lifecycle(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        tools = MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP)
        capture = SessionCapture()
        tools.remember("User prefers morning planning sessions.", entities=["planning sessions"])

        captured = capture.flush(
            SessionCaptureInput(
                trigger="user_correction",
                user_correction="User prefers afternoon planning sessions.",
                entities=["planning sessions"],
            ),
            tools=tools,
        )

        self.assertEqual(captured, ["event-2"])
        explanation = service.explain("event-2", caller=CALLER)
        self.assertEqual(explanation["lifecycle"]["state"], "quarantined")


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
