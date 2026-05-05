from __future__ import annotations

from collections.abc import Callable
import json
import os
from typing import Any
from urllib import error, request

from phone_mem.agent_runtime.client import LLMRequest, LLMResponse, ToolCall, ToolDefinition


Transport = Callable[[str, dict[str, str], dict[str, object]], dict[str, object]]


class OpenAICompatibleConfigurationError(RuntimeError):
    pass


class OpenAICompatibleRequestError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        transport: Transport | None = None,
    ) -> None:
        if not api_key.strip():
            raise OpenAICompatibleConfigurationError("OPENAI_API_KEY is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._transport = transport or _post_json

    @classmethod
    def from_env(cls) -> OpenAICompatibleClient:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("PHONE_MEM_LLM_BASE_URL", "https://api.openai.com/v1")
        return cls(api_key=api_key, base_url=base_url)

    def complete(self, request_data: LLMRequest) -> LLMResponse:
        payload = {
            "model": request_data.model,
            "messages": [message.to_dict() for message in request_data.messages],
        }
        if request_data.thinking is not None:
            payload["thinking"] = dict(request_data.thinking)
        if request_data.tools:
            payload["tools"] = [_tool_payload(tool) for tool in request_data.tools]

        url = f"{self._base_url}/chat/completions"
        try:
            raw = self._transport(
                url,
                {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                payload,
            )
        except OpenAICompatibleRequestError:
            raise
        except error.HTTPError as exc:
            detail = _http_error_detail(exc)
            raise OpenAICompatibleRequestError(
                f"LLM API request failed for {url}: HTTP {exc.code}: {detail}"
            ) from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            raise OpenAICompatibleRequestError(f"LLM API request failed for {url}: {exc}") from exc
        return _parse_chat_completion(raw)


def _tool_payload(tool: ToolDefinition) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


def _parse_chat_completion(raw: dict[str, object]) -> LLMResponse:
    choices = raw.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("OpenAI-compatible response did not include choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise RuntimeError("OpenAI-compatible response choice was invalid")
    message = first_choice.get("message", {})
    if not isinstance(message, dict):
        raise RuntimeError("OpenAI-compatible response message was invalid")
    return LLMResponse(
        text=str(message.get("content") or ""),
        tool_calls=_parse_tool_calls(message.get("tool_calls")),
        raw=raw,
    )


def _parse_tool_calls(raw_tool_calls: object) -> list[ToolCall]:
    if not isinstance(raw_tool_calls, list):
        return []
    tool_calls: list[ToolCall] = []
    for raw_call in raw_tool_calls:
        if not isinstance(raw_call, dict):
            continue
        function = raw_call.get("function", {})
        if not isinstance(function, dict):
            continue
        tool_calls.append(
            ToolCall(
                call_id=str(raw_call.get("id", "")),
                name=str(function.get("name", "")),
                arguments=_parse_arguments(function.get("arguments")),
            )
        )
    return tool_calls


def _parse_arguments(raw_arguments: object) -> dict[str, Any]:
    if not isinstance(raw_arguments, str) or not raw_arguments:
        return {}
    parsed = json.loads(raw_arguments)
    if not isinstance(parsed, dict):
        raise RuntimeError("tool call arguments must decode to a JSON object")
    return parsed


def _http_error_detail(exc: error.HTTPError) -> str:
    raw_body = exc.read().decode("utf-8", errors="replace").strip()
    if raw_body:
        return raw_body
    return str(exc.reason)


def _post_json(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=60) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, dict):
        raise RuntimeError("OpenAI-compatible response must be a JSON object")
    return decoded
