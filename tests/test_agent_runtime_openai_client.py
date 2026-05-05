from __future__ import annotations

import os
import unittest
from urllib.error import URLError
from unittest.mock import patch

from phone_mem.agent_runtime.client import LLMMessage, LLMRequest, ToolDefinition
from phone_mem.agent_runtime.openai_client import (
    OpenAICompatibleClient,
    OpenAICompatibleConfigurationError,
    OpenAICompatibleRequestError,
)


class AgentRuntimeOpenAICompatibleClientTest(unittest.TestCase):
    def test_from_env_requires_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(OpenAICompatibleConfigurationError, "OPENAI_API_KEY"):
                OpenAICompatibleClient.from_env()

    def test_complete_posts_chat_completion_payload_and_parses_response(self) -> None:
        captured: dict[str, object] = {}

        def transport(
            url: str,
            headers: dict[str, str],
            payload: dict[str, object],
        ) -> dict[str, object]:
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = payload
            return {
                "choices": [
                    {
                        "message": {
                            "content": "I found one memory.",
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "search_memory",
                                        "arguments": "{\"query\":\"planning\",\"top_k\":2}",
                                    },
                                }
                            ],
                        }
                    }
                ]
            }

        client = OpenAICompatibleClient(
            api_key="test-key",
            base_url="https://example.test/v1",
            transport=transport,
        )
        response = client.complete(
            LLMRequest(
                model="gpt-test",
                messages=[LLMMessage(role="user", content="Search memory.")],
                thinking={"type": "disabled"},
                tools=[
                    ToolDefinition(
                        name="search_memory",
                        description="Search memory.",
                        parameters={
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    )
                ],
            )
        )

        self.assertEqual(captured["url"], "https://example.test/v1/chat/completions")
        headers = captured["headers"]
        assert isinstance(headers, dict)
        self.assertEqual(headers["Authorization"], "Bearer test-key")
        payload = captured["payload"]
        assert isinstance(payload, dict)
        self.assertEqual(payload["model"], "gpt-test")
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(
            payload["tools"],
            [
                {
                    "type": "function",
                    "function": {
                        "name": "search_memory",
                        "description": "Search memory.",
                        "parameters": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    },
                }
            ],
        )
        self.assertEqual(response.text, "I found one memory.")
        self.assertEqual(response.tool_calls[0].name, "search_memory")
        self.assertEqual(response.tool_calls[0].arguments, {"query": "planning", "top_k": 2})

    def test_complete_wraps_transport_url_errors(self) -> None:
        def transport(
            url: str,
            headers: dict[str, str],
            payload: dict[str, object],
        ) -> dict[str, object]:
            raise URLError("[SSL: UNEXPECTED_EOF_WHILE_READING]")

        client = OpenAICompatibleClient(
            api_key="test-key",
            base_url="https://example.test/v1",
            transport=transport,
        )

        with self.assertRaisesRegex(
            OpenAICompatibleRequestError,
            "https://example.test/v1/chat/completions",
        ) as raised:
            client.complete(
                LLMRequest(
                    model="gpt-test",
                    messages=[LLMMessage(role="user", content="Search memory.")],
                )
            )

        self.assertIn("UNEXPECTED_EOF_WHILE_READING", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
