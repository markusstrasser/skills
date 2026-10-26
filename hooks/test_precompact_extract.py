"""precompact-extract.py reads only the window since the last compact boundary, and its
"Last tools" are the window's last three tool calls."""

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "precompact-extract.py"


def entry(kind, *blocks, **extra):
    return json.dumps({"type": kind, "message": {"content": list(blocks)}, **extra})


def say(text):
    return entry("assistant", {"type": "text", "text": text})


def tool(name):
    return entry("assistant", {"type": "tool_use", "name": name, "input": {}})


def test_only_the_last_window_is_extracted(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    transcript = tmp_path / "t.jsonl"
    old_q = "Should we record the stale stock client charge take in the background tonight?"
    new_q = "Should the fresh prune also run inside every worktree after the next landing?"
    transcript.write_text(
        "\n".join(
            [
                say(old_q),
                tool("Grep"),
                json.dumps({"type": "system", "subtype": "compact_boundary"}),
                tool("Read"),
                tool("Edit"),
                tool("Write"),
                tool("Bash"),
                say(new_q),
            ]
        )
        + "\n"
    )
    sid = "abcdef12-0000-0000-0000-000000000000"
    hook_input = {
        "session_id": sid,
        "transcript_path": str(transcript),
        "cwd": str(repo),
        "trigger": "auto",
    }
    subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(hook_input), text=True, check=True
    )
    text = (repo / ".claude" / f"checkpoint-auto-{sid[:8]}.md").read_text()
    assert new_q in text
    assert old_q not in text
    assert "**Last tools:** Edit, Write, Bash" in text
