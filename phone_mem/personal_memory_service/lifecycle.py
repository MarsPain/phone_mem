from __future__ import annotations

from dataclasses import replace
import re

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
        for existing in self._active_events(event, include_layer=True):
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
        for existing in self._active_events(event, include_layer=False):
            if self._is_contradiction(existing, event):
                return existing
        return None

    def _active_events(self, event: MemoryEvent, *, include_layer: bool) -> list[MemoryEvent]:
        return self._store.query_events(
            MemorySelector(
                app=event.source.app,
                entities=list(event.entities),
                memory_layers=[event.memory_layer] if include_layer else [],
                lifecycle_states=[LifecycleState.ACTIVE],
            )
        )

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
        existing_preference = self._preference_fact(existing_text)
        event_preference = self._preference_fact(event_text)
        if existing_preference is None or event_preference is None:
            return False
        existing_value, existing_context = existing_preference
        event_value, event_context = event_preference
        return existing_context == event_context and existing_value != event_value

    def _normalized_text(self, value: str) -> str:
        return " ".join(value.lower().split())

    def _preference_fact(self, text: str) -> tuple[str, str] | None:
        match = re.match(
            r"^user (?P<verb>prefers|prefer|likes|like|wants|want) "
            r"(?P<value>.+?)(?: for (?P<context>.+))?\.?$",
            text,
        )
        if match is None:
            return None
        value = self._normalized_preference_part(match.group("value"))
        context = self._normalized_preference_part(match.group("context") or "")
        return value, context

    def _normalized_preference_part(self, value: str) -> str:
        return value.strip(" .")
