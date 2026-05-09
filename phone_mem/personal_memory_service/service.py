from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import count
from pathlib import Path
from uuid import uuid4

from phone_mem.governance.audit import AuditLog, AuditSelector
from phone_mem.governance.permissions import PermissionScope, PermissionService
from phone_mem.governance.views import MemoryViewProjector
from phone_mem.context.assembler import ContextAssembler, ContextBundle
from phone_mem.context.budgets import ContextBudget
from phone_mem.personal_memory_service.constructor import MemoryCandidate, MemoryConstructor
from phone_mem.personal_memory_service.events import (
    AuditOperation,
    AuditRecord,
    Lifecycle,
    LifecycleState,
    MemoryEvent,
    MemorySelector,
)
from phone_mem.personal_memory_service.errors import MemoryEventNotFound, MemoryPermissionDenied
from phone_mem.personal_memory_service.lifecycle import MemoryLifecycleValidator
from phone_mem.personal_memory_service.maintenance import MemoryMaintenance
from phone_mem.personal_memory_service.maintenance_reports import (
    DefragReport,
    ReflectionReport,
    SchemaDiffReport,
)
from phone_mem.personal_memory_service.metrics import MemoryServiceMetrics
from phone_mem.personal_memory_service.retrieval import LocalMemoryRetriever, RetrievalResult
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore, TombstoneRecord


