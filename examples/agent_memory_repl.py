from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys
from typing import TextIO

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


CALLER = "interactive_memory_agent"
SOURCE_APP = "system_assistant"


class AgentMemoryRepl:
    def __init__(self) -> None:
        now = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        self._service = PersonalMemoryService.in_memory(clock=lambda: now)
        self._service.grant(CALLER, _scope(), duration_seconds=3_600)

    def execute(self, line: str) -> list[str]:
        command, argument = _split_command(line)
        if command == "":
            return []
        if command in {"quit", "exit"}:
            return ["bye"]
        if command == "help":
            return _help_lines()
        if command == "remember":
            return self._remember(argument)
        if command == "search":
            return self._search(argument)
        if command == "context":
            return self._context(argument)
        if command == "correct":
            return self._correct(argument)
        if command == "explain":
            return self._explain(argument)
        if command == "delete":
            return self._delete(argument)
        if command == "audit":
            return self._audit()
        if command == "metrics":
            return self._metrics()
        return [f"unknown command: {command}", "type 'help' for commands"]

    def close(self) -> None:
        self._service.close()

    def _remember(self, text: str) -> list[str]:
        if not text:
            return ["usage: remember <memory text>"]
        event_id = self._service.record(_candidate(text), caller=CALLER)
        return [f"remembered {event_id}: {text}"]

    def _search(self, query: str) -> list[str]:
        if not query:
            return ["usage: search <query>"]
        results = self._service.search(query, caller=CALLER, top_k=5)
        if not results:
            return ["no active memories matched"]
        lines = ["search results:"]
        for result in results:
            lines.append(
                f"{result.event_id} | {result.snippet.text} | score={result.score:.2f}"
            )
        return lines

    def _context(self, query: str) -> list[str]:
        if not query:
            return ["usage: context <query>"]
        bundle = self._service.build_context(
            query,
            caller=CALLER,
            task={"id": "interactive-task", "description": query},
            budget=ContextBudget(
                max_tokens=120,
                safety_reserve_tokens=10,
                output_reserve_tokens=30,
            ),
            top_k=5,
        )
        lines = [f"context evidence: {bundle.evidence_event_ids}"]
        if not bundle.snippets:
            lines.append("context snippets: none")
            return lines
        lines.append("context snippets:")
        for snippet in bundle.snippets:
            lines.append(f"{snippet.event_id} | {snippet.text}")
        return lines

    def _correct(self, argument: str) -> list[str]:
        event_id, replacement = _split_command(argument)
        if not event_id or not replacement:
            return ["usage: correct <event-id> <new memory text>"]
        corrected_id = self._service.correct(
            event_id,
            {"semantic_description": replacement},
            caller=CALLER,
        )
        return [f"corrected {event_id} -> {corrected_id}: {replacement}"]

    def _explain(self, event_id: str) -> list[str]:
        if not event_id:
            return ["usage: explain <event-id>"]
        explanation = self._service.explain(event_id, caller=CALLER)
        lifecycle = explanation["lifecycle"]
        lifecycle_explanation = explanation["lifecycle_explanation"]
        return [
            f"event: {event_id}",
            f"lifecycle: {lifecycle['state']}",
            f"reason: {lifecycle_explanation['reason']}",
            f"related: {lifecycle_explanation['related_event_ids']}",
        ]

    def _delete(self, argument: str) -> list[str]:
        event_id, reason = _split_command(argument)
        if not event_id:
            return ["usage: delete <event-id> [reason]"]
        resolved_reason = reason or "interactive user requested deletion"
        deleted_ids = self._service.delete_by_event_id(
            event_id,
            caller=CALLER,
            reason=resolved_reason,
        )
        return [f"deleted {deleted_ids}"]

    def _audit(self) -> list[str]:
        records = self._service.audit()
        operations = [record.operation.value for record in records]
        return [f"audit records: {len(records)}", f"operations: {operations}"]

    def _metrics(self) -> list[str]:
        metrics = self._service.metrics_snapshot()
        return [
            f"metrics audit records: {metrics['audit']['total_records']}",
            f"metrics tombstones: {metrics['deletion']['tombstone_count']}",
        ]


def run_repl(
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> None:
    resolved_input = input_stream or sys.stdin
    resolved_output = output_stream or sys.stdout
    repl = AgentMemoryRepl()
    try:
        _write_lines(
            resolved_output,
            [
                "Phone Memory REPL",
                "Type 'help' for commands. Type 'quit' to exit.",
            ],
        )
        for raw_line in resolved_input:
            for output_line in repl.execute(raw_line.strip()):
                print(output_line, file=resolved_output)
                if output_line == "bye":
                    return
    finally:
        repl.close()


def _scope() -> PermissionScope:
    return PermissionScope(
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
    )


def _candidate(text: str) -> MemoryCandidate:
    return MemoryCandidate(
        semantic_description=text,
        source_app=SOURCE_APP,
        actor=Actor.USER,
        modality=[Modality.TEXT],
        attribution=Attribution.USER_STATED,
        entities=_guess_entities(text),
    )


def _guess_entities(text: str) -> list[str]:
    lowered = text.lower()
    entities: list[str] = []
    for keyword in ["planning", "travel", "fitness", "work", "food"]:
        if keyword in lowered:
            entities.append(keyword)
    return entities or ["general"]


def _split_command(line: str) -> tuple[str, str]:
    stripped = line.strip()
    if not stripped:
        return "", ""
    parts = stripped.split(maxsplit=1)
    if len(parts) == 1:
        return parts[0].lower(), ""
    return parts[0].lower(), parts[1].strip()


def _help_lines() -> list[str]:
    return [
        "commands:",
        "remember <memory text>",
        "search <query>",
        "context <query>",
        "correct <event-id> <new memory text>",
        "explain <event-id>",
        "delete <event-id> [reason]",
        "audit",
        "metrics",
        "quit",
    ]


def _write_lines(output_stream: TextIO, lines: list[str]) -> None:
    for line in lines:
        print(line, file=output_stream)


if __name__ == "__main__":
    run_repl()
