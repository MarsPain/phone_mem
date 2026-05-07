from __future__ import annotations

from math import ceil
from typing import Protocol


class TokenCounter(Protocol):
    def count(self, text: str) -> int:
        pass


class ConservativeTokenCounter:
    def __init__(
        self,
        *,
        ascii_chars_per_token: float = 3.5,
        non_ascii_chars_per_token: float = 1.0,
        safety_multiplier: float = 1.3,
        overhead_tokens: int = 8,
    ) -> None:
        self._ascii_chars_per_token = ascii_chars_per_token
        self._non_ascii_chars_per_token = non_ascii_chars_per_token
        self._safety_multiplier = safety_multiplier
        self._overhead_tokens = overhead_tokens

    def count(self, text: str) -> int:
        if not text:
            return 0
        ascii_chars = sum(1 for character in text if ord(character) < 128)
        non_ascii_chars = len(text) - ascii_chars
        estimate = (
            ascii_chars / self._ascii_chars_per_token
            + non_ascii_chars / self._non_ascii_chars_per_token
        )
        return ceil(estimate * self._safety_multiplier) + self._overhead_tokens
