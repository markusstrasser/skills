#!/usr/bin/env python3
"""Test userprompt-clock.sh: emits valid UserPromptSubmit additionalContext with a clock stamp."""
import json
import re
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "userprompt-clock.sh"


def run(payload: dict) -> dict:
    p = subprocess.run(
        [str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=8,
    )
    assert p.returncode == 0, f"nonzero exit {p.returncode}: {p.stderr}"
    return json.loads(p.stdout)


def test_emits_clock_context():
    out = run({"prompt": "hello", "cwd": "/tmp", "session_id": "t"})
    hso = out["hookSpecificOutput"]
    assert hso["hookEventName"] == "UserPromptSubmit"
    ctx = hso["additionalContext"]
    # [clock: YYYY-MM-DD HH:MM TZ]
    assert re.match(r"^\[clock: \d{4}-\d{2}-\d{2} \d{2}:\d{2} \S+\]$", ctx), ctx


def test_fail_open_on_empty_stdin():
    p = subprocess.run([str(HOOK)], input="", capture_output=True, text=True, timeout=8)
    # never blocks; still emits a clock stamp (date needs no input)
    assert p.returncode == 0


if __name__ == "__main__":
    test_emits_clock_context()
    test_fail_open_on_empty_stdin()
    print("OK: test_userprompt_clock")
