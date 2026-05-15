from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolObservation:
    tool_name: str
    text: str
    capture_worthy: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "text": self.text,
            "capture_worthy": self.capture_worthy,
            "metadata": dict(self.metadata),
        }
