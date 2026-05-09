from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReflectionProposal:
    proposal_type: str
    memory_layer: str
    summary: str
    entities: list[str]
    evidence_event_ids: list[str]
    confidence: float
    review_required: bool = True


@dataclass(frozen=True)
class ReflectionReport:
    proposals: list[ReflectionProposal]
    mutates_store: bool = False


@dataclass(frozen=True)
class DefragReport:
    duplicate_event_groups: list[list[str]]
    stale_superseded_chains: list[list[str]]
    missing_lineage: list[dict[str, str]]
    orphaned_projection_edges: list[str]
    actions_require_review: bool
    mutates_store: bool = False


@dataclass(frozen=True)
class SchemaDiffReport:
    missing_documented_fields: list[str]
    unexpected_event_fields: list[str]
    unexpected_relation_types: list[str]
    mutates_store: bool = False
