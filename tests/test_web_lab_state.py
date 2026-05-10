from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

from phone_mem.agent_runtime.client import FakeLLMClient, LLMResponse
from phone_mem.web_lab.state import DEFAULT_CALLER, DEFAULT_SOURCE_APP, LabState


class WebLabStateTest(unittest.TestCase):
    def test_create_initializes_file_backed_service_and_runtime_with_fake_client(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.sqlite3"
            client = FakeLLMClient([LLMResponse(text="Noted.")])
            state = LabState.create(db_path=db_path, client=client, model="fake-web-lab-model")
            self.addCleanup(state.close)

            response = state.run_chat_turn("Remember that I prefer focused mornings.")

            self.assertEqual(response.text, "Noted.")
            self.assertEqual(state.db_path, db_path)
            self.assertEqual(state.caller, DEFAULT_CALLER)
            self.assertEqual(state.source_app, DEFAULT_SOURCE_APP)
            self.assertEqual(state.model, "fake-web-lab-model")
            self.assertEqual(state.provider_status, "fake")
            self.assertEqual(len(state.turn_snapshots), 1)
            self.assertEqual(client.requests[0].model, "fake-web-lab-model")
            self.assertTrue(db_path.exists())

    def test_file_backed_memory_persists_across_lab_state_reopen(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.sqlite3"
            first = LabState.create(
                db_path=db_path,
                client=FakeLLMClient([LLMResponse(text="Stored.")]),
            )
            first.tools.remember("User prefers local-first memory labs.", entities=["lab"])
            first.close()

            reopened = LabState.create(
                db_path=db_path,
                client=FakeLLMClient([LLMResponse(text="Loaded.")]),
            )
            self.addCleanup(reopened.close)

            memories = reopened.service.search("local-first", caller=reopened.caller)

            self.assertEqual(len(memories), 1)
            self.assertEqual(memories[0].snippet.text, "User prefers local-first memory labs.")

    def test_close_closes_underlying_store(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state = LabState.create(
                db_path=Path(tmpdir) / "memory.sqlite3",
                client=FakeLLMClient([LLMResponse(text="Done.")]),
            )

            state.close()

            with self.assertRaises(Exception):
                state.service.store.query_events()

    def test_run_chat_turn_records_captured_event_ids_in_snapshot(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state = LabState.create(
                db_path=Path(tmpdir) / "memory.sqlite3",
                client=FakeLLMClient([LLMResponse(text="Updated.")]),
            )
            self.addCleanup(state.close)

            response = state.run_chat_turn("Actually, I prefer afternoon planning sessions.")

            self.assertEqual(state.turn_snapshots[0].captured_event_ids, response.captured_event_ids)
            self.assertEqual(len(response.captured_event_ids), 1)
            self.assertEqual(
                state.snapshots_payload()["turns"][0]["captured_event_ids"],
                response.captured_event_ids,
            )

    def test_run_chat_turn_uses_session_scoped_conversation_history(self) -> None:
        with TemporaryDirectory() as tmpdir:
            client = FakeLLMClient(
                [
                    LLMResponse(text="We can prepare a checklist first."),
                    LLMResponse(text="Continuing from the checklist."),
                ]
            )
            state = LabState.create(db_path=Path(tmpdir) / "memory.sqlite3", client=client)
            self.addCleanup(state.close)

            state.run_chat_turn("Let's plan the launch review.")
            state.run_chat_turn("Continue that.")

            request_text = "\n".join(message.content for message in client.requests[1].messages)
            self.assertIn("Transient conversation context", request_text)
            self.assertIn("user: Let's plan the launch review.", request_text)
            self.assertIn("assistant: We can prepare a checklist first.", request_text)

    def test_clear_chat_history_removes_snapshots_and_session_context(self) -> None:
        with TemporaryDirectory() as tmpdir:
            client = FakeLLMClient(
                [
                    LLMResponse(text="We can prepare a checklist first."),
                    LLMResponse(text="Continuing from the checklist."),
                    LLMResponse(text="Starting fresh."),
                ]
            )
            state = LabState.create(db_path=Path(tmpdir) / "memory.sqlite3", client=client)
            self.addCleanup(state.close)

            state.run_chat_turn("Let's plan the launch review.")
            state.run_chat_turn("Continue that.")
            cleared = state.clear_chat_history()
            state.run_chat_turn("Start over.")

            request_text = "\n".join(message.content for message in client.requests[2].messages)
            self.assertEqual(cleared["cleared_turns"], 2)
            self.assertNotIn("Transient conversation context", request_text)
            self.assertEqual(len(state.turn_snapshots), 1)
            self.assertEqual(state.turn_snapshots[0].index, 1)
            self.assertEqual(state.turn_snapshots[0].user_message, "Start over.")


if __name__ == "__main__":
    unittest.main()
