from __future__ import annotations

from collections.abc import Callable
from typing import Any

from phone_mem.personal_memory_service.errors import MemoryEventNotFound, MemoryPermissionDenied
from phone_mem.personal_memory_service.events import LifecycleState, MemorySelector
from phone_mem.web_lab.schemas import error_payload, ok_payload, to_jsonable
from phone_mem.web_lab.state import LabState


class MemoryInspector:
    def __init__(self, state: LabState) -> None:
        self._state = state

    def list_memories(self, *, include_deleted: bool = False) -> dict[str, Any]:
        selector = None
        if not include_deleted:
            selector = MemorySelector(
                lifecycle_states=[
                    LifecycleState.ACTIVE,
                    LifecycleState.QUARANTINED,
                    LifecycleState.SUPERSEDED,
                ]
            )
        memories = [
            event.to_dict()
            for event in self._state.service.store.query_events(selector)
        ]
        return ok_payload(memories=memories)

    def search(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        return self._guard(lambda: ok_payload(**self._state.tools.search_memory(query, top_k=top_k)))

    def preview_context(self, query: str, *, max_tokens: int = 160) -> dict[str, Any]:
        return self._guard(
            lambda: ok_payload(**self._state.tools.build_memory_context(query, max_tokens=max_tokens))
        )

    def explain(self, event_id: str) -> dict[str, Any]:
        return self._guard(lambda: ok_payload(**self._state.tools.explain_memory(event_id)))

    def correct(self, event_id: str, replacement_text: str) -> dict[str, Any]:
        return self._guard(
            lambda: ok_payload(**self._state.tools.correct_memory(event_id, replacement_text))
        )

    def delete(self, event_id: str, *, reason: str) -> dict[str, Any]:
        return self._guard(lambda: ok_payload(**self._state.tools.delete_memory(event_id, reason=reason)))

    def audit(self) -> dict[str, Any]:
        records = [record.to_dict() for record in self._state.service.audit()]
        return ok_payload(audit_records=records)

    def metrics(self) -> dict[str, Any]:
        return to_jsonable(self._state.service.metrics_snapshot())

    def _guard(self, action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        try:
            return to_jsonable(action())
        except (MemoryEventNotFound, MemoryPermissionDenied) as exc:
            return error_payload(exc)
