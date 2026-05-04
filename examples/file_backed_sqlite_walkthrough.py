from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from itertools import count
from pathlib import Path
from pprint import pprint
import sys
import tempfile
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore


CALLER = "calendar_agent"
SOURCE_APP = "system_assistant"
QUERY = "morning planning"


def run_walkthrough(db_path: str | Path | None = None) -> dict[str, Any]:
    path = _resolve_db_path(db_path)
    now = datetime.now(tz=UTC).replace(microsecond=0)
    clock = _ticking_clock(now)

    service = _open_file_backed_service(path, clock=clock)
    try:
        service.grant(CALLER, _scope(), duration_seconds=3_600)
        event_id = service.record(_candidate(), caller=CALLER)
    finally:
        service.close()

    service = _open_file_backed_service(path, clock=clock)
    try:
        after_reopen_search = service.search(QUERY, caller=CALLER, top_k=3)
        after_reopen_audit = service.audit()
        after_reopen_tombstones = service.store.list_tombstones()
        deleted_event_ids = service.delete_by_event_id(
            event_id,
            caller=CALLER,
            reason="walkthrough deletion",
        )
    finally:
        service.close()

    service = _open_file_backed_service(path, clock=clock)
    try:
        after_delete_reopen_search = service.search(QUERY, caller=CALLER, top_k=3)
        after_delete_reopen_tombstones = service.store.list_tombstones()
        after_delete_reopen_audit = service.audit()
    finally:
        service.close()

    return {
        "db_path": str(path),
        "event_id": event_id,
        "after_reopen_search_event_ids": [
            result.event_id for result in after_reopen_search
        ],
        "after_reopen_audit_operations": [
            record.operation.value for record in after_reopen_audit
        ],
        "after_reopen_tombstone_event_ids": [
            tombstone.event_id for tombstone in after_reopen_tombstones
        ],
        "deleted_event_ids": deleted_event_ids,
        "after_delete_reopen_search_event_ids": [
            result.event_id for result in after_delete_reopen_search
        ],
        "after_delete_reopen_tombstone_event_ids": [
            tombstone.event_id for tombstone in after_delete_reopen_tombstones
        ],
        "after_delete_reopen_audit_operations": [
            record.operation.value for record in after_delete_reopen_audit
        ],
    }


def _resolve_db_path(db_path: str | Path | None) -> Path:
    if db_path is not None:
        return Path(db_path)

    handle = tempfile.NamedTemporaryFile(
        prefix="phone-mem-",
        suffix=".sqlite3",
        delete=False,
    )
    handle.close()
    return Path(handle.name)


def _ticking_clock(start: datetime) -> Callable[[], datetime]:
    ticks = count()
    return lambda: start + timedelta(seconds=next(ticks))


def _open_file_backed_service(
    path: Path,
    *,
    clock: Callable[[], datetime],
) -> PersonalMemoryService:
    path.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteMemoryStore.connect(str(path))
    store.initialize_schema()
    return PersonalMemoryService.from_store(store, clock=clock)


def _scope() -> PermissionScope:
    return PermissionScope(
        operations=[
            AuditOperation.WRITE,
            AuditOperation.READ,
            AuditOperation.DELETE,
        ],
        apps=[SOURCE_APP],
        privacy_levels=[PrivacyLevel.PERSONAL],
        memory_layers=[MemoryLayer.EPISODIC],
    )


def _candidate() -> MemoryCandidate:
    return MemoryCandidate(
        semantic_description="User prefers morning planning sessions.",
        source_app=SOURCE_APP,
        actor=Actor.USER,
        modality=[Modality.TEXT],
        attribution=Attribution.USER_STATED,
        entities=["planning"],
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write and reopen a file-backed SQLite Personal Memory Service database.",
    )
    parser.add_argument(
        "db_path",
        nargs="?",
        help="SQLite database path. A temporary .sqlite3 file is created when omitted.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    pprint(run_walkthrough(args.db_path))
