"""hook_cmd_fingerprint.py — command fingerprinting for guard-fire telemetry.

Gives the trigger log (~/.claude/hook-triggers.jsonl) a way to tell "the same
command re-fired a guard" apart from "a changed command passed cleanly"
WITHOUT ever persisting the command text itself (T1 of guard-forcerate-study /
rescue-class-surface-closure-loop — arc-agi loop/backlog.jsonl rows 906/909).

fingerprint_command(cmd) -> (first_token, sha8):
  first_token — the command's real executable, coarse: leading shell
    VAR=value assignments and common wrappers (nohup/sudo/time/env/command)
    are skipped, the result is basename'd ("/usr/bin/git" -> "git"). Same
    env-assignment-skipping convention pretool-bash-dispatch.py's own
    _git_add_all_offends() already uses — not reinvented here.
  sha8 — first 8 hex chars of sha256(whitespace-normalized command). Collapses
    incidental whitespace differences (extra spaces/newlines) into the same
    hash; two textually-different commands hash differently with overwhelming
    probability. The RAW command is never written anywhere by this module —
    callers must not persist `cmd` itself alongside the fingerprint.

Both return ("", "") for an empty/whitespace-only command — callers use that
as the "not command-shaped" sentinel (omit the fields entirely rather than
logging empty strings).
"""
from __future__ import annotations

import hashlib
import re
import shlex

_WRAPPERS = {"nohup", "sudo", "time", "env", "command"}
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")


def _first_token(cmd: str) -> str:
    try:
        parts = shlex.split(cmd)
    except ValueError:
        parts = cmd.split()
    i = 0
    while i < len(parts):
        p = parts[i]
        if _ASSIGN_RE.match(p):
            i += 1
            continue
        base = p.rsplit("/", 1)[-1]
        if base in _WRAPPERS:
            i += 1
            continue
        return base
    return ""


def _sha8(cmd: str) -> str:
    normalized = " ".join(cmd.split())
    return hashlib.sha256(normalized.encode("utf-8", "replace")).hexdigest()[:8]


def fingerprint_command(cmd: str | None) -> tuple[str, str]:
    """Returns (first_token, sha8). ("", "") for an empty/whitespace command."""
    cmd = cmd or ""
    if not cmd.strip():
        return "", ""
    return _first_token(cmd), _sha8(cmd)


def main() -> None:
    """CLI: `hook_cmd_fingerprint.py "<cmd>"` (or stdin) -> prints `token sha8`."""
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    tok, sha = fingerprint_command(cmd)
    print(f"{tok} {sha}")


if __name__ == "__main__":
    main()
