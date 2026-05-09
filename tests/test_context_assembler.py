from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
import unittest

from phone_mem.context.assembler import ContextAssembler
from phone_mem.context.budgets import ContextBudget
from phone_mem.context.token_counter import ConservativeTokenCounter
from phone_mem.governance.audit import AuditLog, AuditSelector
from phone_mem.personal_memory_service.relations import RelationPath
from phone_mem.personal_memory_service.events import AuditOperation
from phone_mem.personal_memory_service.retrieval import MemorySnippet, RetrievalResult
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore


def make_result(event_id: str, text: str, *, score: float = 10.0) -> RetrievalResult:
    return RetrievalResult(
        event_id=event_id,
        score=score,
        snippet=MemorySnippet(
            event_id=event_id,
            text=text,
            source_app="system_assistant",
            attribution="user_stated",
            confidence=0.9,
            memory_layer="episodic",
            privacy_level="personal",
            evidence_event_ids=[event_id],
        ),
        explanation={"matched_terms": ["planning"]},
    )


def make_snippet_result(
    event_id: str,
    text: str,
    *,
    attribution: str = "user_stated",
    confidence: float = 0.9,
    memory_layer: str = "episodic",
    score: float = 10.0,
) -> RetrievalResult:
    return RetrievalResult(
        event_id=event_id,
        score=score,
        snippet=MemorySnippet(
            event_id=event_id,
            text=text,
            source_app="system_assistant",
            attribution=attribution,
            confidence=confidence,
            memory_layer=memory_layer,
            privacy_level="personal",
            evidence_event_ids=[event_id],
        ),
        explanation={"matched_terms": ["planning"]},
    )


