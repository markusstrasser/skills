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

    def test_personal_remains_a_science_project_after_merge(self):
        tx = _transcript_user_then_search("maybe /research")
        try:
            code = self._run(
                {
                    "tool_name": "WebSearch",
                    "transcript_path": tx,
                    "cwd": "/Users/alien/Projects/personal",
                }
            )
            self.assertEqual(code, 2)
            self.assertIn("Skill(research)", self._last_stderr)
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


    def _intent_transcript(self, *extra: dict) -> str:
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        rows = [*extra, {"type": "user", "message": "do /research on benchmark design"}]
        Path(path).write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return path

    def _gate(self, tx: str, tool: str = "mcp__exa__web_search_exa", **more) -> int:
        try:
            return self._run(
                {"tool_name": tool, "transcript_path": tx, "cwd": "/Users/alien/Projects/agent-infra", **more}
            )
        finally:
            os.unlink(tx)

    def test_connector_and_scite_search_tools_are_gated(self):
        for tool in ("mcp__claude_ai_Exa__web_search_exa", "mcp__scite__search_literature"):
            self.assertEqual(self._gate(self._intent_transcript(), tool), 2, tool)

    def test_subagent_calls_pass(self):
        # A researcher subagent has no Skill tool and the gate reads its parent's intent.
        self.assertEqual(self._gate(self._intent_transcript(), agent_id="a1b2", agent_type="researcher"), 0)

    def test_skill_called_inside_a_repl_script_counts(self):
        # Code Mode writes the in-script Skill record only after the script ends.
        repl = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "REPL",
                        "input": {"code": "await tools.Skill({skill: 'research'});\nawait tools.WebSearch({query: 'x'})"},
                    }
                ]
            },
        }
        self.assertEqual(self._gate(self._intent_transcript(repl)), 0)
        other = json.loads(json.dumps(repl).replace("'research'", "'modal'"))
        self.assertEqual(self._gate(self._intent_transcript(other)), 2)

    def test_reinvocation_notice_is_not_intent(self):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        Path(path).write_text(
            json.dumps(
                {
                    "type": "user",
                    "message": "(Re-invocation of /research — the skill instructions were previously loaded; "
                    "the arguments: find papers about benchmark design)",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.assertEqual(self._gate(path), 0)

    def test_advisory_mode_prints_context_the_model_receives(self):
        tx = self._intent_transcript()
        try:
            proc = subprocess.run(
                [sys.executable, str(HOOK)],
                input=json.dumps(
                    {"tool_name": "WebSearch", "transcript_path": tx, "cwd": "/Users/alien/Projects/agent-infra"}
                ),
                text=True,
                capture_output=True,
                env={**os.environ, "RESEARCH_SKILL_GATE": "advisory"},
            )
        finally:
            os.unlink(tx)
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertIn("Skill(research)", out["additionalContext"])


if __name__ == "__main__":
    unittest.main()
