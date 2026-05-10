from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

from phone_mem.agent_runtime.client import LLMClient, LLMRequest, LLMResponse
from phone_mem.agent_runtime.openai_client import (
    OpenAICompatibleClient,
    OpenAICompatibleConfigurationError,
)
from phone_mem.agent_runtime.runtime import AgentRuntime, AgentTurnResponse
from phone_mem.agent_runtime.session import AgentSession
from phone_mem.agent_runtime.tools import MemoryToolRegistry
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.events import (
    AuditOperation,
    MemoryLayer,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore
from phone_mem.web_lab.schemas import TurnSnapshot, serialize_error


DEFAULT_CALLER = "web_lab_agent"
DEFAULT_SOURCE_APP = "system_assistant"
DEFAULT_DB_PATH = Path(".phone-mem-lab") / "memory.sqlite3"
DEFAULT_MODEL = "gpt-4.1"
DEFAULT_GRANT_SECONDS = 10 * 365 * 24 * 60 * 60


class ProviderUnavailableClient:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def complete(self, request: LLMRequest) -> LLMResponse:
        raise RuntimeError(self.reason)


@dataclass
class LabState:
    service: PersonalMemoryService
    tools: MemoryToolRegistry
    runtime: AgentRuntime
    session: AgentSession
    db_path: Path
    caller: str = DEFAULT_CALLER
    source_app: str = DEFAULT_SOURCE_APP
    model: str = DEFAULT_MODEL
    provider_status: str = "real"
    turn_snapshots: list[TurnSnapshot] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        db_path: str | Path | None = None,
        client: LLMClient | None = None,
        caller: str = DEFAULT_CALLER,
        source_app: str = DEFAULT_SOURCE_APP,
        model: str | None = None,
        thinking: dict[str, Any] | None = None,
    ) -> LabState:
        resolved_db_path = Path(db_path or DEFAULT_DB_PATH)
        resolved_db_path.parent.mkdir(parents=True, exist_ok=True)
        store = SQLiteMemoryStore.connect(str(resolved_db_path))
        store.initialize_schema()
        service = PersonalMemoryService.from_store(store)
        _ensure_lab_grant(service, caller=caller, source_app=source_app)
        tools = MemoryToolRegistry(service=service, caller=caller, source_app=source_app)
        resolved_model = model or os.environ.get("PHONE_MEM_LLM_MODEL", DEFAULT_MODEL)
        resolved_client, provider_status = _resolve_client(client)
        runtime = AgentRuntime(
            client=resolved_client,
            model=resolved_model,
            thinking=thinking,
            tools=tools,
        )
        session = AgentSession(runtime)
        return cls(
            service=service,
            tools=tools,
            runtime=runtime,
            session=session,
            db_path=resolved_db_path,
            caller=caller,
            source_app=source_app,
            model=resolved_model,
            provider_status=provider_status,
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "caller": self.caller,
            "source_app": self.source_app,
            "model": self.model,
            "provider_status": self.provider_status,
            "db_path": str(self.db_path),
        }

    def run_chat_turn(self, user_message: str) -> AgentTurnResponse:
        try:
            response = self.session.run_turn(user_message)
        except Exception as exc:
            self.turn_snapshots.append(
                TurnSnapshot(
                    index=len(self.turn_snapshots) + 1,
                    user_message=user_message,
                    response_text="",
                    evidence_event_ids=[],
                    captured_event_ids=[],
                    memory_context=None,
                    tool_results=[],
                    error=serialize_error(exc),
                )
            )
            raise

        self.turn_snapshots.append(
            TurnSnapshot(
                index=len(self.turn_snapshots) + 1,
                user_message=user_message,
                response_text=response.text,
                evidence_event_ids=list(response.evidence_event_ids),
                captured_event_ids=list(response.captured_event_ids),
                memory_context=response.memory_context,
                tool_results=list(response.tool_results),
            )
        )
        return response

    def snapshots_payload(self) -> dict[str, Any]:
        return {"turns": [snapshot.to_dict() for snapshot in self.turn_snapshots]}

    def clear_chat_history(self) -> dict[str, int]:
        cleared_turns = len(self.turn_snapshots)
        self.session.clear_history()
        self.turn_snapshots.clear()
        return {"cleared_turns": cleared_turns}

    def close(self) -> None:
        self.service.close()


def _resolve_client(client: LLMClient | None) -> tuple[LLMClient, str]:
    if client is not None:
        return client, "fake"
    try:
        return OpenAICompatibleClient.from_env(), "real"
    except OpenAICompatibleConfigurationError as exc:
        return ProviderUnavailableClient(str(exc)), "unconfigured"


def _ensure_lab_grant(service: PersonalMemoryService, *, caller: str, source_app: str) -> None:
    service.grant(
        caller,
        PermissionScope(
            operations=[
                AuditOperation.WRITE,
                AuditOperation.READ,
                AuditOperation.UPDATE,
                AuditOperation.DELETE,
                AuditOperation.CONTEXT_BUILD,
            ],
            apps=[source_app],
            privacy_levels=[
                PrivacyLevel.SENSITIVE,
                PrivacyLevel.PERSONAL,
                PrivacyLevel.PUBLIC,
            ],
            memory_layers=[
                MemoryLayer.WORKING,
                MemoryLayer.EPISODIC,
                MemoryLayer.SEMANTIC,
                MemoryLayer.PROCEDURAL,
            ],
        ),
        duration_seconds=DEFAULT_GRANT_SECONDS,
    )
