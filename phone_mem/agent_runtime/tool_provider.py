from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from phone_mem.agent_runtime.client import ToolDefinition
from phone_mem.agent_runtime.tools import MemoryToolRegistry
from phone_mem.phone_tools.observations import ToolObservation

if TYPE_CHECKING:
    from phone_mem.phone_tools.registry import PhoneToolRegistry, PhoneToolResult


@dataclass(frozen=True)
class ToolExecutionRecord:
    call_id: str
    provider: str
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    observation: ToolObservation
    capture_worthy: bool
    evidence_event_ids: list[str]


@dataclass(frozen=True)
class CombinedToolProvider:
    memory_tools: MemoryToolRegistry
    phone_tools: PhoneToolRegistry | None = None

    @property
    def source_app(self) -> str:
        return self.memory_tools.source_app

    def build_memory_context(self, query: str, *, max_tokens: int = 160) -> dict[str, Any]:
        return self.memory_tools.build_memory_context(query, max_tokens=max_tokens)

    def record_candidate(self, candidate: Any) -> dict[str, str]:
        return self.memory_tools.record_candidate(candidate)

    def tool_definitions(self) -> list[ToolDefinition]:
        definitions = list(self.memory_tools.tool_definitions())
        if self.phone_tools is not None:
            definitions.extend(self.phone_tools.tool_definitions())
        return definitions

    def execute(self, call_id: str, name: str, arguments: dict[str, Any]) -> ToolExecutionRecord:
        from phone_mem.phone_tools.registry import PhoneToolRegistry, PhoneToolResult
        try:
            result = self.memory_tools.execute(name, arguments)
            return ToolExecutionRecord(
                call_id=call_id,
                provider="memory",
                name=name,
                arguments=arguments,
                result=result,
                observation=ToolObservation(
                    tool_name=name,
                    text=f"Executed memory tool {name}.",
                    capture_worthy=False,
                ),
                capture_worthy=False,
                evidence_event_ids=_extract_evidence_event_ids(result),
            )
        except ValueError as exc:
            if "unknown memory tool" not in str(exc):
                raise
        if self.phone_tools is not None:
            phone_result = self.phone_tools.execute(name, arguments)
            return ToolExecutionRecord(
                call_id=call_id,
                provider="phone",
                name=name,
                arguments=arguments,
                result=phone_result.result,
                observation=phone_result.observation,
                capture_worthy=phone_result.observation.capture_worthy,
                evidence_event_ids=_extract_evidence_event_ids(phone_result.result),
            )
        raise ValueError(f"unknown tool: {name}")


def _extract_evidence_event_ids(result: dict[str, Any]) -> list[str]:
    event_ids: list[str] = []
    if "event_id" in result:
        event_ids.append(result["event_id"])
    event_ids.extend(result.get("evidence_event_ids", []))
    event_ids.extend(result.get("deleted_event_ids", []))
    return event_ids


def normalize_tools(tools: MemoryToolRegistry | CombinedToolProvider) -> CombinedToolProvider:
    if isinstance(tools, CombinedToolProvider):
        return tools
    return CombinedToolProvider(memory_tools=tools, phone_tools=None)
