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


if __name__ == "__main__":
    unittest.main()
