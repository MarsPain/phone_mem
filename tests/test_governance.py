from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.governance.permissions import PermissionScope, PermissionService
from phone_mem.governance.views import MemoryViewProjector
from phone_mem.personal_memory_service.events import AuditOperation, MemoryLayer, PrivacyLevel
from phone_mem.personal_memory_service.storage import SQLiteMemoryStore
from tests.test_storage import make_event


class PermissionServiceTest(unittest.TestCase):
    def test_grant_allows_matching_event_until_expiry(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        service = PermissionService(store, clock=lambda: now, id_factory=lambda: "grant-1")
        event = make_event("event-1")

        grant = service.grant(
            "calendar_agent",
            PermissionScope(
                operations=[AuditOperation.READ],
                memory_layers=[MemoryLayer.EPISODIC],
                privacy_levels=[PrivacyLevel.PERSONAL],
                apps=["system_assistant"],
                entities=["user"],
            ),
            duration_seconds=60,
        )

        decision = service.can_access("calendar_agent", AuditOperation.READ, event, at=now)
        self.assertTrue(decision.allowed)
        self.assertEqual(grant.grant_id, "grant-1")

    def test_expired_grant_denies_matching_event(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        service = PermissionService(store, clock=lambda: now, id_factory=lambda: "grant-1")
        event = make_event("event-1")
        service.grant(
            "calendar_agent",
            PermissionScope(operations=[AuditOperation.READ]),
            duration_seconds=1,
        )

        later = datetime(2026, 5, 1, 9, 1, tzinfo=UTC)
        decision = service.can_access("calendar_agent", AuditOperation.READ, event, at=later)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "no active grant matched")

    def test_revoked_grant_denies_access(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        service = PermissionService(store, clock=lambda: now, id_factory=lambda: "grant-1")
        event = make_event("event-1")
        service.grant("calendar_agent", PermissionScope(operations=[AuditOperation.READ]), 60)

        service.revoke("grant-1")

        decision = service.can_access("calendar_agent", AuditOperation.READ, event, at=now)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "no active grant matched")


class MemoryViewProjectorTest(unittest.TestCase):
    def test_project_returns_only_authorized_events_and_denials(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        store = SQLiteMemoryStore.connect(":memory:")
        store.initialize_schema()
        permissions = PermissionService(store, clock=lambda: now, id_factory=lambda: "grant-1")
        permissions.grant(
            "calendar_agent",
            PermissionScope(
                operations=[AuditOperation.READ],
                apps=["system_assistant"],
                entities=["user"],
            ),
            duration_seconds=60,
        )
        projector = MemoryViewProjector(permissions)

        authorized = make_event("event-1", app="system_assistant", entity="user")
        denied = make_event("event-2", app="health", entity="health")

        view = projector.project(
            "calendar_agent",
            AuditOperation.READ,
            [authorized, denied],
            at=now,
        )

        self.assertEqual([event.event_id for event in view.events], ["event-1"])
        self.assertEqual(view.denied_event_ids, {"event-2": "no active grant matched"})


if __name__ == "__main__":
    unittest.main()
