from __future__ import annotations

from dataclasses import replace

from phone_mem.personal_memory_service.events import (
    Lifecycle,
    LifecycleState,
    Lineage,
    MemoryEvent,
    MemorySelector,
)
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore


class MemoryLifecycleValidator:
    def __init__(self, store: SQLiteMemoryStore) -> None:
        self._store = store

    def find_duplicate(self, event: MemoryEvent) -> MemoryEvent | None:
        for existing in self._active_events():
            if self._is_duplicate(existing, event):
                return existing
        return None

    def quarantine_if_contradictory(self, event: MemoryEvent) -> MemoryEvent:
        contradiction = self._find_contradiction(event)
        if contradiction is None:
            return event
        return replace(
            event,
            lifecycle=Lifecycle(state=LifecycleState.QUARANTINED),
            lineage=Lineage(parents=[contradiction.event_id]),
        )

    def _find_contradiction(self, event: MemoryEvent) -> MemoryEvent | None:
        for existing in self._active_events():
            if self._is_contradiction(existing, event):
                return existing
        return None

    def _active_events(self) -> list[MemoryEvent]:
        return self._store.query_events(MemorySelector(lifecycle_states=[LifecycleState.ACTIVE]))

    def _is_duplicate(self, existing: MemoryEvent, event: MemoryEvent) -> bool:
        return (
            existing.source.app == event.source.app
            and existing.memory_layer == event.memory_layer
            and set(existing.entities) == set(event.entities)
            and self._normalized_text(existing.semantic_description)
            == self._normalized_text(event.semantic_description)
        )

    def _is_contradiction(self, existing: MemoryEvent, event: MemoryEvent) -> bool:
        if existing.source.app != event.source.app:
            return False
        if not set(existing.entities).intersection(event.entities):
            return False
        existing_text = self._normalized_text(existing.semantic_description)
        event_text = self._normalized_text(event.semantic_description)
        return "prefers" in existing_text and "prefers" in event_text and existing_text != event_text

    def _normalized_text(self, value: str) -> str:
        return " ".join(value.lower().split())
