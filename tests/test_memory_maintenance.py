from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import unittest

from phone_mem.personal_memory_service.constructor import MemoryCandidate
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    EventType,
    Lifecycle,
    LifecycleState,
    Lineage,
    MemoryLayer,
    Modality,
)
from phone_mem.personal_memory_service.service import PersonalMemoryService


ROOT = Path(__file__).resolve().parents[1]


class MemoryMaintenanceTest(unittest.TestCase):
    def test_reflect_dry_run_proposes_semantic_and_procedural_candidates_without_writing(self) -> None:
        service = PersonalMemoryService.in_memory(clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC))
        self.addCleanup(service.close)
        self._insert_candidate(
            service,
            "User prefers morning planning sessions.",
            entities=["planning"],
            attribution=Attribution.USER_STATED,
        )
        self._insert_candidate(
            service,
            "User wants calendar summaries before lunch.",
            entities=["planning"],
            attribution=Attribution.USER_STATED,
        )
        self._insert_candidate(
            service,
            "When calendar sync fails twice, retry after refreshing credentials.",
            entities=["calendar_sync"],
            attribution=Attribution.AGENT_INFERRED,
        )
        before_event_ids = [event.event_id for event in service.store.query_events()]

        report = service.reflect()

        self.assertEqual([event.event_id for event in service.store.query_events()], before_event_ids)
        self.assertEqual(
            [proposal.memory_layer for proposal in report.proposals],
            [MemoryLayer.SEMANTIC.value, MemoryLayer.PROCEDURAL.value],
        )
        self.assertTrue(all(proposal.review_required for proposal in report.proposals))
        self.assertEqual(report.proposals[0].proposal_type, "semantic_candidate")
        self.assertEqual(report.proposals[0].entities, ["planning"])
        self.assertEqual(report.proposals[0].evidence_event_ids, ["event-1", "event-2"])
        self.assertEqual(report.proposals[1].proposal_type, "procedural_candidate")
        self.assertEqual(report.proposals[1].evidence_event_ids, ["event-3"])

    def test_defrag_reports_duplicates_missing_lineage_and_orphaned_projection_edges(self) -> None:
        service = PersonalMemoryService.in_memory(clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC))
        self.addCleanup(service.close)
        self._insert_candidate(service, "User prefers morning planning sessions.", entities=["planning"])
        self._insert_candidate(service, "User prefers morning planning sessions.", entities=["planning"])
        self._insert_candidate(
            service,
            "Derived planning summary.",
            entities=["planning"],
            event_type=EventType.DERIVED_SUMMARY,
            lineage=Lineage(derived_from=["missing-event"]),
        )
        service.store.connection.execute(
            """
            insert into relation_edges (
                edge_id, source_node, source_type, relation_type, target_node, target_type,
                source_event_id, evidence_event_ids_json, lifecycle_state
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "orphan-edge",
                "Mira",
                "person",
                "person_assigned_to_project",
                "Project Atlas",
                "project",
                "missing-event",
                '["missing-event"]',
                LifecycleState.ACTIVE.value,
            ),
        )

        report = service.defrag()

        self.assertEqual(report.duplicate_event_groups, [["event-1", "event-2"]])
        self.assertEqual(report.missing_lineage, [{"event_id": "event-3", "missing_event_id": "missing-event"}])
        self.assertEqual(report.orphaned_projection_edges, ["orphan-edge"])
        self.assertEqual(report.actions_require_review, True)

    def test_defrag_reports_stale_superseded_chains(self) -> None:
        service = PersonalMemoryService.in_memory(clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC))
        self.addCleanup(service.close)
        self._insert_candidate(service, "User prefers morning planning sessions.", entities=["planning"])
        self._insert_candidate(
            service,
            "User prefers afternoon planning sessions.",
            entities=["planning"],
            lineage=Lineage(parents=["event-1"], supersedes=["event-1"]),
        )
        self._insert_candidate(
            service,
            "User prefers evening planning sessions.",
            entities=["planning"],
            lineage=Lineage(parents=["event-2"], supersedes=["event-2"]),
        )
        service.store.update_lifecycle("event-1", Lifecycle(state=LifecycleState.SUPERSEDED))
        service.store.update_lifecycle("event-2", Lifecycle(state=LifecycleState.SUPERSEDED))

        report = service.defrag()

        self.assertEqual(report.stale_superseded_chains, [["event-1", "event-2", "event-3"]])

    def test_schema_diff_compares_observed_fields_and_relation_types_against_data_doc(self) -> None:
        service = PersonalMemoryService.in_memory(clock=lambda: datetime(2026, 5, 3, 9, 0, tzinfo=UTC))
        self.addCleanup(service.close)
        self._insert_candidate(
            service,
            "Mira is assigned to Project Atlas.",
            entities=["Mira", "Project Atlas"],
            relations=[
                {
                    "type": "unsupported_custom_link",
                    "source": "Mira",
                    "target": "Project Atlas",
                }
            ],
        )

        report = service.schema_diff(data_doc_path=ROOT / "docs" / "DATA.md")

        self.assertEqual(report.missing_documented_fields, [])
        self.assertEqual(report.unexpected_event_fields, [])
        self.assertEqual(report.unexpected_relation_types, ["unsupported_custom_link"])

    def _insert_candidate(
        self,
        service: PersonalMemoryService,
        semantic_description: str,
        *,
        entities: list[str],
        attribution: Attribution = Attribution.USER_STATED,
        event_type: EventType = EventType.USER_UTTERANCE,
        lineage: Lineage | None = None,
        relations: list[dict[str, object]] | None = None,
    ) -> str:
        event = service.constructor.construct(
            MemoryCandidate(
                semantic_description=semantic_description,
                source_app="system_assistant",
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=attribution,
                event_type=event_type,
                entities=entities,
                lineage=lineage or Lineage(),
                relations=list(relations or []),
            )
        )
        service.store.insert_event(event)
        return event.event_id


if __name__ == "__main__":
    unittest.main()
