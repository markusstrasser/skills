#!/usr/bin/env python3
# Gov-ID: hook:uv-python-guard
# goal: stop "ModuleNotFoundError" launch failures from bare/uvx python invocations
#       that skip the project venv (system python / isolated uvx env lack deps).
# verifier: --selftest
# blast_radius: shared
"""pretool-uv-python-guard.py — steer python invocations to `uv run`.

2026-06-21: when cwd has pyproject.toml or uv.lock, auto-REWRITE bare python
invocations via PreToolUse updatedInput (gate-ergonomics transform) instead of
only blocking. uvx-python-without-deps still blocks."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_UV_RUN = re.compile(r"\buv\s+run\b")
_UVX_PY_WITH = re.compile(r"\buvx\s+(?:\S+\s+)*--with\b")
_BARE_PY_START = re.compile(r"^\s*(python3?|python)\b")
_BARE_PY_COMPOUND = re.compile(r"(?:&&|;|\|)\s*(python3?|python)\b")
_UVX_PY = re.compile(r"\buvx\s+(?:(?!--with\b)\S+\s+)*(python3?|python)\b")


def _is_invocation(cmd: str, end: int) -> bool:
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
    cmd = re.sub(r"'[^']*'", "''", cmd)
    cmd = re.sub(r'"[^"]*"', '""', cmd)
    return cmd


def _project_has_uv(cwd: str) -> bool:
    if not cwd:
        return False
    root = Path(cwd)
    return (root / "pyproject.toml").is_file() or (root / "uv.lock").is_file()


def _in_quotes(cmd: str, pos: int) -> bool:
    """Crude but safe: odd count of ' or \" before pos → inside a quoted region."""
    return cmd.count("'", 0, pos) % 2 == 1 or cmd.count('"', 0, pos) % 2 == 1


def _rewrite_bare_python(cmd: str) -> str | None:
    """Rewrite bare python invocations to `uv run python`. None if unchanged.

    All spans are collected against the ORIGINAL string and applied in reverse
    offset order — splicing left-to-right after an insertion shifts every later
    offset by +7 ("uv run ") and corrupts the command (2026-07-06 exhibits:
    `/dev/null || python3` → `/dev/nuv…`, `jsonl | python3` → `.juv…python3python3`).
    Spans inside quoted regions are skipped (a `python3` in a commit message must
    never be spliced)."""
    if _UV_RUN.search(cmd):
        return None
    spans: list[tuple[int, int, str]] = []
    m = _BARE_PY_START.search(cmd)
    if m and _is_invocation(cmd, m.end()) and not _in_quotes(cmd, m.start(1)):
        spans.append((m.start(1), m.end(1), m.group(1)))
    for m in _BARE_PY_COMPOUND.finditer(cmd):
        if _is_invocation(cmd, m.end()) and not _in_quotes(cmd, m.start(1)):
            spans.append((m.start(1), m.end(1), m.group(1)))
    if not spans:
        return None
    out = cmd
    for s, e, py in sorted(spans, reverse=True):
        out = out[:s] + f"uv run {py}" + out[e:]
    return out if out != cmd else None


def verdict(cmd: str, *, can_rewrite: bool = False) -> tuple[str, str]:
    """Return ('block'|'rewrite'|'pass', message_or_new_cmd)."""
    if not cmd or not cmd.strip():
        return "pass", ""
    bare = _strip_quoted(cmd)
    if _UV_RUN.search(bare):
        return "pass", ""
    m = _UVX_PY.search(bare)
    if m and not _UVX_PY_WITH.search(bare) and _is_invocation(bare, m.end()):
        return ("block",
                "BLOCK: `uvx python` runs an isolated interpreter with NO project deps "
                "(the `No module named …` failure mode). Use `uv run python3` from the "
                "project root, or `uvx --with <pkg> python3` for a real ephemeral env.")
    if can_rewrite:
        new = _rewrite_bare_python(cmd)
        if new:
            return "rewrite", new
    m = _BARE_PY_START.search(bare)
    if m:
        return ("block",
                "BLOCK: use `uv run python3`, not bare `python`/`python3` — system python "
                "lacks project deps (duckdb, etc.). Stdlib throwaway: `uv run --no-project python3`.")
    for m in _BARE_PY_COMPOUND.finditer(bare):
        if _is_invocation(bare, m.end()):
            return ("block",
                    "BLOCK: bare `python3` after `&&`/`;` uses system python, which "
                    "lacks project deps (duckdb etc.) — use `cd <proj> && uv run python3 …`.")
    return "pass", ""


def _selftest() -> int:
    cases = [
        ("python3 foo.py", "block"),
        ("uvx python3 - <<'PY'\nimport duckdb\nPY", "block"),
        ("cd /Users/alien/Projects/intel && python3 setup_duckdb.py", "block"),
        ("uv run python3 foo.py", "pass"),
        ("which python3", "pass"),
        ("git commit -m 'fix `uvx python3` bypass'", "pass"),
    ]
    bad = 0
    for cmd, want in cases:
        got = verdict(cmd, can_rewrite=False)[0]
        ok = got == want
        bad += not ok
        print(f"  {'ok ' if ok else 'FAIL'} want={want:<7} got={got:<7} {cmd!r}")
  # rewrite path
    rw_cases = [
        ("python3 foo.py", "uv run python3 foo.py"),
        ("cd x && python3 -c 'import duckdb'", "cd x && uv run python3 -c 'import duckdb'"),
        ("uv run python3 foo.py", None),
        ("which python3", None),
        # multi-match offset regression (2026-07-06 corruption exhibits):
        ("tail -1 x.jsonl 2>/dev/null || python3 a.py | python3 -m json.tool",
         "tail -1 x.jsonl 2>/dev/null || uv run python3 a.py | uv run python3 -m json.tool"),
        ("python3 d.py --drain 2>&1 | tail -6; tail -1 x.jsonl | python3 -m json.tool",
         "uv run python3 d.py --drain 2>&1 | tail -6; tail -1 x.jsonl | uv run python3 -m json.tool"),
        # quoted python must never be spliced:
        ("git commit -m 'run && python3 later'", None),
    ]
    for cmd, want in rw_cases:
        got = verdict(cmd, can_rewrite=True)
        if want is None:
            ok = got[0] == "pass"
        else:
            ok = got[0] == "rewrite" and got[1] == want
        bad += not ok
        print(f"  {'ok ' if ok else 'FAIL'} rewrite want={want!r} got={got} cmd={cmd!r}")
    print(f"{'FAIL' if bad else 'PASS'}: {bad} failures")
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") not in (None, "Bash", "Shell"):
        return 0
    ti = payload.get("tool_input") or {}
    cmd = ti.get("command", "")
    cwd = payload.get("cwd") or ""
    can_rewrite = _project_has_uv(cwd)
    action, msg = verdict(cmd, can_rewrite=can_rewrite)
    if action == "block":
        print(msg, file=sys.stderr)
        return 2
    if action == "rewrite" and msg:
        updated = dict(ti)
        updated["command"] = msg
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": updated,
            }
        }))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
