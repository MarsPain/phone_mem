from __future__ import annotations

from dataclasses import dataclass, field

from phone_mem.agent_runtime.client import LLMMessage
from phone_mem.agent_runtime.runtime import AgentRuntime, AgentTurnResponse


@dataclass
class AgentSession:
    runtime: AgentRuntime
    max_history_messages: int = 8
    _history: list[LLMMessage] = field(default_factory=list)

    def run_turn(self, user_message: str) -> AgentTurnResponse:
        response = self.runtime.run_turn(
            user_message,
            conversation_messages=self._recent_history(),
        )
        self._history.extend(
            [
                LLMMessage(role="user", content=user_message),
                LLMMessage(role="assistant", content=response.text),
            ]
        )
        return response

    def _recent_history(self) -> list[LLMMessage]:
        if self.max_history_messages <= 0:
            return []
        return list(self._history[-self.max_history_messages :])
