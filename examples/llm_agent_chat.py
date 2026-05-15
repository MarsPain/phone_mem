from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
from typing import Protocol, TextIO

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from phone_mem.agent_runtime.openai_client import OpenAICompatibleClient, OpenAICompatibleRequestError
from phone_mem.agent_runtime.runtime import AgentRuntime, AgentTurnResponse
from phone_mem.agent_runtime.session import AgentSession
from phone_mem.agent_runtime.tool_provider import CombinedToolProvider
from phone_mem.agent_runtime.tools import MemoryToolRegistry
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.events import (
    AuditOperation,
    MemoryLayer,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService
from phone_mem.phone_tools.in_memory_store import InMemoryPhoneToolStore
from phone_mem.phone_tools.registry import PhoneToolRegistry
from phone_mem.phone_tools.seed import seed_research_phone_state


CALLER = "llm_memory_agent"
SOURCE_APP = "system_assistant"


class RuntimeLike(Protocol):
    def run_turn(self, user_message: str) -> AgentTurnResponse:
        raise NotImplementedError


def run_chat(
    *,
    runtime: RuntimeLike | None = None,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> None:
    resolved_input = input_stream or sys.stdin
    resolved_output = output_stream or sys.stdout
    owned_service: PersonalMemoryService | None = None
    resolved_runtime = runtime
    if resolved_runtime is None:
        owned_service = _service_with_grant()
        resolved_runtime = AgentSession(_runtime_from_env(owned_service))

    try:
        print("Phone Memory LLM Agent", file=resolved_output)
        print("Type 'quit' to exit.", file=resolved_output)
        for raw_line in resolved_input:
            user_message = raw_line.strip()
            if not user_message:
                continue
            if user_message in {"quit", "exit"}:
                print("bye", file=resolved_output)
                return
            try:
                response = resolved_runtime.run_turn(user_message)
            except OpenAICompatibleRequestError as exc:
                print(f"error: {exc}", file=resolved_output)
                continue
            print(response.text, file=resolved_output)
            print(f"evidence: {response.evidence_event_ids}", file=resolved_output)
    finally:
        if owned_service is not None:
            owned_service.close()


def _runtime_from_env(service: PersonalMemoryService) -> AgentRuntime:
    model = os.environ.get("PHONE_MEM_LLM_MODEL", "gpt-4.1")
    memory_tools = MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP)
    phone_store = InMemoryPhoneToolStore()
    seed_research_phone_state(phone_store)
    phone_tools = PhoneToolRegistry(phone_store)
    return AgentRuntime(
        client=OpenAICompatibleClient.from_env(),
        model=model,
        thinking=_thinking_from_env(),
        tools=CombinedToolProvider(memory_tools=memory_tools, phone_tools=phone_tools),
    )


def _thinking_from_env() -> dict[str, object]:
    raw_value = os.environ.get("PHONE_MEM_LLM_THINKING", "disabled").strip()
    if raw_value.startswith("{"):
        parsed = json.loads(raw_value)
        if not isinstance(parsed, dict):
            raise ValueError("PHONE_MEM_LLM_THINKING JSON must decode to an object")
        return parsed

    normalized = raw_value.lower()
    if normalized in {"", "0", "false", "no", "off", "disabled"}:
        return {"type": "disabled"}
    if normalized in {"1", "true", "yes", "on", "enabled"}:
        thinking: dict[str, object] = {"type": "enabled"}
        budget_tokens = os.environ.get("PHONE_MEM_LLM_THINKING_BUDGET_TOKENS", "").strip()
        if budget_tokens:
            thinking["budget_tokens"] = int(budget_tokens)
        return thinking
    raise ValueError("PHONE_MEM_LLM_THINKING must be disabled, enabled, or a JSON object")


def _service_with_grant() -> PersonalMemoryService:
    now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
    service = PersonalMemoryService.in_memory(clock=lambda: now)
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
    run_chat()
