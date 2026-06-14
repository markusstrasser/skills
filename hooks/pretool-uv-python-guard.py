#!/usr/bin/env python3
# Gov-ID: hook:uv-python-guard
# goal: stop "ModuleNotFoundError" launch failures from bare/uvx python invocations
#       that skip the project venv (system python / isolated uvx env lack deps).
# verifier: null  (capability-testable via agentlogs missing-module trend; not yet a grader)
# blast_radius: shared
"""pretool-uv-python-guard.py — steer python invocations to `uv run`.

Replaces the fragile inline guard (settings.json) that only caught `python3 …`
at the very START of a command (regex anchored to the JSON quote) and broke on
escaped quotes. Measured gap (2026-06-14, agentlogs): 16 bare-`python3` + 3
`uvx python3` `No module named 'duckdb'` crashes over 2 weeks — the bypass was
`cd <proj> && python3 …` and `uvx python3 <<EOF` (neither starts with python).

Tiered by false-positive risk (P3 measure-before-enforce):
  • BLOCK  bare `python`/`python3` as a command — START or after `&&`/`;`/`|`
           (preserves the old block; closes the compound bypass). System python
           lacks every project dep; this is the discipline the old hook enforced.
  • BLOCK  `uvx python`/`uvx python3` WITHOUT `--with` — an isolated env with no
           project deps; never right for a script that imports anything. High
           confidence, low FP.
  • PASS   anything containing `uv run` (incl. `uv run --no-project python3` for
           stdlib throwaways — the documented escape hatch) or `uvx --with …`.

Reads the stdin hook envelope (no CLAUDE_TOOL_* vars). Bash tool only.
Exit 2 + stderr = block; exit 0 = pass. Fails open on any parse error.
"""
from __future__ import annotations

import json
import re
import sys

# python invoked AS a command: at string start or right after a strong shell
# separator (&&, ;, |). Excludes `which python3`, `grep python3 f`,
# `ls /usr/bin/python3`, `echo "do python3"` (python is an ARG / inside a string
# there, preceded by a word+space, not by a separator). Strong separators only,
# to keep the FP surface minimal on a global hook.
_BARE_PY = re.compile(r"(?:^|&&|;|\|)\s*(python3?|python)\b")
# uvx invoking python with no `--with` between `uvx` and `python`.
_UVX_PY = re.compile(r"\buvx\s+(?:(?!--with\b)\S+\s+)*python3?\b")
_UVX_PY_WITH = re.compile(r"\buvx\s+(?:\S+\s+)*--with\b")
_UV_RUN = re.compile(r"\buv\s+run\b")


def verdict(cmd: str):
    """Return ('block'|'pass', message). Pure — unit-testable."""
    if not cmd or not cmd.strip():
        return "pass", ""
    has_uv_run = bool(_UV_RUN.search(cmd))
    # uvx python without --with → isolated, dep-less → block (even alongside uv run elsewhere
    # is implausible; require both absent to be safe)
    if _UVX_PY.search(cmd) and not _UVX_PY_WITH.search(cmd) and not has_uv_run:
        return ("block",
                "BLOCK: `uvx python` runs an isolated interpreter with NO project deps "
                "(this is the `No module named …` failure mode). Use `uv run python3` from "
                "the project root, or `uvx --with <pkg> python3` if you truly need an "
                "ephemeral env.")
    if has_uv_run:
        return "pass", ""
    if _BARE_PY.search(cmd):
        return ("block",
                "BLOCK: use `uv run python3`, not bare `python`/`python3` — system python "
                "lacks project deps (duckdb, etc.). For a stdlib-only throwaway use "
                "`uv run --no-project python3`.")
    return "pass", ""


def _selftest() -> int:
    cases = [
        ("python3 foo.py", "block"),
        ("cd /Users/alien/Projects/intel && python3 setup_duckdb.py", "block"),
        ("uvx python3 - <<'PY'\nimport duckdb\nPY", "block"),
        ("cd x; python3 -c 'import duckdb'", "block"),
        ("uv run python3 foo.py", "pass"),
        ("cd intel && uv run python3 foo.py", "pass"),
        ("uv run --no-project python3 /tmp/x.py", "pass"),
        ("uvx --with duckdb python3 q.py", "pass"),
        ("which python3", "pass"),
        ("grep python3 settings.json", "pass"),
        ("ls /usr/bin/python3", "pass"),
        ("echo 'use python3'", "pass"),
    ]
    bad = 0
    for cmd, want in cases:
        got = verdict(cmd)[0]
        ok = got == want
        bad += not ok
        print(f"  {'ok ' if ok else 'FAIL'} want={want:<5} got={got:<5} {cmd!r}")
    print(f"{'PASS' if not bad else 'FAIL'}: {len(cases)-bad}/{len(cases)}")
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # fail open
    if payload.get("tool_name") not in (None, "Bash"):
        return 0
    cmd = (payload.get("tool_input") or {}).get("command", "")
    action, msg = verdict(cmd)
    if action == "block":
        print(msg, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
