#!/usr/bin/env python3
# Gov-ID: hook:bare-modal-guard
# goal: prevent bare `modal` CLI invocations that fail silently (not on PATH)
# verifier: null
# blast_radius: shared
"""WARN when Bash uses bare `modal` instead of `uv run modal`.

Mirrors pretool-uv-python-guard.py (WARN tier). `modal` is not on PATH in agent
shells; empty stdout gets misread as signal (genomics 7ffc759b, 2026-06-15).
"""
from __future__ import annotations

import json
import re
import sys

_UV_RUN = re.compile(r"\buv\s+run\b")
_PY_MODAL = re.compile(r"\bpython3?\s+-m\s+modal\b")
_BARE_MODAL_START = re.compile(r"^\s*modal\b")
_BARE_MODAL_COMPOUND = re.compile(r"(?:&&|;|\|)\s*modal\b")

_MSG = (
    "Heads up: bare `modal` is not on PATH here — use `uv run modal …` "
    "(or `uv run python3 -m modal`). Empty output from a missing binary has "
    "been misread as 'no apps running' before."
)


def _strip_quoted(cmd: str) -> str:
    cmd = re.sub(r"'[^']*'", "''", cmd)
    cmd = re.sub(r'"[^"]*"', '""', cmd)
    return cmd


def verdict(cmd: str) -> tuple[str, str]:
    if not cmd or not cmd.strip():
        return "pass", ""
    cmd = _strip_quoted(cmd)
    if _PY_MODAL.search(cmd):
        return "pass", ""
    if _UV_RUN.search(cmd) and re.search(r"\bmodal\b", cmd):
        return "pass", ""
    if _BARE_MODAL_START.search(cmd) or _BARE_MODAL_COMPOUND.search(cmd):
        return "warn", _MSG
    return "pass", ""


def _selftest() -> int:
    cases = [
        ("modal app list", "warn"),
        ("cd genomics && modal app logs foo", "warn"),
        ("uv run modal app list", "pass"),
        ("uv run python3 -m modal app list", "pass"),
        ("grep modal scripts/foo.py", "pass"),
        ("echo 'run modal app list'", "pass"),
    ]
    bad = 0
    for cmd, want in cases:
        got = verdict(cmd)[0]
        ok = got == want
        bad += not ok
        print(f"  {'ok ' if ok else 'FAIL'} want={want:<4} got={got:<4} {cmd!r}")
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") not in (None, "Bash"):
        return 0
    cmd = (payload.get("tool_input") or {}).get("command", "")
    action, msg = verdict(cmd)
    if action == "warn":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