@dataclass(frozen=True)
class PersonalMemoryService:
    store: SQLiteMemoryStore
    constructor: MemoryConstructor
    permissions: PermissionService
    audit_log: AuditLog
    retriever: LocalMemoryRetriever
    context_assembler: ContextAssembler
    lifecycle_validator: MemoryLifecycleValidator
    maintenance: MemoryMaintenance
    metrics: MemoryServiceMetrics
    clock: Callable[[], datetime]
    tombstone_id_factory: Callable[[], str]

    @classmethod
    def from_store(
        cls,
        store: SQLiteMemoryStore,
        *,
        clock: Callable[[], datetime] | None = None,
        event_id_factory: Callable[[], str] | None = None,
        grant_id_factory: Callable[[], str] | None = None,
        audit_id_factory: Callable[[], str] | None = None,
        tombstone_id_factory: Callable[[], str] | None = None,
    ) -> PersonalMemoryService:
        resolved_clock = clock or (lambda: datetime.now(tz=UTC))
        constructor = MemoryConstructor(
            clock=resolved_clock,
            id_factory=event_id_factory or (lambda: str(uuid4())),
        )
        permissions = PermissionService(
            store,
            clock=resolved_clock,
            id_factory=grant_id_factory or (lambda: str(uuid4())),
        )
        audit_log = AuditLog(
            store,
            clock=resolved_clock,
            id_factory=audit_id_factory or (lambda: str(uuid4())),
        )
        retriever = LocalMemoryRetriever(
            store=store,
            projector=MemoryViewProjector(permissions),
            audit_log=audit_log,
            clock=resolved_clock,
        )
        context_assembler = ContextAssembler(audit_log=audit_log)
        metrics = MemoryServiceMetrics(store)
        lifecycle_validator = MemoryLifecycleValidator(store)
        maintenance = MemoryMaintenance(store)
        return cls(
            store=store,
            constructor=constructor,
            permissions=permissions,
            audit_log=audit_log,
            retriever=retriever,
            context_assembler=context_assembler,
            lifecycle_validator=lifecycle_validator,
            maintenance=maintenance,
            metrics=metrics,
            clock=resolved_clock,
            tombstone_id_factory=tombstone_id_factory or (lambda: str(uuid4())),
        )

    @classmethod
    def in_memory(
        cls,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> PersonalMemoryService:
        event_ids = count(1)
        grant_ids = count(1)
        audit_ids = count(1)
        tombstone_ids = count(1)
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        return cls.from_store(
            store,
            clock=clock,
            event_id_factory=lambda: f"event-{next(event_ids)}",
            grant_id_factory=lambda: f"grant-{next(grant_ids)}",
            audit_id_factory=lambda: f"audit-{next(audit_ids)}",
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
            raise MemoryPermissionDenied(
                operation=AuditOperation.WRITE,
                caller=caller,
                denial_reason=decision.reason,
                affected_event_ids=[memory_event.event_id],
            )

        duplicate = self.lifecycle_validator.find_duplicate(memory_event)
        if duplicate is not None:
            self.audit_log.record(
                caller,
                AuditOperation.WRITE,
                {"event": memory_event.to_dict(), "duplicate_of": duplicate.event_id},
                [duplicate.event_id],
                "allowed",
            )
            return duplicate.event_id

        memory_event = self.lifecycle_validator.quarantine_if_contradictory(memory_event)

        with self.store.transaction():
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
        results = self.retriever.search(query, caller=caller, selector=scope, top_k=top_k)
        self.metrics.record_retrieval_results(results)
        return results

    def build_context(
        self,
        query: str,
        *,
        caller: str,
        task: dict[str, object],
        budget: ContextBudget,
        scope: MemorySelector | None = None,
        top_k: int = 10,
    ) -> ContextBundle:
        results = self.search(query, caller=caller, scope=scope, top_k=top_k)
        bundle = self.context_assembler.build_context(
            results,
            task=task,
            budget=budget,
            caller=caller,
        )
        self.metrics.record_context_bundle(bundle)
        return bundle

    def explain(self, event_id: str, *, caller: str) -> dict[str, object]:
        event = self._get_event_or_raise(
            event_id,
            caller=caller,
            operation=AuditOperation.READ,
            scope={"event_id": event_id, "explain": True},
        )
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
            raise MemoryPermissionDenied(
                operation=AuditOperation.READ,
                caller=caller,
                denial_reason=decision.reason,
                affected_event_ids=[event_id],
            )

        self.audit_log.record(
            caller,
            AuditOperation.READ,
            {"event_id": event_id, "explain": True},
            [event_id],
            "allowed",
        )
        return self._explanation(event)

    def correct(self, event_id: str, patch: dict[str, object], *, caller: str) -> str:
        original = self._get_event_or_raise(
            event_id,
            caller=caller,
            operation=AuditOperation.UPDATE,
            scope={"event_id": event_id, "patch": dict(patch)},
        )
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
            raise MemoryPermissionDenied(
                operation=AuditOperation.UPDATE,
                caller=caller,
                denial_reason=decision.reason,
                affected_event_ids=[event_id],
            )

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
                lineage=self._correction_lineage(event_id),
            )
        )
        with self.store.transaction():
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
        events = self.store.query_events(selector)
        denied_decision: tuple[MemoryEvent, str | None] | None = None
        for event in events:
            decision = self.permissions.can_access(caller, AuditOperation.DELETE, event)
            if not decision.allowed:
                denied_decision = (event, decision.reason)
                break

        if denied_decision is not None:
            event, reason_denied = denied_decision
            self.audit_log.record(
                caller,
                AuditOperation.DELETE,
                selector.to_dict(),
                [event.event_id],
                "denied",
                denial_reason=reason_denied,
            )
            raise MemoryPermissionDenied(
                operation=AuditOperation.DELETE,
                caller=caller,
                denial_reason=reason_denied,
                affected_event_ids=[event.event_id],
                selector=selector.to_dict(),
            )

        deleted_event_ids: list[str] = []
        with self.store.transaction():
            for event in events:
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

    def delete_by_event_id(self, event_id: str, *, caller: str, reason: str) -> list[str]:
        return self.delete(MemorySelector(event_ids=[event_id]), caller=caller, reason=reason)

    def grant(self, caller: str, scope: PermissionScope, duration_seconds: int) -> str:
        with self.store.transaction():
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
        with self.store.transaction():
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

    def metrics_snapshot(self) -> dict[str, dict[str, object]]:
        return self.metrics.snapshot()

    def reflect(self) -> ReflectionReport:
        return self.maintenance.reflect()

    def defrag(self) -> DefragReport:
        return self.maintenance.defrag()

    def schema_diff(self, *, data_doc_path: Path | None = None) -> SchemaDiffReport:
        return self.maintenance.schema_diff(data_doc_path=data_doc_path)

    def close(self) -> None:
        self.store.close()

    def _construct_event(self, event: MemoryCandidate | dict[str, object]) -> MemoryEvent:
        if isinstance(event, MemoryCandidate):
            return self.constructor.construct(event)
        return self.constructor.construct(MemoryCandidate(**event))

    def _get_event_or_raise(
        self,
        event_id: str,
        *,
        caller: str,
        operation: AuditOperation,
        scope: dict[str, object],
    ) -> MemoryEvent:
        event = self.store.get_event(event_id)
        if event is not None:
            return event

        self.audit_log.record(
            caller,
            operation,
            scope,
            [event_id],
            "denied",
            denial_reason="memory event not found",
        )
        raise MemoryEventNotFound(operation=operation, caller=caller, event_id=event_id)

    def _correction_lineage(self, event_id: str) -> object:
        from phone_mem.personal_memory_service.events import Lineage

        return Lineage(parents=[event_id], supersedes=[event_id])

    def _explanation(self, event: MemoryEvent) -> dict[str, object]:
        return {
            "event_id": event.event_id,
            "source": event.source.to_dict(),
            "memory_layer": event.memory_layer.value,
            "privacy": event.privacy.to_dict(),
            "quality": event.quality.to_dict(),
            "lineage": event.lineage.to_dict(),
            "lifecycle": event.lifecycle.to_dict(),
            "lifecycle_explanation": self._lifecycle_explanation(event),
        }

    def _lifecycle_explanation(self, event: MemoryEvent) -> dict[str, object]:
        if event.lifecycle.state == LifecycleState.QUARANTINED:
            return {
                "state": event.lifecycle.state.value,
                "reason": "contradicts active memory",
                "related_event_ids": list(event.lineage.parents),
            }

        if event.lifecycle.state == LifecycleState.SUPERSEDED:
            return {
                "state": event.lifecycle.state.value,
                "reason": "superseded by correction",
                "related_event_ids": self._events_superseding(event.event_id),
            }

        if event.lifecycle.state == LifecycleState.DELETED:
            return {
                "state": event.lifecycle.state.value,
                "reason": event.lifecycle.delete_reason or "deleted",
                "related_event_ids": [],
            }

        if event.lineage.supersedes:
            return {
                "state": event.lifecycle.state.value,
                "reason": "corrects previous memory",
                "related_event_ids": list(event.lineage.supersedes),
            }

        return {
            "state": event.lifecycle.state.value,
            "reason": "active memory",
            "related_event_ids": [],
        }

    def _events_superseding(self, event_id: str) -> list[str]:
        return self.store.events_superseding(event_id)
