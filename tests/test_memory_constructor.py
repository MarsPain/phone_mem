from __future__ import annotations

from datetime import UTC, datetime
import unittest

from phone_mem.personal_memory_service.constructor import MemoryCandidate, MemoryConstructor
from phone_mem.personal_memory_service.events import (
    Actor,
    Attribution,
    EventType,
    LifecycleState,
    MemoryLayer,
    Modality,
    PrivacyLevel,
    ProcessingPolicy,
)


class MemoryConstructorTest(unittest.TestCase):
    def test_constructs_user_stated_text_memory(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        constructor = MemoryConstructor(clock=lambda: now, id_factory=lambda: "event-1")
        candidate = MemoryCandidate(
            semantic_description="  User prefers morning planning sessions.  ",
            source_app="system_assistant",
            actor=Actor.USER,
            modality=[Modality.TEXT],
            attribution=Attribution.USER_STATED,
            entities=["user", " planning ", "user"],
            allowed_scopes=["system_assistant", " system_assistant "],
        )

        event = constructor.construct(candidate)

        self.assertEqual(event.event_id, "event-1")
        self.assertEqual(event.created_at, now)
        self.assertEqual(event.valid_time.start, now)
        self.assertEqual(event.event_type, EventType.USER_UTTERANCE)
        self.assertEqual(event.memory_layer, MemoryLayer.EPISODIC)
        self.assertEqual(event.semantic_description, "User prefers morning planning sessions.")
        self.assertEqual(event.entities, ["user", "planning"])
        self.assertEqual(event.privacy.allowed_scopes, ["system_assistant"])
        self.assertEqual(event.privacy.level, PrivacyLevel.PERSONAL)
        self.assertEqual(event.privacy.processing_policy, ProcessingPolicy.CLIENT_ENCRYPTED_SYNC)
        self.assertEqual(event.lifecycle.state, LifecycleState.ACTIVE)

    def test_constructs_sensitive_memory_as_device_only(self) -> None:
        now = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
        constructor = MemoryConstructor(clock=lambda: now, id_factory=lambda: "event-2")
        candidate = MemoryCandidate(
            semantic_description="User shared private health context.",
            source_app="system_assistant",
            actor=Actor.USER,
            modality=[Modality.TEXT],
            attribution=Attribution.USER_STATED,
            privacy_level=PrivacyLevel.SENSITIVE,
        )

        event = constructor.construct(candidate)

        self.assertEqual(event.privacy.level, PrivacyLevel.SENSITIVE)
        self.assertEqual(event.privacy.processing_policy, ProcessingPolicy.DEVICE_ONLY)

    def test_blank_candidate_description_is_rejected(self) -> None:
        constructor = MemoryConstructor(clock=lambda: datetime(2026, 5, 1, 9, 0, tzinfo=UTC))
        candidate = MemoryCandidate(
            semantic_description=" ",
            source_app="system_assistant",
            actor=Actor.USER,
            modality=[Modality.TEXT],
            attribution=Attribution.USER_STATED,
        )

        with self.assertRaisesRegex(ValueError, "semantic_description is required"):
            constructor.construct(candidate)


if __name__ == "__main__":
    unittest.main()
