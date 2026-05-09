from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import re
from typing import Any, Protocol

from phone_mem.governance.audit import AuditLog
from phone_mem.governance.views import MemoryViewProjector
from phone_mem.personal_memory_service.events import (
    AuditOperation,
    LifecycleState,
    MemoryEvent,
    MemorySelector,
)

DEFAULT_TERM_EXPANSIONS: dict[str, list[str]] = {
    "like": ["prefers"],
    "likes": ["prefers"],
    "prefer": ["likes"],
    "prefers": ["likes"],
    "喜欢": ["prefers", "likes"],
    "偏好": ["prefers", "likes"],
    "早上": ["morning"],
    "上午": ["morning"],
    "下午": ["afternoon"],
    "晚上": ["evening"],
}


@dataclass(frozen=True)
class MemorySnippet:
    event_id: str
    text: str
    source_app: str
    attribution: str
    confidence: float
    memory_layer: str
    privacy_level: str
    evidence_event_ids: list[str]


@dataclass(frozen=True)
class RetrievalResult:
    event_id: str
    score: float
    snippet: MemorySnippet
    explanation: dict[str, Any]


@dataclass(frozen=True)
class HybridRetrievalWeights:
    lexical: float = 1.0
    bm25: float = 0.3
    vector: float = 0.7
    entity: float = 1.0
    recency: float = 1.0
    confidence: float = 1.0
    importance: float = 1.0
    mmr_lambda: float = 0.7

    def to_dict(self) -> dict[str, float]:
        return {
            "lexical": self.lexical,
            "bm25": self.bm25,
            "vector": self.vector,
            "entity": self.entity,
            "recency": self.recency,
            "confidence": self.confidence,
            "importance": self.importance,
            "mmr_lambda": self.mmr_lambda,
        }


class VectorRanker(Protocol):
    def rank(self, query: str, events: list[MemoryEvent]) -> dict[str, float]:
        raise NotImplementedError


