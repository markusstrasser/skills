from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "pretool-llmx-guard.sh"


class LlmxGuardTest(unittest.TestCase):
    def run_guard(self, command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT)],
            env={
                "CLAUDE_TOOL_NAME": "Bash",
                "CLAUDE_TOOL_INPUT": json.dumps({"command": command}),
            },
            capture_output=True,
            text=True,
            check=False,
        )

    def test_blocks_default_llmx_chat_mode_without_chat_subcommand(self) -> None:
        proc = self.run_guard('llmx -m gemini-3.1-pro-preview "hello"')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("shared dispatch helper", proc.stderr)

    def test_allows_non_chat_subcommands(self) -> None:
        proc = self.run_guard('llmx image "robot mascot" -o /tmp/robot.png')
        self.assertEqual(proc.returncode, 0)

    def test_blocks_path_qualified_llmx_chat_mode(self) -> None:
        proc = self.run_guard('/usr/local/bin/llmx -m gemini-3.1-pro-preview "hello"')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("scripts/llm-dispatch.py", proc.stderr)


if __name__ == "__main__":
    unittest.main()
