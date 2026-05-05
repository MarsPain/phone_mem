from __future__ import annotations

from datetime import UTC, datetime

from phone_mem.context.budgets import ContextBudget
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.errors import MemoryEventNotFound, MemoryPermissionDenied
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    AuditOperation,
    MemoryLayer,
    Modality,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService
from tests.memory_service_contract_serializers import (
    context_bundle_to_dict,
    retrieval_result_to_dict,
    service_error_to_dict,
)


NOW = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)


def reference_outputs() -> dict[str, object]:
    outputs = _happy_path_outputs()
    outputs["lifecycle_explanations"] = _lifecycle_explanation_outputs()
    outputs["service_errors"] = _service_error_outputs()
    return outputs


def _candidate(
    semantic_description: str = "User prefers morning planning sessions.",
    *,
    entity: str = "planning",
) -> MemoryCandidate:
    return MemoryCandidate(
        semantic_description=semantic_description,
        source_app="system_assistant",
        actor=Actor.USER,
        modality=[Modality.TEXT],
        attribution=Attribution.USER_STATED,
        entities=[entity],
    )


def _happy_path_outputs() -> dict[str, object]:
    service = PersonalMemoryService.in_memory(clock=lambda: NOW)
    try:
        grant_id = service.grant(
            "calendar_agent",
            PermissionScope(
                operations=[
                    AuditOperation.WRITE,
                    AuditOperation.READ,
                    AuditOperation.DELETE,
                    AuditOperation.CONTEXT_BUILD,
                ],
                apps=["system_assistant"],
                privacy_levels=[PrivacyLevel.PERSONAL],
                memory_layers=[MemoryLayer.EPISODIC],
            ),
            duration_seconds=60,
        )
        event_id = service.record(_candidate(), caller="calendar_agent")
        results = service.search("morning planning", caller="calendar_agent", top_k=1)
        bundle = service.build_context(
            "morning planning",
            caller="calendar_agent",
            task={"id": "task-1"},
            budget=ContextBudget(max_tokens=80, safety_reserve_tokens=10, output_reserve_tokens=20),
            top_k=1,
        )
        deleted_event_ids = service.delete_by_event_id(
            event_id,
            caller="calendar_agent",
            reason="user requested deletion",
        )
        tombstone = service.store.list_tombstones()[0]
        event = service.store.get_event(event_id)
        if event is None:
            raise AssertionError("reference event should remain readable after deletion")
        grants = service.store.list_permission_grants(caller="calendar_agent")
        grant = next(item for item in grants if item.grant_id == grant_id)

        return {
            "canonical_event": event.to_dict(),
            "permission_grant": {
                "grant_id": grant.grant_id,
                "caller": grant.caller,
                "scope": grant.scope.to_dict(),
                "granted_at": grant.granted_at.isoformat(),
                "expires_at": grant.expires_at.isoformat(),
                "revoked_at": None,
            },
            "search_result": [retrieval_result_to_dict(result) for result in results],
            "context_bundle": context_bundle_to_dict(bundle),
            "delete_tombstone": {
                "deleted_event_ids": deleted_event_ids,
                "tombstones": [
                    {
                        "tombstone_id": tombstone.tombstone_id,
                        "event_id": tombstone.event_id,
                        "deleted_at": tombstone.deleted_at.isoformat(),
                        "reason": tombstone.reason,
                        "selector": tombstone.selector.to_dict(),
                    }
                ],
            },
            "audit_records": [record.to_dict() for record in service.audit()],
        }
    finally:
        service.close()


def _lifecycle_explanation_outputs() -> dict[str, object]:
    correction_service = PersonalMemoryService.in_memory(clock=lambda: NOW)
    quarantine_service = PersonalMemoryService.in_memory(clock=lambda: NOW)
    try:
        correction_service.grant(
            "calendar_agent",
            PermissionScope(
                operations=[AuditOperation.WRITE, AuditOperation.READ, AuditOperation.UPDATE],
                apps=["system_assistant"],
                entities=["planning"],
            ),
            duration_seconds=60,
        )
        original_id = correction_service.record(_candidate(), caller="calendar_agent")
        corrected_id = correction_service.correct(
            original_id,
            {"semantic_description": "User prefers afternoon planning sessions."},
            caller="calendar_agent",
        )

        quarantine_service.grant(
            "travel_agent",
            PermissionScope(
                operations=[AuditOperation.WRITE, AuditOperation.READ],
                apps=["system_assistant"],
                entities=["travel"],
            ),
            duration_seconds=60,
        )
        active_id = quarantine_service.record(
            _candidate("User prefers aisle seats for flights.", entity="travel"),
            caller="travel_agent",
        )
        quarantined_id = quarantine_service.record(
            _candidate("User prefers window seats for flights.", entity="travel"),
            caller="travel_agent",
        )

        return {
            "correction": {
                "original_event_id": original_id,
                "corrected_event_id": corrected_id,
                "original_explanation": correction_service.explain(original_id, caller="calendar_agent"),
                "corrected_explanation": correction_service.explain(corrected_id, caller="calendar_agent"),
            },
            "quarantine": {
                "active_event_id": active_id,
                "quarantined_event_id": quarantined_id,
                "quarantined_explanation": quarantine_service.explain(quarantined_id, caller="travel_agent"),
            },
        }
    finally:
        correction_service.close()
        quarantine_service.close()


def _service_error_outputs() -> dict[str, object]:
    service = PersonalMemoryService.in_memory(clock=lambda: NOW)
    try:
        try:
            service.record(_candidate(), caller="calendar_agent")
        except MemoryPermissionDenied as error:
            permission_denied = service_error_to_dict("permission_denied", error)
        else:
            raise AssertionError("record without a grant should fail")

        try:
            service.explain("missing-event", caller="calendar_agent")
        except MemoryEventNotFound as error:
            not_found = service_error_to_dict("not_found", error)
        else:
            raise AssertionError("explain for a missing event should fail")

        return {"permission_denied": permission_denied, "not_found": not_found}
    finally:
        service.close()
