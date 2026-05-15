from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path
import json
import unittest
from unittest.mock import patch

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
        self.assertIn('data-debug-tab="capture"', html.text)
        self.assertIn('data-debug-tab="context"', html.text)
        self.assertIn('data-debug-tab="audit"', html.text)
        self.assertIn('data-debug-tab="metrics"', html.text)
        self.assertIn('data-debug-tab="maintenance"', html.text)
        self.assertIn('id="debug-panel-turns"', html.text)
        self.assertIn('id="debug-panel-capture"', html.text)
        self.assertIn('id="debug-panel-context"', html.text)
        self.assertIn('id="debug-panel-audit"', html.text)
        self.assertIn('id="debug-panel-metrics"', html.text)
        self.assertIn('id="debug-panel-maintenance"', html.text)

    def test_html_renders_turn_debugger_help(self) -> None:
        state = self._state(FakeLLMClient([LLMResponse(text="ok")]))
        self.addCleanup(state.close)

        with TestClient(create_app(state)) as client:
            html = client.get("/")

        self.assertEqual(html.status_code, 200)
        self.assertIn('id="debug-help-toggle"', html.text)
        self.assertIn('id="debug-help"', html.text)
        self.assertIn("Turns shows each chat turn snapshot", html.text)
        self.assertIn("Capture shows captured event IDs", html.text)
        self.assertIn("Context shows hot capsules", html.text)
        self.assertIn("Audit shows permissioned memory-service operations", html.text)
        self.assertIn("Metrics shows aggregate service counters", html.text)
        self.assertIn("Maintenance shows dry-run reports", html.text)

    def test_html_renders_retrieval_explanation_and_maintenance_controls(self) -> None:
        state = self._state(FakeLLMClient([LLMResponse(text="ok")]))
        self.addCleanup(state.close)

        with TestClient(create_app(state)) as client:
            html = client.get("/")

        self.assertEqual(html.status_code, 200)
        self.assertIn("Retrieval Explanation", html.text)
        self.assertIn('id="refresh-maintenance"', html.text)
        self.assertIn('data-maintenance-report="reflect"', html.text)
        self.assertIn('data-maintenance-report="defrag"', html.text)
        self.assertIn('data-maintenance-report="schema-diff"', html.text)

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

    def test_chat_route_exposes_turn_boundary_capture_event_ids(self) -> None:
        state = self._state(FakeLLMClient([LLMResponse(text="Updated.")]))
        self.addCleanup(state.close)

        with TestClient(create_app(state)) as client:
            response = client.post(
                "/api/chat",
                json={"message": "Actually, I prefer afternoon planning sessions."},
            )
            turns = client.get("/api/turns")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(len(payload["captured_event_ids"]), 1)
        self.assertEqual(payload["turn"]["captured_event_ids"], payload["captured_event_ids"])
        self.assertEqual(turns.json()["turns"][0]["captured_event_ids"], payload["captured_event_ids"])

    def test_chat_refresh_route_clears_turns_and_session_context(self) -> None:
        fake_client = FakeLLMClient(
            [
                LLMResponse(text="We can prepare a checklist first."),
                LLMResponse(text="Continuing from the checklist."),
                LLMResponse(text="Starting fresh."),
            ]
        )
        state = self._state(fake_client)
        self.addCleanup(state.close)

        with TestClient(create_app(state)) as client:
            client.post("/api/chat", json={"message": "Let's plan the launch review."})
            client.post("/api/chat", json={"message": "Continue that."})
            refresh = client.post("/api/chat/refresh")
            cleared_turns = client.get("/api/turns")
            fresh = client.post("/api/chat", json={"message": "Start over."})

        request_text = "\n".join(message.content for message in fake_client.requests[2].messages)
        self.assertEqual(refresh.status_code, 200)
        self.assertEqual(refresh.json()["ok"], True)
        self.assertEqual(refresh.json()["cleared_turns"], 2)
        self.assertEqual(cleared_turns.json()["turns"], [])
        self.assertNotIn("Transient conversation context", request_text)
        self.assertEqual(fresh.json()["turn"]["index"], 1)

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
        self.assertIn("explanation", search.json()["results"][0])
        self.assertEqual(context.json()["evidence_event_ids"], [event_id])
        self.assertEqual(explanation.json()["event_id"], event_id)
        self.assertEqual(deleted.json()["deleted_event_ids"], [corrected.json()["event_id"]])
        self.assertGreaterEqual(len(audit.json()["audit_records"]), 5)
        self.assertEqual(metrics.json()["deletion"]["deleted_event_count"], 1)

    def test_maintenance_routes_expose_json_safe_dry_run_reports(self) -> None:
        state = self._state(FakeLLMClient([LLMResponse(text="ok")]))
        self.addCleanup(state.close)
        state.tools.remember("User prefers morning planning sessions.", entities=["planning"])
        before_event_ids = [event.event_id for event in state.service.store.query_events()]

        with TestClient(create_app(state)) as client:
            reflection = client.get("/api/maintenance/reflect")
            defrag = client.get("/api/maintenance/defrag")
            schema_diff = client.get("/api/maintenance/schema-diff")

        after_event_ids = [event.event_id for event in state.service.store.query_events()]
        self.assertEqual(reflection.status_code, 200)
        self.assertEqual(defrag.status_code, 200)
        self.assertEqual(schema_diff.status_code, 200)
        json.dumps(reflection.json())
        json.dumps(defrag.json())
        json.dumps(schema_diff.json())
        self.assertEqual(after_event_ids, before_event_ids)
        self.assertEqual(reflection.json()["mutates_store"], False)
        self.assertEqual(defrag.json()["mutates_store"], False)
        self.assertEqual(schema_diff.json()["mutates_store"], False)

    def test_domain_errors_are_serialized_for_routes(self) -> None:
        state = self._state(FakeLLMClient([LLMResponse(text="ok")]))
        self.addCleanup(state.close)

        with TestClient(create_app(state)) as client:
            response = client.get("/api/explain/missing-event")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["ok"], False)
        self.assertEqual(response.json()["error"]["type"], "MemoryEventNotFound")

    def test_multi_user_html_escapes_session_metadata(self) -> None:
        with TemporaryDirectory() as tmpdir:
            from phone_mem.web_lab.users import UserLabStateManager

            manager = UserLabStateManager(users_dir=Path(tmpdir), model="fake")
            self.addCleanup(manager.close_all)

            with patch("phone_mem.web_lab.app.UserLabStateManager", return_value=manager):
                app = create_app()

            with TestClient(app) as client:
                client.post("/api/login", json={"username": "<script>alert(1)</script>"})
                response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertNotIn("<script>alert(1)</script>", response.text)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", response.text)

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
