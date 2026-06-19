#!/usr/bin/env python3
# Gov-ID: hook:genomics-pythonpath-guard
# goal: stop genomics inline-python import failures (pipeline_stages without PYTHONPATH=scripts)
# verifier: --selftest
# blast_radius: shared (PreToolUse Bash; cwd-gated to genomics)
"""pretool-genomics-pythonpath-guard.py — steer genomics inline imports to PYTHONPATH=scripts.

Measured: missing-module:pipeline_stages ×40/8d — 38/40 were `uv run python3` from genomics
cwd without PYTHONPATH=scripts. Module lives at scripts/pipeline_stages.py.
"""
from __future__ import annotations

import json
import re
import sys

_GENOMICS = re.compile(r"/Projects/genomics(?:/|$)")
_HAS_PYRUN = re.compile(r"\buv\s+run\b.*\bpython")
_HAS_PYPATH = re.compile(r"\bPYTHONPATH\s*=\s*scripts\b")
_IMPORT_LOCAL = re.compile(
    r"\b(?:from|import)\s+(pipeline_stages|pipeline_orchestrator|wgs_config|orchestrator)\b"
)
_SCRIPT_PATH = re.compile(r"\bscripts/(?:pipeline_stages|pipeline_orchestrator|wgs_config)\b")


def verdict(cmd: str, cwd: str = "") -> tuple[str, str]:
    if not cmd or not _GENOMICS.search(cwd or ""):
        return "pass", ""
    if not _HAS_PYRUN.search(cmd):
        return "pass", ""
    if _HAS_PYPATH.search(cmd):
        return "pass", ""
    if _SCRIPT_PATH.search(cmd):
        return "pass", ""
    if not _IMPORT_LOCAL.search(cmd):
        return "pass", ""
    return (
        "block",
        "BLOCK: genomics inline python imports `pipeline_stages`/`wgs_config`/orchestrator "
        "modules — prefix `PYTHONPATH=scripts` (e.g. `PYTHONPATH=scripts uv run python3 -c '…'`) "
        "or import via `scripts.pipeline_stages`. See genomics CLAUDE.md.",
    )


def _selftest() -> int:
    g = "/Users/alien/Projects/genomics"
    cases = [
        (g, 'uv run python3 -c "from pipeline_stages import STAGES"', "block"),
        (g, "PYTHONPATH=scripts uv run python3 -c 'from pipeline_stages import STAGES'", "pass"),
        (g, 'uv run python3 scripts/pipeline_stages.py', "pass"),
        ("/Users/alien/Projects/intel", 'uv run python3 -c "from pipeline_stages import STAGES"', "pass"),
        (g, "uv run python3 -m pytest tests/foo.py", "pass"),
    ]
    bad = 0
    for cwd, cmd, want in cases:
        got = verdict(cmd, cwd)[0]
        ok = got == want
        bad += not ok
        print(f"  {'ok' if ok else 'FAIL'} want={want} got={got} {cmd!r}")
    print("PASS" if not bad else "FAIL", f"{len(cases)-bad}/{len(cases)}")
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
    cwd = payload.get("cwd") or ""
    action, msg = verdict(cmd, cwd)
    if action == "block":
        print(msg, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
