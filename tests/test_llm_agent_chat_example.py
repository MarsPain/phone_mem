from __future__ import annotations

from io import StringIO
import unittest

from examples.llm_agent_chat import run_chat
from phone_mem.agent_runtime.runtime import AgentTurnResponse


class ScriptedRuntime:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def run_turn(self, user_message: str) -> AgentTurnResponse:
        self.messages.append(user_message)
        return AgentTurnResponse(
            text="Use morning planning. [memory: event-1]",
            evidence_event_ids=["event-1"],
        )


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


if __name__ == "__main__":
    unittest.main()
