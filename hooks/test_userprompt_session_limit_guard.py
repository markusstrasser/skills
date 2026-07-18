#!/usr/bin/env python3
"""Test userprompt-session-limit-guard.py: fires the resume-protocol nudge on
session-limit and monthly-spend-limit kill strings, silent otherwise, fail-open
on malformed input. Run: uv run pytest hooks/test_userprompt_session_limit_guard.py -q
"""
import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "userprompt-session-limit-guard.py"


def run(payload) -> subprocess.CompletedProcess:
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        ["python3", str(HOOK)], input=stdin, capture_output=True, text=True, timeout=8,
    )


def test_session_limit_fires_with_parsed_reset():
    p = run({"prompt": "failureReason: You've hit your session limit · resets 3:00pm (America/Los_Angeles)"})
    assert p.returncode == 0
    out = json.loads(p.stdout)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "SESSION-LIMIT KILL detected" in ctx
    assert "reset=3:00pm (America/Los_Angeles)" in ctx
    assert "ScheduleWakeup" in ctx


def test_session_limit_case_insensitive_and_alt_format():
    p = run({"prompt": "YOU'VE HIT YOUR SESSION LIMIT, RESETS 11:45AM"})
    out = json.loads(p.stdout)
    assert "reset=11:45AM" in out["hookSpecificOutput"]["additionalContext"]


def test_monthly_spend_limit_fires_different_message():
    p = run({"prompt": "Subagent died: hit your monthly spend limit · raise it at claude.ai/settings/usage"})
    assert p.returncode == 0
    out = json.loads(p.stdout)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "MONTHLY-SPEND-LIMIT KILL detected" in ctx
    assert "periodic ScheduleWakeup" in ctx
    assert "SESSION-LIMIT KILL" not in ctx


def test_benign_prompt_silent():
    p = run({"prompt": "please review this PR for bugs"})
    assert p.returncode == 0
    assert p.stdout.strip() == ""


def test_session_limit_phrase_without_captured_reset_time_silent():
    """Regex requires a captured HH:MM am/pm — a vague mention alone must not
    fire (nothing to self-arm a wakeup against)."""
    p = run({"prompt": "you have hit your session limit apparently"})
    assert p.returncode == 0
    assert p.stdout.strip() == ""


def test_malformed_json_fails_open():
    p = run("not json {{{")
    assert p.returncode == 0
    assert p.stdout.strip() == ""


def test_empty_stdin_fails_open():
    p = subprocess.run(["python3", str(HOOK)], input="", capture_output=True, text=True, timeout=8)
    assert p.returncode == 0
    assert p.stdout.strip() == ""


def test_missing_prompt_key_fails_open():
    p = run({"cwd": "/tmp"})
    assert p.returncode == 0
    assert p.stdout.strip() == ""


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
