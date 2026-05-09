from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from itertools import count
import unittest

from phone_mem.governance.audit import AuditLog, AuditSelector
from phone_mem.governance.permissions import PermissionScope, PermissionService
from phone_mem.governance.views import MemoryViewProjector
from phone_mem.personal_memory_service.events import (
    AuditOperation,
    Lifecycle,
    LifecycleState,
    MemoryLayer,
    MemorySelector,
    PrivacyLevel,
)
from phone_mem.personal_memory_service.retrieval import HybridRetrievalWeights, LocalMemoryRetriever
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore
from tests.test_storage import make_event


def make_retrieval_stack() -> tuple[SQLiteMemoryStore, PermissionService, AuditLog]:
    now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
    ids = count(1)
    store = SQLiteMemoryStore.connect(":memory:")
    store.initialize_schema()
    permissions = PermissionService(
        store,
        clock=lambda: now,
        id_factory=lambda: f"grant-{next(ids)}",
    )
    audit = AuditLog(
        store,
        clock=lambda: now,
        id_factory=lambda: f"audit-{next(ids)}",
    )
    return store, permissions, audit


class LocalMemoryRetrieverTest(unittest.TestCase):
    def test_permission_projection_happens_before_ranking(self) -> None:
        store, permissions, audit = make_retrieval_stack()
        self.addCleanup(store.close)
        authorized = replace(
            make_event("event-1", app="system_assistant", entity="planning"),
            semantic_description="User prefers morning planning sessions.",
        )
        denied = replace(
            make_event("event-2", app="health", entity="health"),
            semantic_description="User takes insulin before breakfast.",
        )
        store.insert_event(authorized)
        store.insert_event(denied)
        permissions.grant(
            "calendar_agent",
            PermissionScope(
                operations=[AuditOperation.READ],
                apps=["system_assistant"],
                privacy_levels=[PrivacyLevel.PERSONAL],
            ),
            duration_seconds=60,
        )
        retriever = LocalMemoryRetriever(
            store=store,
            projector=MemoryViewProjector(permissions),
            audit_log=audit,
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC),
        )

        results = retriever.search("insulin", caller="calendar_agent")

        self.assertEqual(results, [])
        denied_records = audit.query(AuditSelector(caller="calendar_agent"))
        self.assertEqual(denied_records[0].outcome, "denied")
        self.assertEqual(denied_records[0].affected_event_ids, ["event-2"])

    def test_deleted_and_superseded_events_are_excluded(self) -> None:
        store, permissions, audit = make_retrieval_stack()
        self.addCleanup(store.close)
        active = replace(
            make_event("event-1", entity="travel"),
            semantic_description="User prefers aisle seats for flights.",
        )
        deleted = replace(
            make_event("event-2", entity="travel"),
            semantic_description="User prefers window seats for flights.",
            lifecycle=Lifecycle().mark_deleted(
                deleted_at=datetime(2026, 5, 2, 9, 0, tzinfo=UTC),
                reason="user corrected preference",
            ),
        )
        superseded = replace(
            make_event("event-3", entity="travel"),
            semantic_description="User prefers middle seats for flights.",
            lifecycle=Lifecycle(state=LifecycleState.SUPERSEDED),
        )
        store.insert_event(active)
        store.insert_event(deleted)
        store.insert_event(superseded)
        permissions.grant(
            "travel_agent",
            PermissionScope(operations=[AuditOperation.READ], entities=["travel"]),
            duration_seconds=60,
        )
        retriever = LocalMemoryRetriever(
            store=store,
            projector=MemoryViewProjector(permissions),
            audit_log=audit,
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC),
        )

        results = retriever.search("flights seats", caller="travel_agent")

        self.assertEqual([result.event_id for result in results], ["event-1"])

    def test_scoring_is_deterministic_and_preserves_explanation_metadata(self) -> None:
        store, permissions, audit = make_retrieval_stack()
        self.addCleanup(store.close)
        weaker = replace(
            make_event("event-1", entity="planning"),
            semantic_description="User mentioned planning.",
        )
        stronger = replace(
            make_event("event-2", entity="planning"),
            semantic_description="User prefers morning planning and calendar planning.",
        )
        store.insert_event(weaker)
        store.insert_event(stronger)
        permissions.grant(
            "calendar_agent",
            PermissionScope(operations=[AuditOperation.READ], entities=["planning"]),
            duration_seconds=60,
        )
        retriever = LocalMemoryRetriever(
            store=store,
            projector=MemoryViewProjector(permissions),
            audit_log=audit,
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC),
        )

        results = retriever.search(
            "morning planning",
            caller="calendar_agent",
            selector=MemorySelector(memory_layers=[MemoryLayer.EPISODIC]),
            top_k=1,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].event_id, "event-2")
        self.assertGreater(results[0].score, 0)
        self.assertEqual(results[0].snippet.event_id, "event-2")
        self.assertEqual(results[0].snippet.confidence, stronger.quality.confidence)
        self.assertEqual(results[0].explanation["matched_terms"], ["morning", "planning"])

    def test_default_query_expansion_matches_basic_preference_synonyms(self) -> None:
        store, permissions, audit = make_retrieval_stack()
        self.addCleanup(store.close)
        event = replace(
            make_event("event-1", entity="planning"),
            semantic_description="User prefers morning planning sessions.",
        )
        store.insert_event(event)
        permissions.grant(
            "calendar_agent",
            PermissionScope(operations=[AuditOperation.READ], entities=["planning"]),
            duration_seconds=60,
        )
        retriever = LocalMemoryRetriever(
            store=store,
            projector=MemoryViewProjector(permissions),
            audit_log=audit,
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC),
        )

        results = retriever.search("likes morning planning", caller="calendar_agent")

        self.assertEqual([result.event_id for result in results], ["event-1"])
        self.assertIn("prefers", results[0].explanation["expanded_terms"])

    def test_chinese_query_matches_chinese_memory_text(self) -> None:
        store, permissions, audit = make_retrieval_stack()
        self.addCleanup(store.close)
        coffee = replace(
            make_event("event-1", entity="coffee"),
            semantic_description="用户喜欢早上9点喝咖啡。",
            entities=["咖啡"],
        )
        store.insert_event(coffee)
        permissions.grant(
            "assistant_agent",
            PermissionScope(operations=[AuditOperation.READ], entities=["咖啡"]),
            duration_seconds=60,
        )
        retriever = LocalMemoryRetriever(
            store=store,
            projector=MemoryViewProjector(permissions),
            audit_log=audit,
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC),
        )

        results = retriever.search("我喜欢几点喝咖啡", caller="assistant_agent")

        self.assertEqual([result.event_id for result in results], ["event-1"])
        self.assertIn("喝咖啡", results[0].explanation["matched_terms"])

    def test_hybrid_ranking_explains_bm25_and_weighted_score_components(self) -> None:
        store, permissions, audit = make_retrieval_stack()
        self.addCleanup(store.close)
        weak = replace(
            make_event("event-1", entity="planning"),
            semantic_description="User mentioned planning.",
        )
        strong_bm25 = replace(
            make_event("event-2", entity="planning"),
            semantic_description="planning planning planning launch review",
        )
        store.insert_event(weak)
        store.insert_event(strong_bm25)
        permissions.grant(
            "calendar_agent",
            PermissionScope(operations=[AuditOperation.READ], entities=["planning"]),
            duration_seconds=60,
        )
        retriever = LocalMemoryRetriever(
            store=store,
            projector=MemoryViewProjector(permissions),
            audit_log=audit,
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC),
            weights=HybridRetrievalWeights(lexical=0.2, bm25=1.0, entity=0.0),
        )

        results = retriever.search("planning launch", caller="calendar_agent")

        self.assertEqual(results[0].event_id, "event-2")
        self.assertIn("bm25_score", results[0].explanation)
        self.assertIn("score_components", results[0].explanation)
        self.assertEqual(results[0].explanation["score_weights"]["bm25"], 1.0)
        self.assertGreater(results[0].explanation["score_components"]["bm25"], 0.0)

    def test_vector_ranker_runs_after_permission_filtering(self) -> None:
        class RecordingVectorRanker:
            def __init__(self) -> None:
                self.seen_event_ids: list[str] = []

            def rank(self, query: str, events: list[object]) -> dict[str, float]:
                self.seen_event_ids = [event.event_id for event in events]
                return {event.event_id: 1.0 for event in events}

        store, permissions, audit = make_retrieval_stack()
        self.addCleanup(store.close)
        authorized = replace(
            make_event("event-1", app="system_assistant", entity="planning"),
            semantic_description="User prefers morning planning sessions.",
        )
        denied = replace(
            make_event("event-2", app="health", entity="health"),
            semantic_description="User takes insulin before breakfast.",
        )
        store.insert_event(authorized)
        store.insert_event(denied)
        permissions.grant(
            "calendar_agent",
            PermissionScope(
                operations=[AuditOperation.READ],
                apps=["system_assistant"],
                privacy_levels=[PrivacyLevel.PERSONAL],
            ),
            duration_seconds=60,
        )
        vector_ranker = RecordingVectorRanker()
        retriever = LocalMemoryRetriever(
            store=store,
            projector=MemoryViewProjector(permissions),
            audit_log=audit,
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC),
            vector_ranker=vector_ranker,
            weights=HybridRetrievalWeights(lexical=0.0, bm25=0.0, vector=1.0),
        )

        results = retriever.search("insulin planning", caller="calendar_agent")

        self.assertEqual(vector_ranker.seen_event_ids, ["event-1"])
        self.assertEqual([result.event_id for result in results], ["event-1"])
        self.assertEqual(results[0].explanation["score_components"]["vector"], 1.0)

    def test_mmr_diversifies_top_k_when_high_ranked_results_share_entities(self) -> None:
        store, permissions, audit = make_retrieval_stack()
        self.addCleanup(store.close)
        launch_first = replace(
            make_event("event-1", entity="launch"),
            semantic_description="planning launch checklist review",
            entities=["launch"],
        )
        launch_duplicate = replace(
            make_event("event-2", entity="launch"),
            semantic_description="planning launch checklist review followup",
            entities=["launch"],
        )
        calendar = replace(
            make_event("event-3", entity="calendar"),
            semantic_description="planning calendar review",
            entities=["calendar"],
        )
        store.insert_event(launch_first)
        store.insert_event(launch_duplicate)
        store.insert_event(calendar)
        permissions.grant(
            "calendar_agent",
            PermissionScope(operations=[AuditOperation.READ], entities=["launch", "calendar"]),
            duration_seconds=60,
        )
        retriever = LocalMemoryRetriever(
            store=store,
            projector=MemoryViewProjector(permissions),
            audit_log=audit,
            clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC),
        )

        results = retriever.search("planning review", caller="calendar_agent", top_k=2)

        self.assertEqual([result.event_id for result in results], ["event-1", "event-3"])
        self.assertLess(results[1].explanation["mmr_diversity_penalty"], 0.5)


if __name__ == "__main__":
    unittest.main()
