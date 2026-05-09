from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
from typing import Any

from phone_mem.personal_memory_service.events import (
    Attribution,
    LifecycleState,
    MemoryEvent,
    MemoryLayer,
    MemorySelector,
)
from phone_mem.personal_memory_service.maintenance_reports import (
    DefragReport,
    ReflectionProposal,
    ReflectionReport,
    SchemaDiffReport,
)
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore


class MemoryMaintenance:
    _known_relation_types = {
        "derived_from",
        "lineage_parent",
        "person_assigned_to_project",
        "review_policy",
        "solved_by",
        "supersedes",
        "tool_supports_project",
    }

    def __init__(self, store: SQLiteMemoryStore) -> None:
        self._store = store

    def reflect(self) -> ReflectionReport:
        events = self._store.query_events(
            MemorySelector(
                memory_layers=[MemoryLayer.EPISODIC],
                lifecycle_states=[LifecycleState.ACTIVE],
            )
        )
        proposals = [*self._semantic_proposals(events), *self._procedural_proposals(events)]
        return ReflectionReport(proposals=proposals)

    def defrag(self) -> DefragReport:
        events = self._store.query_events()
        report = DefragReport(
            duplicate_event_groups=self._duplicate_groups(events),
            stale_superseded_chains=self._stale_superseded_chains(events),
            missing_lineage=self._missing_lineage(events),
            orphaned_projection_edges=self._orphaned_projection_edges(),
            actions_require_review=True,
        )
        return report

    def schema_diff(self, *, data_doc_path: Path | None = None) -> SchemaDiffReport:
        events = self._store.query_events()
        expected_fields = self._documented_event_fields(data_doc_path)
        observed_fields = sorted({key for event in events for key in event.to_dict()})
        observed_relation_types = sorted(
            {
                str(relation["type"])
                for event in events
                for relation in event.relations
                if isinstance(relation.get("type"), str)
            }
        )
        return SchemaDiffReport(
            missing_documented_fields=[
                field for field in expected_fields if observed_fields and field not in observed_fields
            ],
            unexpected_event_fields=[
                field for field in observed_fields if expected_fields and field not in expected_fields
            ],
            unexpected_relation_types=[
                relation_type
                for relation_type in observed_relation_types
                if relation_type not in self._known_relation_types
            ],
        )

    def _semantic_proposals(self, events: list[MemoryEvent]) -> list[ReflectionProposal]:
        grouped: dict[tuple[str, ...], list[MemoryEvent]] = defaultdict(list)
        for event in events:
            if event.source.attribution != Attribution.USER_STATED:
                continue
            if event.quality.confidence < 0.85:
                continue
            grouped[tuple(event.entities)].append(event)
        proposals: list[ReflectionProposal] = []
        for entities, group in sorted(grouped.items()):
            if len(group) < 2:
                continue
            proposals.append(
                ReflectionProposal(
                    proposal_type="semantic_candidate",
                    memory_layer=MemoryLayer.SEMANTIC.value,
                    summary=f"Semantic candidate from {len(group)} episodic memories.",
                    entities=list(entities),
                    evidence_event_ids=[event.event_id for event in group],
                    confidence=round(min(event.quality.confidence for event in group), 3),
                )
            )
        return proposals

    def _procedural_proposals(self, events: list[MemoryEvent]) -> list[ReflectionProposal]:
        proposals: list[ReflectionProposal] = []
        for event in events:
            text = event.semantic_description.lower()
            if not (text.startswith("when ") or " retry " in text):
                continue
            proposals.append(
                ReflectionProposal(
                    proposal_type="procedural_candidate",
                    memory_layer=MemoryLayer.PROCEDURAL.value,
                    summary="Procedural candidate from episodic task pattern.",
                    entities=list(event.entities),
                    evidence_event_ids=[event.event_id],
                    confidence=event.quality.confidence,
                )
            )
        return proposals

    def _duplicate_groups(self, events: list[MemoryEvent]) -> list[list[str]]:
        groups: dict[tuple[object, ...], list[str]] = defaultdict(list)
        for event in events:
            if event.lifecycle.state != LifecycleState.ACTIVE:
                continue
            groups[
                (
                    event.source.app,
                    event.memory_layer.value,
                    tuple(sorted(event.entities)),
                    self._normalized(event.semantic_description),
                )
            ].append(event.event_id)
        return sorted(sorted(ids) for ids in groups.values() if len(ids) > 1)

    def _missing_lineage(self, events: list[MemoryEvent]) -> list[dict[str, str]]:
        existing_ids = {event.event_id for event in events}
        missing: list[dict[str, str]] = []
        for event in events:
            references = [
                *event.lineage.parents,
                *event.lineage.derived_from,
                *event.lineage.supersedes,
            ]
            for referenced_id in references:
                if referenced_id not in existing_ids:
                    missing.append({"event_id": event.event_id, "missing_event_id": referenced_id})
        return missing

    def _stale_superseded_chains(self, events: list[MemoryEvent]) -> list[list[str]]:
        by_id = {event.event_id: event for event in events}
        chains: list[list[str]] = []
        for event in events:
            if event.lifecycle.state != LifecycleState.SUPERSEDED:
                continue
            chain = [event.event_id]
            current_id = event.event_id
            while superseding := self._store.events_superseding(current_id):
                current_id = superseding[0]
                chain.append(current_id)
                current = by_id.get(current_id)
                if current is None or current.lifecycle.state != LifecycleState.SUPERSEDED:
                    break
            if len(chain) > 2:
                chains.append(chain)
        return chains

    def _orphaned_projection_edges(self) -> list[str]:
        rows = self._store.connection.execute(
            """
            select re.edge_id
            from relation_edges re
            left join memory_events me on me.event_id = re.source_event_id
            where me.event_id is null
            order by re.edge_id
            """
        ).fetchall()
        return [row["edge_id"] for row in rows]

    def _documented_event_fields(self, data_doc_path: Path | None) -> list[str]:
        data_doc_path = data_doc_path or Path(__file__).resolve().parents[2] / "docs" / "DATA.md"
        if not data_doc_path.exists():
            return []
        match = re.search(r"```json\n(?P<json>\{.*?\})\n```", data_doc_path.read_text(), re.S)
        if match is None:
            return []
        data: dict[str, Any] = json.loads(match.group("json"))
        return sorted(data)

    def _normalized(self, value: str) -> str:
        return " ".join(value.lower().split())
