from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.agent_runtime.tools import MemoryToolRegistry
from phone_mem.context.assembler import ContextBundle, ContextTokenBudget
from phone_mem.context.capsules import HotMemoryCapsule
from phone_mem.personal_memory_service.relations import RelationPath
from phone_mem.personal_memory_service.retrieval import MemorySnippet
from phone_mem.governance.permissions import PermissionScope
from phone_mem.personal_memory_service.errors import MemoryPermissionDenied
from phone_mem.personal_memory_service.events import (
    AuditOperation,
    MemoryLayer,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService


CALLER = "runtime_agent"
SOURCE_APP = "system_assistant"


class AgentRuntimeMemoryToolsTest(unittest.TestCase):
    def test_memory_tools_record_search_context_explain_correct_and_delete(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        tools = MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP)

        remembered = tools.remember(
            "User prefers morning planning sessions.",
            entities=["planning"],
        )
        search = tools.search_memory("morning planning", top_k=3)
        context = tools.build_memory_context("morning planning", max_tokens=80)
        explanation = tools.explain_memory(remembered["event_id"])
        corrected = tools.correct_memory(
            remembered["event_id"],
            "User prefers afternoon planning sessions.",
        )
        deleted = tools.delete_memory(corrected["event_id"], reason="user requested deletion")

        self.assertEqual(remembered["event_id"], "event-1")
        self.assertEqual(search["results"][0]["event_id"], "event-1")
        self.assertEqual(search["results"][0]["text"], "User prefers morning planning sessions.")
        self.assertEqual(context["evidence_event_ids"], ["event-1"])
        self.assertEqual(explanation["event_id"], "event-1")
        self.assertEqual(corrected["event_id"], "event-2")
        self.assertEqual(deleted["deleted_event_ids"], ["event-2"])

        audit_operations = [record.operation for record in service.audit()]
        self.assertIn(AuditOperation.WRITE, audit_operations)
        self.assertIn(AuditOperation.READ, audit_operations)
        self.assertIn(AuditOperation.CONTEXT_BUILD, audit_operations)
        self.assertIn(AuditOperation.UPDATE, audit_operations)
        self.assertIn(AuditOperation.DELETE, audit_operations)

    def test_memory_context_retrieves_chinese_preference_followup(self) -> None:
        service = _service_with_grant()
        self.addCleanup(service.close)
        tools = MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP)

        remembered = tools.remember("用户喜欢早上9点喝咖啡。", entities=["咖啡"])
        context = tools.build_memory_context("我喜欢几点喝咖啡", max_tokens=80)

        self.assertEqual(remembered["event_id"], "event-1")
        self.assertEqual(context["evidence_event_ids"], ["event-1"])
        self.assertEqual(context["snippets"][0]["text"], "用户喜欢早上9点喝咖啡。")

    def test_memory_tools_preserve_permission_denial_errors(self) -> None:
        service = PersonalMemoryService.in_memory(clock=lambda: datetime(2026, 5, 3, tzinfo=UTC))
        self.addCleanup(service.close)
        tools = MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP)

        with self.assertRaises(MemoryPermissionDenied) as raised:
            tools.remember("User prefers morning planning sessions.")

        self.assertEqual(raised.exception.operation, AuditOperation.WRITE)
        self.assertEqual(raised.exception.caller, CALLER)

    def test_tool_definitions_are_provider_neutral(self) -> None:
        tools = MemoryToolRegistry(
            service=PersonalMemoryService.in_memory(),
            caller=CALLER,
            source_app=SOURCE_APP,
        )
        self.addCleanup(tools.service.close)

        definitions = {definition.name: definition for definition in tools.tool_definitions()}

        self.assertIn("search_memory", definitions)
        self.assertIn("remember", definitions)
        self.assertEqual(definitions["search_memory"].parameters["type"], "object")
        self.assertIn("query", definitions["search_memory"].parameters["properties"])

    def test_remember_tool_schema_exposes_governed_classification_fields(self) -> None:
        tools = MemoryToolRegistry(
            service=PersonalMemoryService.in_memory(),
            caller=CALLER,
            source_app=SOURCE_APP,
        )
        self.addCleanup(tools.service.close)

        definitions = {definition.name: definition for definition in tools.tool_definitions()}
        remember_properties = definitions["remember"].parameters["properties"]

        self.assertIn("privacy_level", remember_properties)
        self.assertIn("memory_layer", remember_properties)
        self.assertIn("enum", remember_properties["privacy_level"])
        self.assertIn("enum", remember_properties["memory_layer"])

    def test_execute_remember_passes_privacy_and_layer_through_governed_service(self) -> None:
        service = PersonalMemoryService.in_memory(clock=lambda: datetime(2026, 5, 3, tzinfo=UTC))
        self.addCleanup(service.close)
        service.grant(
            CALLER,
            PermissionScope(
                operations=[AuditOperation.WRITE, AuditOperation.READ],
                apps=[SOURCE_APP],
                privacy_levels=[PrivacyLevel.PUBLIC],
                memory_layers=[MemoryLayer.SEMANTIC],
            ),
            duration_seconds=3_600,
        )
        tools = MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP)

        remembered = tools.execute(
            "remember",
            {
                "text": "The beta launch date is May 20.",
                "entities": ["beta launch"],
                "privacy_level": "public",
                "memory_layer": "semantic",
            },
        )
        explanation = tools.explain_memory(remembered["event_id"])

        self.assertEqual(explanation["memory_layer"], "semantic")
        self.assertEqual(explanation["privacy"]["level"], "public")

    def test_context_tool_serializes_stage_1_7_bundle_fields(self) -> None:
        relation_path = RelationPath(
            nodes=["Mira", "Project Atlas", "credential refresh"],
            edge_types=["person_assigned_to_project", "solved_by"],
            evidence_event_ids=["event-2", "event-3"],
            compression_score=0.67,
        )
        service = _ContextBundleService(
            ContextBundle(
                task={"id": "agent-runtime-turn", "description": "planning"},
                snippets=[
                    MemorySnippet(
                        event_id="event-1",
                        text="User prefers morning planning sessions.",
                        source_app=SOURCE_APP,
                        attribution="user_stated",
                        confidence=0.95,
                        memory_layer="episodic",
                        privacy_level="personal",
                        evidence_event_ids=["event-1"],
                    )
                ],
                hot_memory_capsules=[
                    HotMemoryCapsule(
                        category="stable_user_confirmed_fact",
                        text="Fact.",
                        evidence_event_ids=["event-1"],
                        confidence=0.95,
                        attribution="user_stated",
                        omitted_memory=[{"event_id": "event-9", "reason": "budget_exhausted"}],
                    )
                ],
                relation_paths=[relation_path],
                evidence_event_ids=["event-1", "event-2", "event-3"],
                token_budget=ContextTokenBudget(
                    max_tokens=80,
                    safety_reserve_tokens=10,
                    output_reserve_tokens=30,
                    tool_reserve_tokens=10,
                    available_memory_tokens=30,
                    used_tokens=12,
                ),
                omitted_memory=[{"event_id": "event-9", "reason": "budget_exhausted"}],
                safety_metadata={
                    "capsule_budget": {
                        "separate_from_snippets": True,
                        "budget_tokens": 30,
                        "used_tokens": 4,
                        "omitted_capsules": [],
                    }
                },
            )
        )
        tools = MemoryToolRegistry(service=service, caller=CALLER, source_app=SOURCE_APP)

        context = tools.build_memory_context("planning", max_tokens=80)

        self.assertEqual(context["omitted_memory"], [{"event_id": "event-9", "reason": "budget_exhausted"}])
        self.assertEqual(context["relation_paths"][0]["relation_types"], ["person_assigned_to_project", "solved_by"])
        self.assertEqual(context["relation_paths"][0]["source_label"], "Mira")
        self.assertEqual(context["relation_paths"][0]["target_label"], "credential refresh")
        self.assertEqual(context["relation_paths"][0]["evidence_event_ids"], ["event-2", "event-3"])
        self.assertEqual(context["relation_paths"][0]["path_metadata"]["node_count"], 3)
        self.assertEqual(context["token_budget"]["safety_reserve_tokens"], 10)
        self.assertEqual(context["safety_metadata"]["capsule_budget"]["used_tokens"], 4)


def _service_with_grant() -> PersonalMemoryService:
    service = PersonalMemoryService.in_memory(clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC))
    service.grant(
        CALLER,
        PermissionScope(
            operations=[
                AuditOperation.WRITE,
                AuditOperation.READ,
                AuditOperation.UPDATE,
                AuditOperation.DELETE,
                AuditOperation.CONTEXT_BUILD,
            ],
            apps=[SOURCE_APP],
            privacy_levels=[PrivacyLevel.PERSONAL],
            memory_layers=[MemoryLayer.EPISODIC],
        ),
        duration_seconds=3_600,
    )
    return service


class _ContextBundleService:
    def __init__(self, bundle: ContextBundle) -> None:
        self.bundle = bundle

    def build_context(self, *args: object, **kwargs: object) -> ContextBundle:
        return self.bundle


if __name__ == "__main__":
    unittest.main()
