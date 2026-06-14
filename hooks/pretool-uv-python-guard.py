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

FALSE-POSITIVE LESSON (dogfood, 2026-06-14): a first cut blocked any command that
*mentioned* `uvx python3` — it FP-blocked a `git commit -m "... uvx python3 ..."`.
Matching python anywhere in a command string catches prose/heredoc/commit-message
MENTIONS, not just invocations. So:
  • An offending python token counts only if it's an actual INVOCATION — the next
    non-space char is a flag (`-`), heredoc (`<`), or a path (`./x`, `*.py`), or
    it's end-of-command. A token followed by a word / backtick / quote is a
    mention and is ignored.
Tiered by residual FP risk (P3 measure-before-enforce):
  • BLOCK  bare `python`/`python3` at command START (no uv run) — mentions are
           never at position 0; preserves the old block exactly.
  • BLOCK  `uvx python`/`uvx python3` WITHOUT `--with`, when shaped as an
           invocation — isolated dep-less env, never right; shape filter kills the
           mention FP.
  • WARN   bare `python`/`python3` after `&&`/`;`/`|` (no uv run), shaped as an
           invocation — real but FP-prone (prose `ran python3 x.py`), so nudge,
           don't block; escalate to BLOCK later if the warn proves ineffective.
  • PASS   anything with `uv run` (incl. `uv run --no-project python3`) or
           `uvx --with …`, and all mentions.

Reads the stdin hook envelope (no CLAUDE_TOOL_* vars). Bash tool only.
Exit 2 + stderr = block; additionalContext JSON = warn; exit 0 = pass.
Fails open on any parse error.
"""
from __future__ import annotations

import json
import re
import sys

_UV_RUN = re.compile(r"\buv\s+run\b")
_UVX_PY_WITH = re.compile(r"\buvx\s+(?:\S+\s+)*--with\b")
# match positions; shape is validated separately on the char that follows.
_BARE_PY_START = re.compile(r"^\s*(python3?|python)\b")
_BARE_PY_COMPOUND = re.compile(r"(?:&&|;|\|)\s*(python3?|python)\b")
_UVX_PY = re.compile(r"\buvx\s+(?:(?!--with\b)\S+\s+)*(python3?|python)\b")


def _is_invocation(cmd: str, end: int) -> bool:
    """True if what follows the python token at `end` looks like an invocation,
    not a prose/string mention. Invocation: flag (-), heredoc (<), redirect,
    a path/script token (has / or ends .py), or end-of-command."""
    rest = cmd[end:].lstrip()
    if rest == "":
        return True
    if rest[0] in "-<>":
        return True
    first = rest.split()[0] if rest.split() else ""
    if "/" in first or first.endswith(".py"):
        return True
    return False


def _strip_quoted(cmd: str) -> str:
    """Blank out single/double-quoted substrings so python text inside `-m "…"`,
    echo/printf args, and JSON payloads is treated as a MENTION, not an invocation
    (dogfood FP, 2026-06-14: a quoted `… uvx python3 - <<EOF …` test payload and a
    `git commit -m "… uvx python3 …"` both wrongly blocked). A real invocation —
    `cd proj && python3 foo.py` — is unquoted and survives. Under-blocking inside
    quotes is safe; over-blocking a commit/echo is the harm we're killing."""
    cmd = re.sub(r"'[^']*'", "''", cmd)
    cmd = re.sub(r'"[^"]*"', '""', cmd)
    return cmd


def verdict(cmd: str):
    """Return ('block'|'warn'|'pass', message). Pure — unit-testable."""
    if not cmd or not cmd.strip():
        return "pass", ""
    cmd = _strip_quoted(cmd)
    if _UV_RUN.search(cmd):
        return "pass", ""
    # uvx python without --with, shaped as an invocation
    m = _UVX_PY.search(cmd)
    if m and not _UVX_PY_WITH.search(cmd) and _is_invocation(cmd, m.end()):
        return ("block",
                "BLOCK: `uvx python` runs an isolated interpreter with NO project deps "
                "(the `No module named …` failure mode). Use `uv run python3` from the "
                "project root, or `uvx --with <pkg> python3` for a real ephemeral env.")
    # bare python at command start → block (preserves old behavior; never a mention)
    m = _BARE_PY_START.search(cmd)
    if m:
        return ("block",
                "BLOCK: use `uv run python3`, not bare `python`/`python3` — system python "
                "lacks project deps (duckdb, etc.). Stdlib throwaway: `uv run --no-project python3`.")
    # bare python after a separator, shaped as an invocation → warn (FP-prone)
    for m in _BARE_PY_COMPOUND.finditer(cmd):
        if _is_invocation(cmd, m.end()):
            return ("warn",
                    "Heads up: bare `python3` after `&&`/`;` uses system python, which lacks "
                    "project deps (duckdb etc.) — prefer `uv run python3` from the project root.")
    return "pass", ""


def _selftest() -> int:
    cases = [
        ("python3 foo.py", "block"),
        ("uvx python3 - <<'PY'\nimport duckdb\nPY", "block"),
        ("uvx python3 -c 'import duckdb'", "block"),
        ("cd /Users/alien/Projects/intel && python3 setup_duckdb.py", "warn"),
        ("cd x; python3 -c 'import duckdb'", "warn"),
        ("uv run python3 foo.py", "pass"),
        ("cd intel && uv run python3 foo.py", "pass"),
        ("uv run --no-project python3 /tmp/x.py", "pass"),
        ("uvx --with duckdb python3 q.py", "pass"),
        ("which python3", "pass"),
        ("grep python3 settings.json", "pass"),
        ("ls /usr/bin/python3", "pass"),
        ("echo 'use python3'", "pass"),
        # the dogfood FP: commit messages that MENTION python must pass
        ("git commit -m 'fix `uvx python3` bypass and `python3` block'", "pass"),
        ("echo 'run python3 foo.py to test' && ls", "pass"),  # mention inside echo string
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
    if action == "warn":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "additionalContext": msg}}))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
