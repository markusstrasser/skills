#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "pretool-research-skill-gate.py"


def _transcript_user_then_search(user_text: str, *, skill_first: bool = False) -> str:
    lines: list[dict] = []
    if skill_first:
        lines.append(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Skill",
                            "input": {"skill": "research"},
                        }
                    ]
                },
            }
        )
    lines.append({"type": "user", "message": user_text})
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    p = Path(path)
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    return str(p)


class ResearchSkillGateTests(unittest.TestCase):
    def _run(self, payload: dict, *, env: dict | None = None) -> int:
        merged = {**os.environ, **(env or {})}
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=merged,
        )
        self._last_stderr = proc.stderr
        return proc.returncode

    def test_blocks_science_research_without_skill(self):
        tx = _transcript_user_then_search(
            "Alright ... any more /research on agents and RSI we haven't done already"
        )
        try:
            code = self._run(
                {
                    "tool_name": "WebSearch",
                    "transcript_path": tx,
                    "cwd": "/Users/alien/Projects/agent-infra",
                }
            )
            self.assertEqual(code, 2)
            self.assertIn("Skill(research)", self._last_stderr)
        finally:
            os.unlink(tx)

    def test_passes_after_research_skill(self):
        tx = _transcript_user_then_search(
            "any more /research on agents and RSI",
            skill_first=True,
        )
        try:
            code = self._run(
                {
                    "tool_name": "mcp__exa__web_search_exa",
                    "transcript_path": tx,
                    "cwd": "/Users/alien/Projects/agent-infra",
                }
            )
            self.assertEqual(code, 0)
        finally:
            os.unlink(tx)

    def test_ignores_casual_loom_query(self):
        tx = _transcript_user_then_search(
            "is there /research a better loom video alternative?"
        )
        try:
            code = self._run(
                {
                    "tool_name": "WebSearch",
                    "transcript_path": tx,
                    "cwd": "/Users/alien/Projects/agent-infra",
                }
            )
            self.assertEqual(code, 0)
        finally:
            os.unlink(tx)

    def test_genomics_inline_research(self):
        tx = _transcript_user_then_search("Ok ... /modal and also /research this ...")
        try:
            code = self._run(
                {
                    "tool_name": "mcp__research__search_papers",
                    "transcript_path": tx,
                    "cwd": "/Users/alien/Projects/genomics",
                }
            )
            self.assertEqual(code, 2)
        finally:
            os.unlink(tx)

    def test_shadow_mode(self):
        tx = _transcript_user_then_search("do /research on benchmark design")
        try:
            code = self._run(
                {
                    "tool_name": "WebSearch",
                    "transcript_path": tx,
                    "cwd": "/Users/alien/Projects/evals",
                },
                env={"RESEARCH_SKILL_GATE": "shadow"},
            )
            self.assertEqual(code, 0)
        finally:
            os.unlink(tx)


if __name__ == "__main__":
    unittest.main()
