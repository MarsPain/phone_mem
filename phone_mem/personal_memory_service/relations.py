from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from phone_mem.personal_memory_service.events import MemoryEvent


@dataclass(frozen=True)
class RelationNode:
    node: str
    node_type: str

    def to_dict(self) -> dict[str, str]:
        return {"node": self.node, "node_type": self.node_type}


@dataclass(frozen=True)
class RelationEdge:
    edge_id: str
    source_node: str
    source_type: str
    relation_type: str
    target_node: str
    target_type: str
    evidence_event_ids: list[str]
    lifecycle_state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "edge_id": self.edge_id,
            "source_node": self.source_node,
            "source_type": self.source_type,
            "relation_type": self.relation_type,
            "target_node": self.target_node,
            "target_type": self.target_type,
            "evidence_event_ids": list(self.evidence_event_ids),
            "lifecycle_state": self.lifecycle_state,
        }


@dataclass(frozen=True)
class RelationPath:
    nodes: list[str]
    edge_types: list[str]
    evidence_event_ids: list[str]
    compression_score: float

    def to_dict(self) -> dict[str, object]:
        return {
            "nodes": list(self.nodes),
            "edge_types": list(self.edge_types),
            "evidence_event_ids": list(self.evidence_event_ids),
            "compression_score": self.compression_score,
        }


@dataclass(frozen=True)
class RelationProjection:
    nodes: list[RelationNode]
    edges: list[RelationEdge]


class RelationProjectionBuilder:
    def build_for_event(self, event: MemoryEvent) -> RelationProjection:
        nodes_by_key: dict[str, RelationNode] = {}
        edges: list[RelationEdge] = []

        for relation in event.relations:
            edge = self._edge_from_relation(event, relation)
            if edge is None:
                continue
            edges.append(edge)
            nodes_by_key[edge.source_node] = RelationNode(edge.source_node, edge.source_type)
            nodes_by_key[edge.target_node] = RelationNode(edge.target_node, edge.target_type)

        for relation_type, targets in (
            ("lineage_parent", event.lineage.parents),
            ("derived_from", event.lineage.derived_from),
            ("supersedes", event.lineage.supersedes),
        ):
            for target_event_id in targets:
                edge = self._lineage_edge(event, relation_type, target_event_id)
                edges.append(edge)
                nodes_by_key[edge.source_node] = RelationNode(edge.source_node, edge.source_type)
                nodes_by_key[edge.target_node] = RelationNode(edge.target_node, edge.target_type)

        return RelationProjection(
            nodes=sorted(nodes_by_key.values(), key=lambda node: (node.node_type, node.node)),
            edges=sorted(edges, key=lambda edge: edge.edge_id),
        )

    def _edge_from_relation(
        self,
        event: MemoryEvent,
        relation: dict[str, Any],
    ) -> RelationEdge | None:
        relation_type = self._clean_text(relation.get("type"))
        source = self._clean_text(relation.get("source"))
        target = self._clean_text(relation.get("target"))
        if relation_type is None or source is None or target is None:
            return None

        source_type = self._clean_text(relation.get("source_type")) or self._classify_node(source)
        target_type = self._clean_text(relation.get("target_type")) or self._classify_node(target)
        return RelationEdge(
            edge_id=f"{event.event_id}:{relation_type}:{source}:{target}",
            source_node=source,
            source_type=source_type,
            relation_type=relation_type,
            target_node=target,
            target_type=target_type,
            evidence_event_ids=[event.event_id],
            lifecycle_state=event.lifecycle.state.value,
        )

    def _lineage_edge(
        self,
        event: MemoryEvent,
        relation_type: str,
        target_event_id: str,
    ) -> RelationEdge:
        source_node = f"event:{event.event_id}"
        target_node = f"event:{target_event_id}"
        return RelationEdge(
            edge_id=f"{event.event_id}:{relation_type}:{source_node}:{target_node}",
            source_node=source_node,
            source_type="memory_event",
            relation_type=relation_type,
            target_node=target_node,
            target_type="memory_event",
            evidence_event_ids=[event.event_id, target_event_id],
            lifecycle_state=event.lifecycle.state.value,
        )

    def _clean_text(self, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    def _classify_node(self, value: str) -> str:
        lowered = value.lower()
        if self._looks_like_person(value):
            return "person"
        if "project" in lowered:
            return "project"
        if "decision" in lowered or "decided" in lowered:
            return "decision"
        if "task" in lowered or "todo" in lowered:
            return "task"
        if "tool" in lowered or "api" in lowered or "script" in lowered:
            return "tool"
        if "error" in lowered or "bug" in lowered or "fail" in lowered:
            return "error"
        return "entity"

    def _looks_like_person(self, value: str) -> bool:
        return bool(re.fullmatch(r"[A-Z][a-z]+(?: [A-Z][a-z]+)?", value))
