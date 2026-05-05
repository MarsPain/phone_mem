from __future__ import annotations

from io import StringIO
import unittest

from examples.agent_memory_repl import AgentMemoryRepl, run_repl


class AgentMemoryReplTest(unittest.TestCase):
    def test_scripted_repl_session_records_searches_corrects_and_deletes_memory(self) -> None:
        input_stream = StringIO(
            "\n".join(
                [
                    "remember I prefer afternoon planning sessions",
                    "search planning",
                    "context planning",
                    "correct event-1 I prefer morning planning sessions",
                    "explain event-1",
                    "search morning",
                    "delete event-2",
                    "search morning",
                    "audit",
                    "quit",
                    "",
                ]
            )
        )
        output_stream = StringIO()

        run_repl(input_stream=input_stream, output_stream=output_stream)

        output = output_stream.getvalue()
        self.assertIn("Phone Memory REPL", output)
        self.assertIn("remembered event-1", output)
        self.assertIn("event-1 | I prefer afternoon planning sessions", output)
        self.assertIn("context evidence: ['event-1']", output)
        self.assertIn("corrected event-1 -> event-2", output)
        self.assertIn("lifecycle: superseded", output)
        self.assertIn("reason: superseded by correction", output)
        self.assertIn("event-2 | I prefer morning planning sessions", output)
        self.assertIn("deleted ['event-2']", output)
        self.assertIn("no active memories matched", output)
        self.assertIn("audit records:", output)
        self.assertIn("bye", output)

    def test_unknown_and_incomplete_commands_return_actionable_help(self) -> None:
        repl = AgentMemoryRepl()
        self.addCleanup(repl.close)

        self.assertIn("usage: remember", "\n".join(repl.execute("remember")))
        self.assertIn("unknown command", "\n".join(repl.execute("dance")))


if __name__ == "__main__":
    unittest.main()
