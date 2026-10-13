#!/usr/bin/env python3
# Gov-ID: hook:emb-project-guard
# goal: stop ModuleNotFoundError: emb when agents run blindspot_miner / emb.embed
#       via bare `uv run` instead of `uv run --project ~/Projects/emb`
# verifier: --selftest
# blast_radius: shared (PreToolUse Bash; Cursor shell guards)
"""pretool-emb-project-guard.py — steer emb-touching python into emb's uv project.

Measured (observe 2026-07-20 failures): missing-module:emb ×3/2d — Codex/Claude
invoking `scripts/blindspot_miner.py` or `from emb.embed import …` with
`uv run python3` from agent-infra/evals cwd. emb (torch) must stay in
~/Projects/emb; agent-infra never inherits it. Prefer rewrite; fail-open.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_EMB_PROJECT = Path.home() / "Projects" / "emb"
_UV_RUN = re.compile(r"\buv\s+run\b")
# Only commands that execute Python can hit ModuleNotFoundError; `rg "from emb"` cannot.
_RUNS_PYTHON = re.compile(r"\b(?:python3?(?:\.\d+)?|uv\s+run|pytest)\b")
_HAS_EMB_PROJECT = re.compile(
    r"--project\s+(?:\S*/)?(?:Projects/)?emb(?:/|\s|$)"
    r"|--directory\s+(?:\S*/)?(?:Projects/)?emb(?:/|\s|$)"
)
_NEEDS_EMB = re.compile(
    r"\bblindspot_miner\.py\b"
    r"|\b(?:from|import)\s+emb(?:\.|\b)"
    r"|\bimportlib\.import_module\(\s*['\"]emb(?:\.|['\"])"
    r"|\b__import__\(\s*['\"]emb(?:\.|['\"])"
    r"|\bemb\.embed\b"
)


def _emb_project() -> Path:
    env = os.environ.get("EMB_PROJECT")
    if env:
        return Path(env).expanduser()
    return _EMB_PROJECT


def _needs_emb(cmd: str) -> bool:
    return bool(_NEEDS_EMB.search(cmd or ""))


def _insert_project(cmd: str, emb: Path) -> str | None:
    m = _UV_RUN.search(cmd)
    if not m:
        return None
    rest = cmd[m.end() :]
    if re.match(r"\s+--(?:project|directory)\b", rest):
        # Already pinned to some project — only rewrite if it's NOT emb.
        if _HAS_EMB_PROJECT.search(cmd):
            return None
        # Wrong --project (e.g. agent-infra): leave alone — block path below.
        return None
    return cmd[: m.end()] + f" --project {emb}" + cmd[m.end() :]


def verdict(cmd: str, cwd: str = "") -> tuple[str, str]:
    """Return ('block'|'rewrite'|'pass', message_or_new_cmd)."""
    del cwd  # fleet-wide; not cwd-gated
    if not cmd or not cmd.strip():
        return "pass", ""
    if not _needs_emb(cmd) or not _RUNS_PYTHON.search(cmd):
        return "pass", ""
    if _HAS_EMB_PROJECT.search(cmd):
        return "pass", ""

    emb = _emb_project()
    if _UV_RUN.search(cmd):
        new = _insert_project(cmd, emb)
        if new and new != cmd:
            return "rewrite", new
        # uv run already has --project/--directory pointing elsewhere
        return (
            "block",
            "BLOCK: this command imports `emb` / runs `blindspot_miner.py` but "
            f"`uv run` is pinned to a non-emb project. Use: "
            f"`uv run --project {emb} python3 …` (or `just blindspot`). "
            "Do NOT pip-install emb/torch into agent-infra.",
        )

    return (
        "block",
        "BLOCK: emb lives in ~/Projects/emb (torch). Run: "
        f"`uv run --project {emb} python3 …` or `just blindspot`. "
        "Bare python3 / wrong-cwd uv will ModuleNotFoundError: emb.",
    )


def _selftest() -> int:
    emb = str(_emb_project())
    cases: list[tuple[str, str]] = [
        ('uv run python3 scripts/blindspot_miner.py --days 7', "rewrite"),
        ('uv run python3 -c "from emb.embed import EmbeddingEngine"', "rewrite"),
        (f'uv run --project {emb} python3 scripts/blindspot_miner.py', "pass"),
        ("just blindspot", "pass"),
        ("uv run python3 scripts/doctor.py", "pass"),
        ('rg -n "^from emb|import emb" src/', "pass"),
        ('python3 -c "from emb.embed import EmbeddingEngine"', "block"),
        (
            'uv run --project /Users/alien/Projects/agent-infra python3 '
            'scripts/blindspot_miner.py',
            "block",
        ),
    ]
    bad = 0
    for cmd, want in cases:
        got, msg = verdict(cmd)
        ok = got == want
        if ok and want == "rewrite":
            ok = f"--project {emb}" in msg
        bad += not ok
        print(f"  {'ok' if ok else 'FAIL'} want={want} got={got} cmd={cmd!r}")
        if want == "rewrite" and got == "rewrite":
            print(f"       → {msg}")
    print("PASS" if not bad else "FAIL", f"{len(cases) - bad}/{len(cases)}")
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
    action, msg = verdict(cmd, cwd)
    if action == "block":
        print(msg, file=sys.stderr)
        return 2
    if action == "rewrite" and msg:
        updated = dict(ti)
        updated["command"] = msg
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "updatedInput": updated,
                    }
                }
            )
        )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
