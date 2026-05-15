from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from phone_mem.agent_runtime.client import LLMClient, LLMMessage, LLMRequest
from phone_mem.agent_runtime.prompts import build_agent_messages
from phone_mem.agent_runtime.session_capture import SessionCapture, SessionCaptureInput
from phone_mem.agent_runtime.tool_provider import CombinedToolProvider, ToolExecutionRecord, normalize_tools
from phone_mem.agent_runtime.tools import MemoryToolRegistry
from phone_mem.phone_tools.observations import ToolObservation


@dataclass(frozen=True)
class AgentTurnResponse:
    text: str
    evidence_event_ids: list[str]
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    memory_context: dict[str, Any] | None = None
    captured_event_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AgentRuntime:
    client: LLMClient
    model: str
    tools: MemoryToolRegistry | CombinedToolProvider
    thinking: dict[str, Any] | None = None
    session_capture: SessionCapture = field(default_factory=SessionCapture)
    max_tool_iterations: int = 4

    def run_turn(
        self,
        user_message: str,
        conversation_messages: list[LLMMessage] | None = None,
    ) -> AgentTurnResponse:
        tools = normalize_tools(self.tools)
        memory_context = tools.build_memory_context(user_message)
        initial_messages = build_agent_messages(
            user_message=user_message,
            memory_context=memory_context,
            recent_conversation=conversation_messages,
        )
        initial_response = self.client.complete(
            LLMRequest(
                model=self.model,
                messages=initial_messages,
                thinking=self.thinking,
                tools=tools.tool_definitions(),
            )
        )
        if not initial_response.has_tool_calls:
            captured_event_ids = self._flush_session_capture(
                user_message=user_message,
                assistant_text=initial_response.text,
                tool_results=[],
                tools=tools,
            )
            return AgentTurnResponse(
                text=initial_response.text,
                evidence_event_ids=_dedupe(
                    [
                        *memory_context["evidence_event_ids"],
                        *initial_response.evidence_event_ids,
                    ]
                ),
                memory_context=memory_context,
                captured_event_ids=captured_event_ids,
            )

        messages = list(initial_messages)
        current_response = initial_response
        response_evidence_event_ids = list(initial_response.evidence_event_ids)
        tool_results: list[dict[str, Any]] = []
        for _ in range(max(self.max_tool_iterations, 0)):
            if not current_response.has_tool_calls:
                break
            execution_records = [
                _execute_tool_call(tools, call.call_id, call.name, call.arguments)
                for call in current_response.tool_calls
            ]
            iteration_tool_results = [
                _serialize_execution_record(record) for record in execution_records
            ]
            tool_results.extend(iteration_tool_results)
            messages = [
                *messages,
                LLMMessage(role="assistant", content=_tool_call_summary(iteration_tool_results)),
                LLMMessage(role="user", content="Use the tool results to answer the user."),
            ]
            current_response = self.client.complete(
                LLMRequest(
                    model=self.model,
                    messages=messages,
                    thinking=self.thinking,
                    tools=tools.tool_definitions(),
                )
            )
            response_evidence_event_ids.extend(current_response.evidence_event_ids)
        else:
            if current_response.has_tool_calls:
                tool_results.append(
                    _serialize_execution_record(
                        _error_execution_record(
                            call_id="tool-loop-limit",
                            name="tool_loop",
                            arguments={},
                            error=RuntimeError("maximum tool iterations reached"),
                        )
                    )
                )

        captured_event_ids = self._flush_session_capture(
            user_message=user_message,
            assistant_text=current_response.text,
            tool_results=tool_results,
            tools=tools,
        )
        return AgentTurnResponse(
            text=current_response.text,
            evidence_event_ids=_dedupe(
                [
                    *memory_context["evidence_event_ids"],
                    *_tool_evidence_event_ids(tool_results),
                    *response_evidence_event_ids,
                ]
            ),
            tool_results=tool_results,
            memory_context=memory_context,
            captured_event_ids=captured_event_ids,
        )

    def _flush_session_capture(
        self,
        *,
        user_message: str,
        assistant_text: str,
        tool_results: list[dict[str, Any]],
        tools: CombinedToolProvider,
    ) -> list[str]:
        return self.session_capture.flush(
            SessionCaptureInput(
                trigger="turn_boundary",
                user_message=user_message,
                assistant_text=assistant_text,
                tool_observations=_tool_observations(tool_results),
            ),
            tools=tools,
        )


def _serialize_execution_record(record: Any) -> dict[str, Any]:
    return {
        "call_id": record.call_id,
        "provider": record.provider,
        "name": record.name,
        "arguments": record.arguments,
        "result": record.result,
        "observation": record.observation.to_dict(),
        "capture_worthy": record.capture_worthy,
        "evidence_event_ids": list(record.evidence_event_ids),
    }


def _execute_tool_call(
    tools: CombinedToolProvider,
    call_id: str,
    name: str,
    arguments: dict[str, Any],
) -> ToolExecutionRecord:
    try:
        return tools.execute(call_id, name, arguments)
    except Exception as exc:
        return _error_execution_record(
            call_id=call_id,
            name=name,
            arguments=arguments,
            error=exc,
        )


def _error_execution_record(
    *,
    call_id: str,
    name: str,
    arguments: dict[str, Any],
    error: Exception,
) -> ToolExecutionRecord:
    message = str(error) or type(error).__name__
    return ToolExecutionRecord(
        call_id=call_id,
        provider="error",
        name=name,
        arguments=arguments,
        result={"error": message, "error_type": type(error).__name__},
        observation=ToolObservation(
            tool_name=name,
            text=f"{name} error: {message}",
            capture_worthy=False,
        ),
        capture_worthy=False,
        evidence_event_ids=[],
    )


def _tool_call_summary(tool_results: list[dict[str, Any]]) -> str:
    return "Tool results:\n" + json.dumps(tool_results, sort_keys=True)


def _tool_evidence_event_ids(tool_results: list[dict[str, Any]]) -> list[str]:
    event_ids: list[str] = []
    for tool_result in tool_results:
        result = tool_result["result"]
        if "event_id" in result:
            event_ids.append(result["event_id"])
        event_ids.extend(result.get("evidence_event_ids", []))
        event_ids.extend(result.get("deleted_event_ids", []))
    return event_ids


def _tool_observations(tool_results: list[dict[str, Any]]) -> list[str]:
    observations: list[str] = []
    for tool_result in tool_results:
        result = tool_result.get("result", {})
        if "error" in result:
            observations.append(f"{tool_result['name']} error: {result['error']}")
        observation = tool_result.get("observation")
        if observation and observation.get("capture_worthy"):
            observations.append(observation["text"])
    return observations


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
