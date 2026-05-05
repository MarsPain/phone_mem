from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from phone_mem.agent_runtime.client import LLMClient, LLMMessage, LLMRequest
from phone_mem.agent_runtime.prompts import build_agent_messages
from phone_mem.agent_runtime.tools import MemoryToolRegistry


@dataclass(frozen=True)
class AgentTurnResponse:
    text: str
    evidence_event_ids: list[str]
    tool_results: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class AgentRuntime:
    client: LLMClient
    model: str
    tools: MemoryToolRegistry

    def run_turn(self, user_message: str) -> AgentTurnResponse:
        memory_context = self.tools.build_memory_context(user_message)
        initial_messages = build_agent_messages(
            user_message=user_message,
            memory_context=memory_context,
        )
        initial_response = self.client.complete(
            LLMRequest(
                model=self.model,
                messages=initial_messages,
                tools=self.tools.tool_definitions(),
            )
        )
        if not initial_response.has_tool_calls:
            return AgentTurnResponse(
                text=initial_response.text,
                evidence_event_ids=_dedupe(
                    [
                        *memory_context["evidence_event_ids"],
                        *initial_response.evidence_event_ids,
                    ]
                ),
            )

        tool_results = [
            {
                "call_id": call.call_id,
                "name": call.name,
                "result": self.tools.execute(call.name, call.arguments),
            }
            for call in initial_response.tool_calls
        ]
        final_response = self.client.complete(
            LLMRequest(
                model=self.model,
                messages=[
                    *initial_messages,
                    LLMMessage(role="assistant", content=_tool_call_summary(tool_results)),
                    LLMMessage(role="user", content="Use the tool results to answer the user."),
                ],
                tools=self.tools.tool_definitions(),
            )
        )
        return AgentTurnResponse(
            text=final_response.text,
            evidence_event_ids=_dedupe(
                [
                    *memory_context["evidence_event_ids"],
                    *_tool_evidence_event_ids(tool_results),
                    *final_response.evidence_event_ids,
                ]
            ),
            tool_results=tool_results,
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


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
