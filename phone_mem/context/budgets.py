from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextBudget:
    max_tokens: int
    safety_reserve_tokens: int = 0
    output_reserve_tokens: int = 0
    tool_reserve_tokens: int = 0

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if self.available_memory_tokens < 0:
            raise ValueError("context reserves cannot exceed max_tokens")

    @property
    def available_memory_tokens(self) -> int:
        return (
            self.max_tokens
            - self.safety_reserve_tokens
            - self.output_reserve_tokens
            - self.tool_reserve_tokens
        )
