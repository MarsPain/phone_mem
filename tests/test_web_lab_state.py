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


if __name__ == "__main__":
    unittest.main()