class LocalMemoryRetriever:
    def __init__(
        self,
        *,
        store: object,
        projector: MemoryViewProjector,
        audit_log: AuditLog,
        clock: Callable[[], datetime] | None = None,
        weights: HybridRetrievalWeights | None = None,
        vector_ranker: VectorRanker | None = None,
    ) -> None:
        self._store = store
        self._projector = projector
        self._audit_log = audit_log
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._weights = weights or HybridRetrievalWeights()
        self._vector_ranker = vector_ranker

    def search(
        self,
        query: str,
        *,
        caller: str,
        selector: MemorySelector | None = None,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        active_selector = self._active_selector(selector)
        candidate_events = self._store.query_events(active_selector)
        view = self._projector.project(
            caller,
            AuditOperation.READ,
            candidate_events,
            at=self._clock(),
        )
        self._record_denials(caller, query, active_selector, view.denied_event_ids)

        authorized_event_ids = [event.event_id for event in view.events]
        bm25_scores = self._bm25_scores(query, authorized_event_ids)
        vector_scores = self._vector_scores(query, view.events)
        results = [
            result
            for event in view.events
            if (
                result := self._score_event(
                    query,
                    event,
                    bm25_score=bm25_scores.get(event.event_id, 0.0),
                    vector_score=vector_scores.get(event.event_id, 0.0),
                )
            )
            is not None
        ]
        results.sort(key=lambda result: (-result.score, result.event_id))
        selected = self._select_mmr(results, top_k=max(top_k, 0))
        self._audit_log.record(
            caller=caller,
            operation=AuditOperation.READ,
            scope=self._audit_scope(query, active_selector, top_k),
            affected_event_ids=[result.event_id for result in selected],
            outcome="allowed",
        )
        return selected

    def _active_selector(self, selector: MemorySelector | None) -> MemorySelector:
        if selector is None:
            return MemorySelector(lifecycle_states=[LifecycleState.ACTIVE])
        return replace(selector, lifecycle_states=[LifecycleState.ACTIVE])

    def _record_denials(
        self,
        caller: str,
        query: str,
        selector: MemorySelector,
        denied_event_ids: dict[str, str],
    ) -> None:
        for event_id, reason in sorted(denied_event_ids.items()):
            self._audit_log.record(
                caller=caller,
                operation=AuditOperation.READ,
                scope=self._audit_scope(query, selector, None),
                affected_event_ids=[event_id],
                outcome="denied",
                denial_reason=reason,
            )

    def _score_event(
        self,
        query: str,
        event: MemoryEvent,
        *,
        bm25_score: float,
        vector_score: float,
    ) -> RetrievalResult | None:
        base_query_terms = self._terms(query)
        query_terms = self._expanded_terms(base_query_terms)
        event_terms = self._event_terms(event)
        matched_terms = [term for term in query_terms if term in event_terms]
        entity_matches = [entity for entity in event.entities if entity.lower() in query_terms]
        expanded_terms = [term for term in query_terms if term not in base_query_terms]
        lexical_score = sum(event_terms[term] for term in matched_terms)
        entity_score = len(entity_matches)
        if lexical_score == 0 and entity_score == 0 and bm25_score == 0 and vector_score == 0:
            return None

        recency_score = self._recency_score(event)
        score_components = {
            "lexical": float(lexical_score),
            "bm25": float(bm25_score),
            "vector": float(vector_score),
            "entity": float(entity_score),
            "recency": float(recency_score),
            "confidence": float(event.quality.confidence),
            "importance": float(event.quality.importance),
        }
        score = self._weighted_score(score_components)
        return RetrievalResult(
            event_id=event.event_id,
            score=round(score, 6),
            snippet=self._snippet(event),
            explanation={
                "matched_terms": matched_terms,
                "matched_entities": entity_matches,
                "expanded_terms": expanded_terms,
                "lexical_score": lexical_score,
                "bm25_score": bm25_score,
                "vector_score": vector_score,
                "recency_score": recency_score,
                "score_components": score_components,
                "score_weights": self._weights.to_dict(),
            },
        )

    def _weighted_score(self, components: dict[str, float]) -> float:
        return (
            components["lexical"] * self._weights.lexical * 10.0
            + components["bm25"] * self._weights.bm25 * 10.0
            + components["vector"] * self._weights.vector * 10.0
            + components["entity"] * self._weights.entity * 3.0
            + components["recency"] * self._weights.recency
            + components["confidence"] * self._weights.confidence * 2.0
            + components["importance"] * self._weights.importance * 2.0
        )

    def _bm25_scores(self, query: str, event_ids: list[str]) -> dict[str, float]:
        bm25 = getattr(self._store, "bm25_scores", None)
        if bm25 is None:
            return {}
        return dict(bm25(query, event_ids))

    def _vector_scores(self, query: str, events: list[MemoryEvent]) -> dict[str, float]:
        if self._vector_ranker is None:
            return {}
        return dict(self._vector_ranker.rank(query, events))

    def _select_mmr(self, results: list[RetrievalResult], *, top_k: int) -> list[RetrievalResult]:
        if top_k <= 0 or not results:
            return []
        selected: list[RetrievalResult] = []
        remaining = list(results)
        max_score = max(result.score for result in remaining) or 1.0

        while remaining and len(selected) < top_k:
            if not selected:
                result = remaining.pop(0)
                selected.append(self._with_mmr_penalty(result, 0.0))
                continue
            best_index = 0
            best_value: float | None = None
            best_penalty = 0.0
            for index, candidate in enumerate(remaining):
                penalty = max(
                    self._similarity(candidate, chosen)
                    for chosen in selected
                )
                value = (
                    self._weights.mmr_lambda * (candidate.score / max_score)
                    - (1.0 - self._weights.mmr_lambda) * penalty
                )
                if best_value is None or value > best_value:
                    best_index = index
                    best_value = value
                    best_penalty = penalty
            selected.append(self._with_mmr_penalty(remaining.pop(best_index), best_penalty))
        return selected

    def _with_mmr_penalty(self, result: RetrievalResult, penalty: float) -> RetrievalResult:
        explanation = dict(result.explanation)
        explanation["mmr_diversity_penalty"] = round(penalty, 6)
        return replace(result, explanation=explanation)

    def _similarity(self, left: RetrievalResult, right: RetrievalResult) -> float:
        left_terms = set(self._terms(left.snippet.text))
        right_terms = set(self._terms(right.snippet.text))
        if not left_terms or not right_terms:
            return 0.0
        overlap = len(left_terms.intersection(right_terms))
        union = len(left_terms.union(right_terms))
        return overlap / union

    def _snippet(self, event: MemoryEvent) -> MemorySnippet:
        return MemorySnippet(
            event_id=event.event_id,
            text=event.semantic_description,
            source_app=event.source.app,
            attribution=event.source.attribution.value,
            confidence=event.quality.confidence,
            memory_layer=event.memory_layer.value,
            privacy_level=event.privacy.level.value,
            evidence_event_ids=[event.event_id, *event.lineage.derived_from],
        )

    def _recency_score(self, event: MemoryEvent) -> float:
        age = self._clock() - event.valid_time.start
        age_days = max(age.total_seconds() / 86_400, 0.0)
        return round(1.0 / (1.0 + age_days), 6)

    def _event_terms(self, event: MemoryEvent) -> Counter[str]:
        terms = self._terms(event.semantic_description)
        terms.extend(entity.lower() for entity in event.entities)
        return Counter(terms)

    def _terms(self, text: str) -> list[str]:
        terms: list[str] = []
        for match in re.finditer(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.lower()):
            token = match.group(0)
            if re.fullmatch(r"[a-z0-9]+", token):
                terms.append(token)
                continue
            terms.extend(self._cjk_ngrams(token))
        return terms

    def _expanded_terms(self, terms: list[str]) -> list[str]:
        expanded: list[str] = []
        for term in terms:
            if term not in expanded:
                expanded.append(term)
            for synonym in DEFAULT_TERM_EXPANSIONS.get(term, []):
                if synonym not in expanded:
                    expanded.append(synonym)
        return expanded

    def _cjk_ngrams(self, text: str) -> list[str]:
        grams: list[str] = []
        max_size = min(4, len(text))
        for size in range(2, max_size + 1):
            for index in range(0, len(text) - size + 1):
                grams.append(text[index : index + size])
        if len(text) == 1:
            grams.append(text)
        return grams

    def _audit_scope(
        self,
        query: str,
        selector: MemorySelector,
        top_k: int | None,
    ) -> dict[str, object]:
        scope: dict[str, object] = {"query": query, "selector": selector.to_dict()}
        if top_k is not None:
            scope["top_k"] = top_k
        return scope
