from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from itertools import count

from phone_mem.governance.audit import AuditLog, AuditSelector
from phone_mem.governance.permissions import PermissionScope, PermissionService
from phone_mem.governance.views import MemoryViewProjector
from phone_mem.personal_memory_service.constructor import MemoryCandidate, MemoryConstructor
from phone_mem.personal_memory_service.events import (
    AuditOperation,
    AuditRecord,
    Lifecycle,
    LifecycleState,
    Lineage,
    MemoryEvent,
    MemorySelector,
)
from phone_mem.personal_memory_service.retrieval import LocalMemoryRetriever, RetrievalResult
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore, TombstoneRecord


@dataclass(frozen=True)
class PersonalMemoryService:
    store: SQLiteMemoryStore
    constructor: MemoryConstructor
    permissions: PermissionService
    audit_log: AuditLog
    retriever: LocalMemoryRetriever
    clock: Callable[[], datetime]
    tombstone_id_factory: Callable[[], str]

    @classmethod
    def in_memory(
        cls,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> PersonalMemoryService:
        resolved_clock = clock or (lambda: datetime.now(tz=UTC))
        event_ids = count(1)
        grant_ids = count(1)
        audit_ids = count(1)
        tombstone_ids = count(1)
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        constructor = MemoryConstructor(
            clock=resolved_clock,
            id_factory=lambda: f"event-{next(event_ids)}",
        )
        permissions = PermissionService(
            store,
            clock=resolved_clock,
            id_factory=lambda: f"grant-{next(grant_ids)}",
        )
        audit_log = AuditLog(
            store,
            clock=resolved_clock,
            id_factory=lambda: f"audit-{next(audit_ids)}",
        )
        retriever = LocalMemoryRetriever(
            store=store,
            projector=MemoryViewProjector(permissions),
            audit_log=audit_log,
            clock=resolved_clock,
        )
        return cls(
            store=store,
            constructor=constructor,
            permissions=permissions,
            audit_log=audit_log,
            retriever=retriever,
            clock=resolved_clock,
            tombstone_id_factory=lambda: f"tombstone-{next(tombstone_ids)}",
        )

    def record(self, event: MemoryCandidate | dict[str, object], *, caller: str) -> str:
        memory_event = self._construct_event(event)
        decision = self.permissions.can_access(caller, AuditOperation.WRITE, memory_event)
        if not decision.allowed:
            self.audit_log.record(
                caller,
                AuditOperation.WRITE,
                {"event": memory_event.to_dict()},
                [memory_event.event_id],
                "denied",
                denial_reason=decision.reason,
            )
            raise PermissionError(decision.reason)

        duplicate = self._find_duplicate(memory_event)
        if duplicate is not None:
            self.audit_log.record(
                caller,
                AuditOperation.WRITE,
                {"event": memory_event.to_dict(), "duplicate_of": duplicate.event_id},
                [duplicate.event_id],
                "allowed",
            )
            return duplicate.event_id

        contradiction = self._find_contradiction(memory_event)
        if contradiction is not None:
            memory_event = replace(
                memory_event,
                lifecycle=Lifecycle(state=LifecycleState.QUARANTINED),
                lineage=Lineage(parents=[contradiction.event_id]),
            )

        self.store.insert_event(memory_event)
        self.audit_log.record(
            caller,
            AuditOperation.WRITE,
            {"event": memory_event.to_dict()},
            [memory_event.event_id],
            "allowed",
        )
        return memory_event.event_id

    def search(
        self,
        query: str,
        *,
        caller: str,
        scope: MemorySelector | None = None,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        return self.retriever.search(query, caller=caller, selector=scope, top_k=top_k)

    def explain(self, event_id: str, *, caller: str) -> dict[str, object]:
        event = self._get_event_or_raise(event_id)
        decision = self.permissions.can_access(caller, AuditOperation.READ, event)
        if not decision.allowed:
            self.audit_log.record(
                caller,
                AuditOperation.READ,
                {"event_id": event_id, "explain": True},
                [event_id],
                "denied",
                denial_reason=decision.reason,
            )
            raise PermissionError(decision.reason)

        self.audit_log.record(
            caller,
            AuditOperation.READ,
            {"event_id": event_id, "explain": True},
            [event_id],
            "allowed",
        )
        return self._explanation(event)

    def correct(self, event_id: str, patch: dict[str, object], *, caller: str) -> str:
        original = self._get_event_or_raise(event_id)
        decision = self.permissions.can_access(caller, AuditOperation.UPDATE, original)
        if not decision.allowed:
            self.audit_log.record(
                caller,
                AuditOperation.UPDATE,
                {"event_id": event_id, "patch": dict(patch)},
                [event_id],
                "denied",
                denial_reason=decision.reason,
            )
            raise PermissionError(decision.reason)

        corrected = self.constructor.construct(
            MemoryCandidate(
                semantic_description=str(
                    patch.get("semantic_description", original.semantic_description)
                ),
                source_app=original.source.app,
                actor=original.source.actor,
                modality=list(original.source.modality),
                attribution=original.source.attribution,
                event_type=original.event_type,
                memory_layer=original.memory_layer,
                entities=list(patch.get("entities", original.entities)),
                relations=list(patch.get("relations", original.relations)),
                privacy_level=original.privacy.level,
                allowed_scopes=list(original.privacy.allowed_scopes),
                confidence=original.quality.confidence,
                importance=original.quality.importance,
                freshness_half_life_days=original.quality.freshness_half_life_days,
                valid_at=original.valid_time.start,
                lineage=Lineage(parents=[event_id], supersedes=[event_id]),
            )
        )
        self.store.insert_event(corrected)
        self.store.update_lifecycle(event_id, Lifecycle(state=LifecycleState.SUPERSEDED))
        self.audit_log.record(
            caller,
            AuditOperation.UPDATE,
            {"event_id": event_id, "patch": dict(patch)},
            [event_id, corrected.event_id],
            "allowed",
        )
        return corrected.event_id

    def delete(self, selector: MemorySelector, *, caller: str, reason: str) -> list[str]:
        deleted_at = self.clock()
        deleted_event_ids: list[str] = []
        for event in self.store.query_events(selector):
            decision = self.permissions.can_access(caller, AuditOperation.DELETE, event)
            if not decision.allowed:
                self.audit_log.record(
                    caller,
                    AuditOperation.DELETE,
                    selector.to_dict(),
                    [event.event_id],
                    "denied",
                    denial_reason=decision.reason,
                )
                raise PermissionError(decision.reason)

            self.store.update_lifecycle(
                event.event_id,
                event.lifecycle.mark_deleted(deleted_at=deleted_at, reason=reason),
            )
            self.store.write_tombstone(
                TombstoneRecord(
                    tombstone_id=self.tombstone_id_factory(),
                    event_id=event.event_id,
                    deleted_at=deleted_at,
                    reason=reason,
                    selector=selector,
                )
            )
            deleted_event_ids.append(event.event_id)

        self.audit_log.record(
            caller,
            AuditOperation.DELETE,
            selector.to_dict(),
            deleted_event_ids,
            "allowed",
        )
        return deleted_event_ids

    def grant(self, caller: str, scope: PermissionScope, duration_seconds: int) -> str:
        grant = self.permissions.grant(caller, scope, duration_seconds)
        self.audit_log.record(
            caller,
            AuditOperation.GRANT,
            scope.to_dict(),
            [],
            "allowed",
        )
        return grant.grant_id

    def revoke(self, grant_id: str) -> None:
        self.permissions.revoke(grant_id)
        self.audit_log.record(
            "system",
            AuditOperation.REVOKE,
            {"grant_id": grant_id},
            [],
            "allowed",
        )

    def audit(self, selector: AuditSelector | None = None) -> list[AuditRecord]:
        return self.audit_log.query(selector)

    def _construct_event(self, event: MemoryCandidate | dict[str, object]) -> MemoryEvent:
        if isinstance(event, MemoryCandidate):
            return self.constructor.construct(event)
        return self.constructor.construct(MemoryCandidate(**event))

    def _get_event_or_raise(self, event_id: str) -> MemoryEvent:
        event = self.store.get_event(event_id)
        if event is None:
            raise KeyError(event_id)
        return event

    def _find_duplicate(self, event: MemoryEvent) -> MemoryEvent | None:
        for existing in self._active_events():
            if self._is_duplicate(existing, event):
                return existing
        return None

    def _find_contradiction(self, event: MemoryEvent) -> MemoryEvent | None:
        for existing in self._active_events():
            if self._is_contradiction(existing, event):
                return existing
        return None

    def _active_events(self) -> list[MemoryEvent]:
        return self.store.query_events(MemorySelector(lifecycle_states=[LifecycleState.ACTIVE]))

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

    def _explanation(self, event: MemoryEvent) -> dict[str, object]:
        return {
            "event_id": event.event_id,
            "source": event.source.to_dict(),
            "memory_layer": event.memory_layer.value,
            "privacy": event.privacy.to_dict(),
            "quality": event.quality.to_dict(),
            "lineage": event.lineage.to_dict(),
            "lifecycle": event.lifecycle.to_dict(),
        }
