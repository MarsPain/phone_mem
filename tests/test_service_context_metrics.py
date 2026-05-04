from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.context.budgets import ContextBudget
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    AuditOperation,
    MemoryLayer,
    Modality,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService


def grant_full_personal_access(service: PersonalMemoryService, caller: str) -> None:
    service.grant(
        caller,
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


class ServiceContextAndMetricsTest(unittest.TestCase):
    def test_build_context_uses_governed_retrieval_and_records_metrics(self) -> None:
        now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        service = PersonalMemoryService.in_memory(clock=lambda: now)
        self.addCleanup(service.close)
        grant_full_personal_access(service, "calendar_agent")
        event_id = service.record(
            MemoryCandidate(
                semantic_description="User prefers morning planning sessions.",
                source_app="system_assistant",
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=Attribution.USER_STATED,
                entities=["planning"],
            ),
            caller="calendar_agent",
        )

        bundle = service.build_context(
            "morning planning",
            caller="calendar_agent",
            task={"id": "task-1"},
            budget=ContextBudget(max_tokens=80, safety_reserve_tokens=10, output_reserve_tokens=20),
        )
        metrics = service.metrics_snapshot()

        self.assertEqual(bundle.evidence_event_ids, [event_id])
        self.assertEqual(metrics["retrieval"]["read_audit_records"], 1)
        self.assertEqual(metrics["context"]["context_build_audit_records"], 1)
        self.assertEqual(metrics["context"]["latest_budget_used_tokens"], bundle.token_budget.used_tokens)
        self.assertEqual(metrics["context"]["latest_budget_limit_tokens"], bundle.token_budget.available_memory_tokens)

    def test_metrics_snapshot_counts_permission_denials_and_deletion_tombstones(self) -> None:
        now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        service = PersonalMemoryService.in_memory(clock=lambda: now)
        self.addCleanup(service.close)
        grant_full_personal_access(service, "calendar_agent")
        event_id = service.record(
            MemoryCandidate(
                semantic_description="User prefers morning planning sessions.",
                source_app="system_assistant",
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=Attribution.USER_STATED,
                entities=["planning"],
            ),
            caller="calendar_agent",
        )

        with self.assertRaises(PermissionError):
            service.explain(event_id, caller="health_agent")
        service.delete_by_event_id(event_id, caller="calendar_agent", reason="user requested deletion")
        metrics = service.metrics_snapshot()

        self.assertEqual(metrics["permission"]["denied_audit_records"], 1)
        self.assertEqual(metrics["deletion"]["tombstone_count"], 1)
        self.assertEqual(metrics["deletion"]["deleted_event_count"], 1)
        self.assertEqual(metrics["audit"]["write_audit_records"], 1)


if __name__ == "__main__":
    unittest.main()
