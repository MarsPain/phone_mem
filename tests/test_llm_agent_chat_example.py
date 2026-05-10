from __future__ import annotations

from io import StringIO
import unittest
from unittest.mock import patch

from examples.llm_agent_chat import _runtime_from_env, run_chat
from phone_mem.agent_runtime.client import FakeLLMClient, LLMResponse
from phone_mem.agent_runtime.openai_client import OpenAICompatibleClient
from phone_mem.agent_runtime.openai_client import OpenAICompatibleRequestError
from phone_mem.agent_runtime.runtime import AgentRuntime, AgentTurnResponse
from phone_mem.agent_runtime.tools import MemoryToolRegistry


class ScriptedRuntime:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def run_turn(self, user_message: str) -> AgentTurnResponse:
        self.messages.append(user_message)
        return AgentTurnResponse(
            text="Use morning planning. [memory: event-1]",
            evidence_event_ids=["event-1"],
        )


class FailingRuntime:
    def run_turn(self, user_message: str) -> AgentTurnResponse:
        raise OpenAICompatibleRequestError("LLM API request failed: TLS handshake failed")


class LlmAgentChatExampleTest(unittest.TestCase):
    def test_run_chat_accepts_injected_runtime_without_provider_credentials(self) -> None:
        runtime = ScriptedRuntime()
        input_stream = StringIO("Plan my morning planning session.\nquit\n")
        output_stream = StringIO()

        run_chat(runtime=runtime, input_stream=input_stream, output_stream=output_stream)

        output = output_stream.getvalue()
        self.assertIn("Phone Memory LLM Agent", output)
        self.assertIn("Use morning planning. [memory: event-1]", output)
        self.assertIn("evidence: ['event-1']", output)
        self.assertIn("bye", output)
        self.assertEqual(runtime.messages, ["Plan my morning planning session."])

    def test_run_chat_default_runtime_uses_session_history(self) -> None:
        client = FakeLLMClient(
            [
                LLMResponse(text="We can prepare a checklist first."),
                LLMResponse(text="Continuing from the checklist."),
            ]
        )

        def runtime_factory(service: object) -> AgentRuntime:
            return AgentRuntime(
                client=client,
                model="fake-memory-model",
                tools=MemoryToolRegistry(
                    service=service,  # type: ignore[arg-type]
                    caller="llm_memory_agent",
                    source_app="system_assistant",
                ),
            )

        input_stream = StringIO("Let's plan the launch review.\nContinue that.\nquit\n")
        output_stream = StringIO()

        with patch("examples.llm_agent_chat._runtime_from_env", side_effect=runtime_factory):
            run_chat(input_stream=input_stream, output_stream=output_stream)

        request_text = "\n".join(message.content for message in client.requests[1].messages)
        self.assertIn("Transient conversation context", request_text)
        self.assertIn("user: Let's plan the launch review.", request_text)
        self.assertIn("assistant: We can prepare a checklist first.", request_text)

    def test_runtime_from_env_defaults_thinking_to_disabled(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            runtime = _runtime_from_env(service=object())  # type: ignore[arg-type]

        self.assertIsInstance(runtime.client, OpenAICompatibleClient)
        self.assertEqual(runtime.model, "gpt-4.1")
        self.assertEqual(runtime.thinking, {"type": "disabled"})

    def test_run_chat_prints_provider_request_errors_without_traceback(self) -> None:
        input_stream = StringIO("Plan my morning planning session.\nquit\n")
        output_stream = StringIO()

        run_chat(runtime=FailingRuntime(), input_stream=input_stream, output_stream=output_stream)

        output = output_stream.getvalue()
        self.assertIn("error: LLM API request failed: TLS handshake failed", output)
        self.assertIn("bye", output)


if __name__ == "__main__":
    unittest.main()
