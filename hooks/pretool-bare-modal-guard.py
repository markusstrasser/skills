#!/usr/bin/env python3
# Gov-ID: hook:bare-modal-guard
# goal: prevent bare `modal` CLI invocations that fail silently (not on PATH)
# verifier: --selftest
# blast_radius: shared
"""Transform bare `modal` Bash invocations to the installed binary path.

2026-06-21: upgraded from WARN-only to PreToolUse `updatedInput` rewrite
(leverage WIN2 / gate-ergonomics — transform, don't block-then-retry).
`modal` lives at ~/.local/bin/modal but is absent from agent-shell PATH;
empty stdout from a missing binary has been misread as signal."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_UV_RUN = re.compile(r"\buv\s+run\b")
_PY_MODAL = re.compile(r"\bpython3?\s+-m\s+modal\b")
_BARE_MODAL = re.compile(r"(^|(?:&&|;|\|)\s*)modal\b")

_MODAL_BIN = Path.home() / ".local" / "bin" / "modal"


def _strip_quoted(cmd: str) -> str:
    cmd = re.sub(r"'[^']*'", "''", cmd)
    cmd = re.sub(r'"[^"]*"', '""', cmd)
    return cmd


def _needs_rewrite(cmd: str) -> bool:
    if not cmd or not cmd.strip():
        return False
    bare = _strip_quoted(cmd)
    if _PY_MODAL.search(bare):
        return False
    if _UV_RUN.search(bare) and re.search(r"\bmodal\b", bare):
        return False
    return bool(_BARE_MODAL.search(bare))


def rewrite(cmd: str) -> str | None:
    """Return rewritten command, or None if no change."""
    if not _needs_rewrite(cmd):
        return None
    if not _MODAL_BIN.is_file():
        return None
    modal_path = str(_MODAL_BIN)

    def repl(m: re.Match[str]) -> str:
        return f"{m.group(1)}{modal_path}"

    return _BARE_MODAL.sub(repl, cmd)


def verdict(cmd: str) -> tuple[str, str]:
    """Return ('rewrite'|'pass', new_cmd_or_msg)."""
    new = rewrite(cmd)
    if new and new != cmd:
        return "rewrite", new
    return "pass", ""


def _selftest() -> int:
    cases: list[tuple[str, str | None]] = [
        ("modal app list", str(_MODAL_BIN) + " app list"),
        ("cd genomics && modal app logs foo", f"cd genomics && { _MODAL_BIN } app logs foo"),
        ("uv run modal app list", None),
        ("uv run python3 -m modal app list", None),
        ("grep modal scripts/foo.py", None),
        ("echo 'run modal app list'", None),
    ]
    bad = 0
    for cmd, want in cases:
        got = rewrite(cmd)
        ok = got == want
        bad += not ok
        print(f"  {'ok ' if ok else 'FAIL'} want={want!r} got={got!r} cmd={cmd!r}")
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
    ti = payload.get("tool_input") or {}
    cmd = ti.get("command", "")
    action, out = verdict(cmd)
    if action == "rewrite" and out:
        updated = dict(ti)
        updated["command"] = out
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": updated,
            }
        }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
