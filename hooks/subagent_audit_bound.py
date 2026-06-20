#!/usr/bin/env python3
"""Audit-bound contract for filesystem scout dispatches (PostToolUse + pretool inject).

Subagents that audit paths must declare SEARCH_ROOT / GLOB_SCOPE / VERDICT_REQUIRES
so parents can reject wrong-repo false negatives.
"""
from __future__ import annotations

import json
import re
import sys

AUDIT_DISPATCH = re.compile(
    r"\b("
    r"audit|scout|file.?system|codebase.?map|exists\?|path.?exists|"
    r"verify.+(file|path|repo)|read.?only.+(review|scout)|"
    r"grep.+(repo|project|monorepo)|inventory.+(hook|script|recipe)"
    r")\b",
    re.I,
)

BOUND_BLOCK = re.compile(
    r"^SEARCH_ROOT\s*:\s*\S+",
    re.I | re.M,
)
GLOB_BLOCK = re.compile(r"^GLOB_SCOPE\s*:\s*\S+", re.I | re.M)
VERDICT_BLOCK = re.compile(r"^VERDICT_REQUIRES\s*:\s*\S+", re.I | re.M)

INJECT_TEXT = (
    "AUDIT BOUND (required): If you verify filesystem paths, your response MUST "
    "start with these three lines (plain text, no markdown bold):\n"
    "SEARCH_ROOT: <absolute path you searched>\n"
    "GLOB_SCOPE: repo | monorepo | ~/Projects\n"
    "VERDICT_REQUIRES: exists | content-match | not-found"
)


def _prompt_text(env: dict) -> str:
    ti = env.get("tool_input") or {}
    return f"{ti.get('description', '')}\n{ti.get('prompt', '')}"


def _response_text(env: dict) -> str:
    tr = env.get("tool_response")
    if tr is None:
        return ""
    if isinstance(tr, str):
        return tr
    if isinstance(tr, dict):
        for key in ("content", "result", "output", "text"):
            if tr.get(key):
                return str(tr[key])
        return json.dumps(tr)
    return str(tr)


def is_audit_dispatch(text: str) -> bool:
    return bool(text.strip() and AUDIT_DISPATCH.search(text))


def pretool_inject(env: dict) -> str | None:
    """Return inject suffix if audit dispatch lacks bound lines in the prompt."""
    text = _prompt_text(env)
    if not is_audit_dispatch(text):
        return None
    if BOUND_BLOCK.search(text) and GLOB_BLOCK.search(text):
        return None
    return INJECT_TEXT


def posttool_warning(env: dict) -> str | None:
    """Warn if audit dispatch returned without SEARCH_ROOT in the response."""
    if (env.get("tool_name") or "") not in ("", "Agent"):
        return None
    text = _prompt_text(env)
    if not is_audit_dispatch(text):
        return None
    resp = _response_text(env)
    if not resp.strip():
        return None
    missing = []
    if not BOUND_BLOCK.search(resp):
        missing.append("SEARCH_ROOT")
    if not GLOB_BLOCK.search(resp):
        missing.append("GLOB_SCOPE")
    if not VERDICT_BLOCK.search(resp):
        missing.append("VERDICT_REQUIRES")
    if not missing:
        return None
    return (
        f"SUBAGENT AUDIT BOUND MISSING: response lacks {', '.join(missing)} after an "
        "filesystem-audit dispatch — do not trust path-existence verdicts until the "
        "subagent re-runs with explicit search bounds (include ~/Projects/skills when "
        "cross-project)."
    )


def _selftest() -> int:
    cases = [
        ("audit hooks in skills repo", True),
        ("summarize this design doc", False),
    ]
    bad = 0
    for text, want in cases:
        got = is_audit_dispatch(text)
        ok = got == want
        bad += not ok
        print(f"  {'ok' if ok else 'FAIL'} audit={want} {text!r}")
    env = {
        "tool_input": {"description": "scout codebase", "prompt": "verify hook exists"},
        "tool_response": "File not found",
    }
    w = posttool_warning(env)
    print(f"  {'ok' if w else 'FAIL'} posttool warns on missing bound")
    bad += not w
    env2 = {
        "tool_input": {"description": "scout", "prompt": "audit paths"},
        "tool_response": "SEARCH_ROOT: /Users/alien/Projects/skills\nGLOB_SCOPE: monorepo\nVERDICT_REQUIRES: exists\nok",
    }
    w2 = posttool_warning(env2)
    print(f"  {'ok' if not w2 else 'FAIL'} posttool passes complete bound")
    bad += bool(w2)
    print("PASS" if not bad else "FAIL")
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        env = json.loads(raw)
    except json.JSONDecodeError:
        return 0
    mode = sys.argv[1] if len(sys.argv) > 1 else "posttool"
    if mode == "pretool":
        inject = pretool_inject(env)
        if inject:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": inject,
                }
            }))
        return 0
    msg = posttool_warning(env)
    if msg:
        print(json.dumps({"additionalContext": msg}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
