from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

from phone_mem.personal_memory_service.errors import MemoryEventNotFound, MemoryPermissionDenied


@dataclass(frozen=True)
class ChatTurnRequest:
    message: str


@dataclass(frozen=True)
class TurnSnapshot:
    index: int
    user_message: str
    response_text: str
    evidence_event_ids: list[str]
    memory_context: dict[str, Any] | None
    tool_results: list[dict[str, Any]]
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ErrorPayload:
    type: str
    message: str
    operation: str | None = None
    caller: str | None = None
    event_id: str | None = None
    affected_event_ids: list[str] = field(default_factory=list)
    denial_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ok_payload(**values: Any) -> dict[str, Any]:
    return {"ok": True, **to_jsonable(values)}


def error_payload(error: Exception) -> dict[str, Any]:
    return {"ok": False, "error": serialize_error(error)}


def serialize_error(error: Exception) -> dict[str, Any]:
    if isinstance(error, MemoryEventNotFound):
        return ErrorPayload(
            type=type(error).__name__,
            message=str(error),
            operation=error.operation.value,
            caller=error.caller,
            event_id=error.event_id,
            affected_event_ids=error.affected_event_ids,
            denial_reason=error.denial_reason,
        ).to_dict()
    if isinstance(error, MemoryPermissionDenied):
        return ErrorPayload(
            type=type(error).__name__,
            message=str(error),
            operation=error.operation.value,
            caller=error.caller,
            affected_event_ids=error.affected_event_ids,
            denial_reason=error.denial_reason,
        ).to_dict()
    return ErrorPayload(type=type(error).__name__, message=str(error)).to_dict()


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "to_dict"):
        return to_jsonable(value.to_dict())
    return value
