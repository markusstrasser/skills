"""Tests for resume_worktree_guard.py and its wiring in pretool-universal-dispatch.py.

Run: uv run --no-project --with pytest python3 -m pytest hooks/test_resume_worktree_guard.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))

import resume_worktree_guard as guard  # noqa: E402

DISPATCH = HOOKS_DIR / "pretool-universal-dispatch.py"


def _session(tmp_path, **meta):
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("")
    subagents = tmp_path / "session" / "subagents"
    subagents.mkdir(parents=True)
    (subagents / "agent-a1ed8c64.meta.json").write_text(json.dumps({"name": "gencode-p2", **meta}))
    return str(transcript)


def test_warns_when_the_resumed_agent_lost_its_worktree(tmp_path):
    transcript = _session(tmp_path, worktreeCleanlyRemoved=True)
    for target in ("gencode-p2", "a1ed8c64"):
        note = guard.removed_worktree_note({"to": target, "message": "continue"}, transcript)
        assert "worktree the harness removed" in note


def test_silent_when_the_message_names_a_managed_worktree(tmp_path):
    transcript = _session(tmp_path, worktreeCleanlyRemoved="True")
    message = "Resume in /repo/.claude/worktrees/gencode-p2"
    assert guard.removed_worktree_note({"to": "gencode-p2", "message": message}, transcript) == ""


def test_silent_for_a_live_worktree_or_an_unknown_target(tmp_path):
    transcript = _session(tmp_path, worktreePath="/repo/.claude/worktrees/agent-a1ed8c64")
    assert guard.removed_worktree_note({"to": "gencode-p2", "message": "go"}, transcript) == ""
    assert guard.removed_worktree_note({"to": "someone-else", "message": "go"}, transcript) == ""


def test_dispatch_emits_the_note_for_sendmessage(tmp_path):
    transcript = _session(tmp_path, worktreeCleanlyRemoved=True)
    envelope = {
        "tool_name": "SendMessage",
        "tool_input": {"to": "gencode-p2", "message": "continue"},
        "transcript_path": transcript,
        "session_id": "test-resume-guard",
    }
    proc = subprocess.run(
        [sys.executable, str(DISPATCH)],
        input=json.dumps(envelope),
        capture_output=True,
        text=True,
        env={"CLAUDE_HOOK_STATE_DIR": str(tmp_path), "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
        timeout=30,
    )
    assert proc.returncode == 0
    notes = [json.loads(line)["additionalContext"] for line in proc.stdout.splitlines() if line.startswith("{")]
    assert any("worktree the harness removed" in note for note in notes)
