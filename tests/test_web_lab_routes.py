from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from phone_mem.agent_runtime.client import FakeLLMClient, LLMResponse, ToolCall
from examples.web_lab import build_parser
from phone_mem.web_lab.app import create_app
from phone_mem.web_lab.state import LabState


class WebLabRoutesTest(unittest.TestCase):
    def test_html_and_metadata_routes_render_lab_shell(self) -> None:
        state = self._state(FakeLLMClient([LLMResponse(text="ok")]))
        self.addCleanup(state.close)

        with TestClient(create_app(state)) as client:
            html = client.get("/")
            metadata = client.get("/api/metadata")

        self.assertEqual(html.status_code, 200)
        self.assertIn("Python Web Lab", html.text)
        self.assertIn("web_lab_agent", html.text)
        self.assertEqual(metadata.json()["model"], state.model)
        self.assertEqual(metadata.json()["provider_status"], "fake")

    def test_html_renders_turn_debugger_tabs(self) -> None:
        state = self._state(FakeLLMClient([LLMResponse(text="ok")]))
        self.addCleanup(state.close)

        with TestClient(create_app(state)) as client:
            html = client.get("/")

        self.assertEqual(html.status_code, 200)
        self.assertIn('role="tablist"', html.text)
        self.assertIn('data-debug-tab="turns"', html.text)
        self.assertIn('data-debug-tab="audit"', html.text)
        self.assertIn('data-debug-tab="metrics"', html.text)
        self.assertIn('id="debug-panel-turns"', html.text)
        self.assertIn('id="debug-panel-audit"', html.text)
        self.assertIn('id="debug-panel-metrics"', html.text)

    def test_html_renders_turn_debugger_help(self) -> None:
        state = self._state(FakeLLMClient([LLMResponse(text="ok")]))
        self.addCleanup(state.close)

        with TestClient(create_app(state)) as client:
            html = client.get("/")

        self.assertEqual(html.status_code, 200)
        self.assertIn('id="debug-help-toggle"', html.text)
        self.assertIn('id="debug-help"', html.text)
        self.assertIn("Turns shows each chat turn snapshot", html.text)
        self.assertIn("Audit shows permissioned memory-service operations", html.text)
        self.assertIn("Metrics shows aggregate service counters", html.text)

    def test_chat_route_returns_turn_debugger_payload_and_records_snapshot(self) -> None:
        state = self._state(
            FakeLLMClient(
                [
                    LLMResponse(
                        text="",
                        tool_calls=[
                            ToolCall(
                                call_id="call-1",
                                name="remember",
                                arguments={"text": "User prefers lab demos."},
                            )
                        ],
                    ),
                    LLMResponse(text="I will remember that."),
                ]
            )
        )
        self.addCleanup(state.close)

        with TestClient(create_app(state)) as client:
            response = client.post("/api/chat", json={"message": "Remember that I prefer lab demos."})
            turns = client.get("/api/turns")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["text"], "I will remember that.")
        event_id = payload["tool_results"][0]["result"]["event_id"]
        self.assertEqual(payload["evidence_event_ids"], [event_id])
        self.assertEqual(turns.json()["turns"][0]["evidence_event_ids"], [event_id])

    def test_memory_inspector_routes_expose_operations(self) -> None:
        state = self._state(FakeLLMClient([LLMResponse(text="ok")]))
        self.addCleanup(state.close)
        event_id = state.tools.remember("User prefers searchable memories.")["event_id"]

        with TestClient(create_app(state)) as client:
            memories = client.get("/api/memories")
            search = client.get("/api/search", params={"query": "searchable"})
            context = client.get("/api/context", params={"query": "searchable"})
            explanation = client.get(f"/api/explain/{event_id}")
            corrected = client.post(
                f"/api/correct/{event_id}",
                json={"replacement_text": "User prefers inspectable memories."},
            )
            deleted = client.post(
                f"/api/delete/{corrected.json()['event_id']}",
                json={"reason": "route test"},
            )
            audit = client.get("/api/audit")
            metrics = client.get("/api/metrics")

        self.assertEqual(memories.json()["memories"][0]["event_id"], event_id)
        self.assertEqual(search.json()["results"][0]["event_id"], event_id)
        self.assertEqual(context.json()["evidence_event_ids"], [event_id])
        self.assertEqual(explanation.json()["event_id"], event_id)
        self.assertEqual(deleted.json()["deleted_event_ids"], [corrected.json()["event_id"]])
        self.assertGreaterEqual(len(audit.json()["audit_records"]), 5)
        self.assertEqual(metrics.json()["deletion"]["deleted_event_count"], 1)

    def test_domain_errors_are_serialized_for_routes(self) -> None:
        state = self._state(FakeLLMClient([LLMResponse(text="ok")]))
        self.addCleanup(state.close)

        with TestClient(create_app(state)) as client:
            response = client.get("/api/explain/missing-event")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["ok"], False)
        self.assertEqual(response.json()["error"]["type"], "MemoryEventNotFound")

    def test_launch_wrapper_parser_accepts_host_port_and_reload(self) -> None:
        args = build_parser().parse_args(["--host", "0.0.0.0", "--port", "9000", "--reload"])

        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 9000)
        self.assertTrue(args.reload)

    def _state(self, client: FakeLLMClient) -> LabState:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return LabState.create(db_path=Path(tmpdir.name) / "memory.sqlite3", client=client)


if __name__ == "__main__":
    unittest.main()
