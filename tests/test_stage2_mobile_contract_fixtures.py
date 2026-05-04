from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
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


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "memory_service"


class Stage2MobileWorkspaceBoundaryTest(unittest.TestCase):
    def test_mobile_workspace_documents_reference_service_domains(self) -> None:
        readme = ROOT / "mobile" / "README.md"
        self.assertTrue(readme.exists(), "mobile/README.md should describe Stage 2 scope")
        text = readme.read_text(encoding="utf-8")

        for expected in [
            "memory_core",
            "governance",
            "storage",
            "retrieval",
            "context",
            "service",
            "Python reference",
        ]:
            self.assertIn(expected, text)

    def test_mobile_type_boundaries_exist_without_toolchain_lock_in(self) -> None:
        expected_files = [
            "mobile/memory_core/events.ts",
            "mobile/governance/permissions.ts",
            "mobile/governance/audit.ts",
            "mobile/storage/storage.ts",
            "mobile/retrieval/retrieval.ts",
            "mobile/context/context.ts",
            "mobile/service/personal_memory_service.ts",
        ]

        for relative_path in expected_files:
            self.assertTrue((ROOT / relative_path).exists(), relative_path)

        self.assertFalse((ROOT / "mobile" / "package.json").exists())


class MemoryServiceFixtureContractTest(unittest.TestCase):
    def test_required_fixture_files_exist(self) -> None:
        expected_files = [
            "canonical_event.json",
            "permission_grant.json",
            "search_result.json",
            "context_bundle.json",
            "delete_tombstone.json",
            "audit_records.json",
        ]

        for file_name in expected_files:
            with self.subTest(file_name=file_name):
                self.assertTrue((FIXTURE_DIR / file_name).exists())

    def test_fixtures_match_python_reference_service_output(self) -> None:
        actual = self._reference_outputs()

        for name, expected in actual.items():
            path = FIXTURE_DIR / f"{name}.json"
            with self.subTest(path=path):
                loaded = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(loaded, expected)

    def _reference_outputs(self) -> dict[str, object]:
        now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        service = PersonalMemoryService.in_memory(clock=lambda: now)
        self.addCleanup(service.close)
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
        self.assertIsNotNone(event)
        assert event is not None
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
            "search_result": [self._retrieval_result_to_dict(result) for result in results],
            "context_bundle": self._context_bundle_to_dict(bundle),
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

    def _retrieval_result_to_dict(self, result: object) -> dict[str, object]:
        snippet = result.snippet
        return {
            "event_id": result.event_id,
            "score": result.score,
            "snippet": {
                "event_id": snippet.event_id,
                "text": snippet.text,
                "source_app": snippet.source_app,
                "attribution": snippet.attribution,
                "confidence": snippet.confidence,
                "memory_layer": snippet.memory_layer,
                "privacy_level": snippet.privacy_level,
                "evidence_event_ids": snippet.evidence_event_ids,
            },
            "explanation": result.explanation,
        }

    def _context_bundle_to_dict(self, bundle: object) -> dict[str, object]:
        return {
            "task": bundle.task,
            "snippets": [
                {
                    "event_id": snippet.event_id,
                    "text": snippet.text,
                    "source_app": snippet.source_app,
                    "attribution": snippet.attribution,
                    "confidence": snippet.confidence,
                    "memory_layer": snippet.memory_layer,
                    "privacy_level": snippet.privacy_level,
                    "evidence_event_ids": snippet.evidence_event_ids,
                }
                for snippet in bundle.snippets
            ],
            "evidence_event_ids": bundle.evidence_event_ids,
            "token_budget": {
                "max_tokens": bundle.token_budget.max_tokens,
                "safety_reserve_tokens": bundle.token_budget.safety_reserve_tokens,
                "output_reserve_tokens": bundle.token_budget.output_reserve_tokens,
                "tool_reserve_tokens": bundle.token_budget.tool_reserve_tokens,
                "available_memory_tokens": bundle.token_budget.available_memory_tokens,
                "used_tokens": bundle.token_budget.used_tokens,
            },
            "omitted_memory": bundle.omitted_memory,
            "safety_metadata": bundle.safety_metadata,
        }


if __name__ == "__main__":
    unittest.main()
