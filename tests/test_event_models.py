from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    EventSource,
    EventType,
    Lifecycle,
    LifecycleState,
    Lineage,
    MemoryEvent,
    MemoryLayer,
    Modality,
    Privacy,
    PrivacyLevel,
    ProcessingPolicy,
    Quality,
    ValidTime,
)


class PackageImportTest(unittest.TestCase):
    def test_personal_memory_service_package_imports(self) -> None:
        import phone_mem
        import phone_mem.personal_memory_service as service_package

        self.assertEqual(phone_mem.__version__, "0.1.0")
        self.assertIn("MemoryEvent", service_package.__all__)


class MemoryEventModelTest(unittest.TestCase):
    def test_valid_user_stated_event_serializes_to_canonical_dict(self) -> None:
        created_at = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        event = MemoryEvent(
            event_id="event-1",
            created_at=created_at,
            valid_time=ValidTime(start=created_at),
            event_type=EventType.USER_UTTERANCE,
            memory_layer=MemoryLayer.EPISODIC,
            semantic_description="User prefers morning planning sessions.",
            entities=["user"],
            relations=[],
            source=EventSource(
                app="system_assistant",
                actor=Actor.USER,
                modality=[Modality.TEXT],
                attribution=Attribution.USER_STATED,
            ),
            privacy=Privacy(
                level=PrivacyLevel.PERSONAL,
                allowed_scopes=["system_assistant"],
                processing_policy=ProcessingPolicy.CLIENT_ENCRYPTED_SYNC,
            ),
            quality=Quality(confidence=0.95, importance=0.7, freshness_half_life_days=30),
            lineage=Lineage(),
            lifecycle=Lifecycle(),
        )

        data = event.to_dict()

        self.assertEqual(data["event_id"], "event-1")
        self.assertEqual(data["created_at"], "2026-05-01T09:00:00+00:00")
        self.assertEqual(data["event_type"], "user_utterance")
        self.assertEqual(data["memory_layer"], "episodic")
        self.assertEqual(data["source"]["actor"], "user")
        self.assertEqual(data["privacy"]["level"], "personal")
        self.assertEqual(data["quality"]["confidence"], 0.95)
        self.assertEqual(data["lineage"]["parents"], [])
        self.assertEqual(data["lifecycle"]["state"], "active")

    def test_blank_event_id_is_rejected(self) -> None:
        created_at = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)

        with self.assertRaisesRegex(Exception, "event_id is required"):
            MemoryEvent(
                event_id=" ",
                created_at=created_at,
                valid_time=ValidTime(start=created_at),
                event_type=EventType.USER_UTTERANCE,
                memory_layer=MemoryLayer.EPISODIC,
                semantic_description="User prefers morning planning sessions.",
                entities=[],
                relations=[],
                source=EventSource(
                    app="system_assistant",
                    actor=Actor.USER,
                    modality=[Modality.TEXT],
                    attribution=Attribution.USER_STATED,
                ),
                privacy=Privacy(level=PrivacyLevel.PERSONAL),
                quality=Quality(confidence=0.95, importance=0.7, freshness_half_life_days=30),
                lineage=Lineage(),
                lifecycle=Lifecycle(),
            )

    def test_sensitive_memory_cannot_leave_device_by_default(self) -> None:
        with self.assertRaisesRegex(Exception, "sensitive memory must use device_only processing"):
            Privacy(
                level=PrivacyLevel.SENSITIVE,
                processing_policy=ProcessingPolicy.CLIENT_ENCRYPTED_SYNC,
            )

    def test_quality_scores_are_bounded(self) -> None:
        with self.assertRaisesRegex(Exception, "quality.confidence must be between 0 and 1"):
            Quality(confidence=1.1, importance=0.5, freshness_half_life_days=30)

        with self.assertRaisesRegex(Exception, "quality.importance must be between 0 and 1"):
            Quality(confidence=0.9, importance=-0.1, freshness_half_life_days=30)

    def test_mark_deleted_requires_reason_and_timestamp(self) -> None:
        deleted_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
        lifecycle = Lifecycle().mark_deleted(deleted_at=deleted_at, reason="user requested deletion")

        self.assertEqual(lifecycle.state, LifecycleState.DELETED)
        self.assertEqual(lifecycle.deleted_at, deleted_at)
        self.assertEqual(lifecycle.delete_reason, "user requested deletion")

    def test_deleted_lifecycle_requires_deleted_at(self) -> None:
        with self.assertRaisesRegex(Exception, "deleted lifecycle requires deleted_at"):
            Lifecycle(state=LifecycleState.DELETED, delete_reason="missing timestamp")


if __name__ == "__main__":
    unittest.main()