class ContextAssemblerTest(unittest.TestCase):
    def test_build_context_preserves_evidence_and_budget_accounting(self) -> None:
        assembler = ContextAssembler()
        results = [
            make_result("event-1", "User prefers morning planning sessions."),
            make_result("event-2", "User wants calendar summaries before lunch."),
        ]

        bundle = assembler.build_context(
            results,
            task={"id": "task-1", "description": "Plan tomorrow morning."},
            budget=ContextBudget(max_tokens=80, safety_reserve_tokens=10, output_reserve_tokens=20),
            caller="calendar_agent",
        )

        self.assertEqual(bundle.task["id"], "task-1")
        self.assertEqual([snippet.event_id for snippet in bundle.snippets], ["event-1", "event-2"])
        self.assertEqual(bundle.evidence_event_ids, ["event-1", "event-2"])
        self.assertLessEqual(bundle.token_budget.used_tokens, bundle.token_budget.available_memory_tokens)
        self.assertEqual(bundle.omitted_memory, [])

    def test_build_context_omits_lower_ranked_memory_when_budget_is_exhausted(self) -> None:
        assembler = ContextAssembler()
        results = [
            make_result("event-1", "short memory", score=20.0),
            make_result(
                "event-2",
                "this memory has enough words to exceed the small remaining token budget",
                score=10.0,
            ),
        ]

        bundle = assembler.build_context(
            results,
            task={"id": "task-1"},
            budget=ContextBudget(max_tokens=45, safety_reserve_tokens=10, output_reserve_tokens=20),
            caller="calendar_agent",
        )

        self.assertEqual([snippet.event_id for snippet in bundle.snippets], ["event-1"])
        self.assertEqual(bundle.omitted_memory, [{"event_id": "event-2", "reason": "budget_exhausted"}])

    def test_default_token_counter_counts_cjk_text_conservatively(self) -> None:
        counter = ConservativeTokenCounter()

        self.assertGreater(counter.count("用户喜欢早上9点喝咖啡。"), 0)

    def test_build_context_accepts_injected_token_counter(self) -> None:
        class FixedTokenCounter:
            def count(self, text: str) -> int:
                return 4 if "small" in text else 100

        assembler = ContextAssembler(token_counter=FixedTokenCounter())

        bundle = assembler.build_context(
            [
                make_result("event-1", "small memory", score=20.0),
                make_result("event-2", "large memory", score=10.0),
            ],
            task={"id": "task-1"},
            budget=ContextBudget(max_tokens=14, safety_reserve_tokens=5, output_reserve_tokens=5),
            caller="calendar_agent",
        )

        self.assertEqual([snippet.event_id for snippet in bundle.snippets], ["event-1"])
        self.assertEqual(bundle.token_budget.used_tokens, 4)
        self.assertEqual(bundle.omitted_memory, [{"event_id": "event-2", "reason": "budget_exhausted"}])

    def test_context_build_can_write_audit_record(self) -> None:
        now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        ids = count(1)
        store = SQLiteMemoryStore.connect(":memory:")
        self.addCleanup(store.close)
        store.initialize_schema()
        audit = AuditLog(
            store,
            clock=lambda: now,
            id_factory=lambda: f"audit-{next(ids)}",
        )
        assembler = ContextAssembler(audit_log=audit)

        assembler.build_context(
            [make_result("event-1", "User prefers morning planning sessions.")],
            task={"id": "task-1"},
            budget=ContextBudget(max_tokens=80, safety_reserve_tokens=10, output_reserve_tokens=20),
            caller="calendar_agent",
        )

        records = audit.query(
            AuditSelector(caller="calendar_agent", operations=[AuditOperation.CONTEXT_BUILD])
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].affected_event_ids, ["event-1"])

    def test_build_context_adds_hot_memory_capsules_from_authorized_snippets(self) -> None:
        assembler = ContextAssembler()

        bundle = assembler.build_context(
            [
                make_snippet_result(
                    "event-1",
                    "User prefers morning planning sessions.",
                    attribution="user_stated",
                    confidence=0.96,
                ),
                make_snippet_result(
                    "event-2",
                    "User decided to move the launch review to Friday.",
                    confidence=0.91,
                ),
                make_snippet_result(
                    "event-3",
                    "When calendar sync fails twice, retry after refreshing credentials.",
                    attribution="agent_inferred",
                    confidence=0.86,
                    memory_layer="procedural",
                ),
            ],
            task={"id": "task-1"},
            budget=ContextBudget(max_tokens=150, safety_reserve_tokens=10, output_reserve_tokens=20),
            caller="calendar_agent",
        )

        capsule_categories = [capsule.category for capsule in bundle.hot_memory_capsules]
        self.assertIn("stable_user_confirmed_fact", capsule_categories)
        self.assertIn("recent_decision", capsule_categories)
        self.assertIn("procedural_candidate", capsule_categories)
        self.assertEqual(bundle.hot_memory_capsules[0].lifecycle_state, "active")
        self.assertEqual(bundle.hot_memory_capsules[0].evidence_event_ids, ["event-1"])
        self.assertEqual(bundle.safety_metadata["capsule_budget"]["separate_from_snippets"], True)

    def test_capsules_include_budget_omission_reasons_under_separate_budget(self) -> None:
        class FixedTokenCounter:
            def count(self, text: str) -> int:
                if text.startswith("capsule:"):
                    return 4
                return 4 if "short" in text else 100

        assembler = ContextAssembler(token_counter=FixedTokenCounter())

        bundle = assembler.build_context(
            [
                make_snippet_result("event-1", "short memory", confidence=0.95),
                make_snippet_result("event-2", "large memory", confidence=0.95),
            ],
            task={"id": "task-1"},
            budget=ContextBudget(max_tokens=18, safety_reserve_tokens=5, output_reserve_tokens=5),
            caller="calendar_agent",
        )

        self.assertEqual(bundle.omitted_memory, [{"event_id": "event-2", "reason": "budget_exhausted"}])
        self.assertEqual(bundle.hot_memory_capsules[0].omitted_memory, bundle.omitted_memory)
        self.assertEqual(bundle.safety_metadata["capsule_budget"]["used_tokens"], 4)
        self.assertEqual(bundle.token_budget.used_tokens, 4)

    def test_build_context_accepts_bounded_relation_paths_as_auditable_context(self) -> None:
        assembler = ContextAssembler()
        relation_path = RelationPath(
            nodes=["Mira", "Project Atlas", "credential refresh"],
            edge_types=["person_assigned_to_project", "solved_by"],
            evidence_event_ids=["event-2", "event-3"],
            compression_score=0.67,
        )

        bundle = assembler.build_context(
            [make_result("event-1", "User prefers morning planning sessions.")],
            task={"id": "task-1"},
            budget=ContextBudget(max_tokens=80, safety_reserve_tokens=10, output_reserve_tokens=20),
            caller="calendar_agent",
            relation_paths=[relation_path],
        )

        self.assertEqual(bundle.relation_paths, [relation_path])
        self.assertEqual(bundle.evidence_event_ids, ["event-1", "event-2", "event-3"])
        self.assertEqual(
            bundle.safety_metadata["relation_projection"],
            {
                "bounded": True,
                "path_count": 1,
                "evidence_event_ids": ["event-2", "event-3"],
            },
        )


if __name__ == "__main__":
    unittest.main()
