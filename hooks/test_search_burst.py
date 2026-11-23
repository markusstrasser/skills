#!/usr/bin/env python3
"""pretool-search-burst.sh: one advisory at 10, one refused search at 30, then a fresh count."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "pretool-search-burst.sh"
DISPATCH = Path(__file__).resolve().parent / "pretool-universal-dispatch.py"


class SearchBurstTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="burst-")
        self.counter = os.path.join(self.dir, "counter")

    def _call(self, tool: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(HOOK)],
            input=json.dumps({"tool_name": tool, "tool_input": {"query": "x"}, "session_id": "s"}),
            text=True,
            capture_output=True,
            env={**os.environ, "SEARCH_BURST_COUNTER": self.counter},
        )

    def test_warns_once_then_blocks_once_then_restarts(self) -> None:
        outs = [self._call("mcp__exa__web_search_exa") for _ in range(31)]
        self.assertTrue(all(o.returncode == 0 for o in outs[:29]))
        warned = [i for i, o in enumerate(outs) if o.stdout.strip()]
        self.assertEqual(warned, [9])
        ctx = json.loads(outs[9].stdout)["hookSpecificOutput"]
        self.assertEqual(ctx["hookEventName"], "PreToolUse")
        self.assertIn("10 search queries", ctx["additionalContext"])
        self.assertEqual(outs[29].returncode, 2)
        self.assertIn("refused", outs[29].stderr)
        self.assertEqual(outs[30].returncode, 0)  # a speed bump, not a wall

    def test_connector_and_scite_count_and_a_read_tool_clears(self) -> None:
        for tool in ("mcp__claude_ai_Exa__web_search_exa", "mcp__scite__search_literature", "WebSearch"):
            self._call(tool)
        self.assertEqual(Path(self.counter).read_text().count("s"), 3)
        self._call("mcp__research__read_paper")
        self.assertEqual(Path(self.counter).read_text(), "")

    def test_researcher_check_is_not_a_search(self) -> None:
        self._call("mcp__exa__deep_researcher_check")
        self.assertFalse(Path(self.counter).exists() and Path(self.counter).read_text())

    def test_universal_dispatch_clears_the_count_on_read(self) -> None:
        owner = str(os.getpid())
        burst = Path(self.dir) / f"claude-search-burst-{owner}"
        burst.write_text("s\ns\n")
        subprocess.run(
            ["python3", str(DISPATCH)],
            input=json.dumps({"tool_name": "Grep", "tool_input": {"pattern": "x"}, "session_id": "s"}),
            text=True,
            capture_output=True,
            env={**os.environ, "CLAUDE_HOOK_STATE_DIR": self.dir},
        )
        self.assertEqual(burst.read_text(), "")


if __name__ == "__main__":
    unittest.main()
