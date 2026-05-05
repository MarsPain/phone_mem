from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

from phone_mem.agent_runtime.client import FakeLLMClient, LLMResponse
from phone_mem.web_lab.inspector import MemoryInspector
from phone_mem.web_lab.state import LabState


class WebLabInspectorTest(unittest.TestCase):
    def test_lists_searches_previews_and_explains_memories_through_service_boundary(self) -> None:
        state = self._state()
        self.addCleanup(state.close)
        event_id = state.tools.remember(
            "User prefers morning planning sessions.",
            entities=["planning"],
        )["event_id"]
        inspector = MemoryInspector(state)

        memories = inspector.list_memories()
        search = inspector.search("morning planning")
        preview = inspector.preview_context("morning planning")
        explanation = inspector.explain(event_id)

        self.assertEqual(memories["memories"][0]["event_id"], event_id)
        self.assertEqual(search["results"][0]["event_id"], event_id)
        self.assertEqual(preview["evidence_event_ids"], [event_id])
        self.assertEqual(explanation["event_id"], event_id)
        self.assertEqual(explanation["lifecycle"]["state"], "active")

    def test_corrects_deletes_and_reports_audit_and_metrics(self) -> None:
        state = self._state()
        self.addCleanup(state.close)
        event_id = state.tools.remember("User prefers Friday retrospectives.")["event_id"]
        inspector = MemoryInspector(state)

        corrected = inspector.correct(event_id, "User prefers Thursday retrospectives.")
        deleted = inspector.delete(corrected["event_id"], reason="user cleanup")
        audit = inspector.audit()
        metrics = inspector.metrics()

        self.assertEqual(deleted["deleted_event_ids"], [corrected["event_id"]])
        self.assertGreaterEqual(len(audit["audit_records"]), 4)
        self.assertEqual(metrics["deletion"]["deleted_event_count"], 1)

    def test_structured_domain_errors_are_returned_as_error_payloads(self) -> None:
        state = self._state()
        self.addCleanup(state.close)
        inspector = MemoryInspector(state)

        payload = inspector.explain("missing-event")

        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["error"]["type"], "MemoryEventNotFound")
        self.assertEqual(payload["error"]["event_id"], "missing-event")

    def _state(self) -> LabState:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return LabState.create(
            db_path=Path(tmpdir.name) / "memory.sqlite3",
            client=FakeLLMClient([LLMResponse(text="ok")]),
        )


if __name__ == "__main__":
    unittest.main()
