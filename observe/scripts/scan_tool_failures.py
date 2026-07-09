#!/usr/bin/env python3
"""scan_tool_failures.py — Tier 1 of /observe failures: which tools are actually
BROKEN, mined deterministically from agentlogs (no LLM, $0).

The precision trick: filter to LAUNCH-FAILURE and SHELL-ENV signatures FIRST, cluster by root
cause, count DISTINCT tool_calls (not events), and split interactive-agent vs
harness invocations so cron noise does not promote as agent behavior.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB = Path.home() / ".claude" / "agentlogs.db"

_TRACEBACK = "Traceback (most recent call last):"
_RAISED_IMPORT = re.compile(r"(?m)^\s*(ModuleNotFoundError|ImportError|cannot import name)\b")
_NO_MODULE = re.compile(r"No module named ['\"]([A-Za-z0-9_.]+)['\"]")
_CANNOT_IMPORT = re.compile(r"cannot import name ['\"]([A-Za-z0-9_]+)['\"] from ['\"]?([A-Za-z0-9_.]+)")
_SHIM = re.compile(r'File "[^"]*/bin/([A-Za-z0-9_.-]+)", line \d+, in <module>')
_CMD_NOTFOUND_REAL = re.compile(
    r"(?:line \d+: ([A-Za-z0-9_.-]+): command not found"
    r"|\(eval\):\d+: command not found: ([A-Za-z0-9_.-]+)"
    r"|(?:zsh|bash): ([A-Za-z0-9_.-]+): command not found)"
)
_LAUNCHD_MARKERS = re.compile(
    r"\b(launchctl|LaunchAgents|pulse-tick|maintain-tick|agentlogs\s+index|"
    r"com\.agent-infra\.)\b",
    re.I,
)
_PRETOOL_HOOK_BLOCK = re.compile(r"PreToolUse:(?:Bash|Shell) hook error", re.I)
_ZSH_NOMATCH = re.compile(r"(?:\(eval\):\d+: )?no matches found:")
_ZSH_ALIAS_COLLISION = re.compile(r"defining function based on alias")
_ZSH_PARSE = re.compile(r"(?:\(eval\):\d+: )?parse error near")


def _hook_block(text: str) -> bool:
    return bool(_PRETOOL_HOOK_BLOCK.search(text))


def classify(text: str):
    """Return (cluster_key, key_line) for a REAL launch/shell-env failure, else None."""
    if _hook_block(text):
        return None
    if _ZSH_ALIAS_COLLISION.search(text):
        line = next((l.strip() for l in text.splitlines() if _ZSH_ALIAS_COLLISION.search(l)), "alias collision")
        return "zsh-env:alias-collision", line[:160]
    if _ZSH_NOMATCH.search(text):
        line = next((l.strip() for l in text.splitlines() if _ZSH_NOMATCH.search(l)), "nomatch")
        return "zsh-env:nomatch", line[:160]
    if _ZSH_PARSE.search(text) and "(eval)" in text:
        line = next((l.strip() for l in text.splitlines() if _ZSH_PARSE.search(l)), "parse error")
        return "zsh-env:parse-error", line[:160]
    if _TRACEBACK in text and _RAISED_IMPORT.search(text):
        mod = _NO_MODULE.search(text)
        shim = _SHIM.search(text)
        if shim and mod:
            key = f"broken-cli:{shim.group(1)} (missing {mod.group(1)})"
        elif mod:
            key = f"missing-module:{mod.group(1)}"
        else:
            ci = _CANNOT_IMPORT.search(text)
            key = f"import-error:{ci.group(1)}@{ci.group(2).split('.')[-1]}" if ci else "import-error"
        line = next((l.strip() for l in text.splitlines()
                     if _RAISED_IMPORT.match(l) or _RAISED_IMPORT.search(l)), key)
        return key, line[:160]
    m = _CMD_NOTFOUND_REAL.search(text)
    if m:
        cmd = next(g for g in m.groups() if g)
        return f"command-not-found:{cmd}", m.group(0).strip()[:160]
    return None


def invoker_kind(args_json: str | None, vendor: str | None) -> str:
    """interactive_agent | harness | unknown"""
    blob = args_json or ""
    if _LAUNCHD_MARKERS.search(blob):
        return "harness"
    if vendor in ("claude", "codex", "cursor"):
        return "interactive_agent"
    return "unknown"


def scan(days: int = 21) -> list[dict]:
    if not DB.exists():
        return []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    con = sqlite3.connect(f"file://{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    agg: dict[str, dict] = defaultdict(
        lambda: {
            "tool_calls": set(),
            "days": set(),
            "runs": set(),
            "sessions": set(),
            "interactive": 0,
            "harness": 0,
            "unknown": 0,
            "sample": "",
            "last": "",
        }
    )
    try:
        q = (
            "SELECT t.tool_call_id, t.run_id, t.args_json, t.ts_start, e.text, "
            "r.vendor, s.session_uuid "
            "FROM tool_calls t "
            "JOIN events e ON e.tool_call_id = t.tool_call_id "
            "JOIN runs r ON r.run_id = t.run_id "
            "JOIN sessions s ON s.session_pk = r.session_pk "
            "WHERE t.status='error' AND e.text IS NOT NULL AND t.ts_start > ?"
        )
        for r in con.execute(q, (cutoff,)):
            verdict = classify(r["text"] or "")
            if verdict is None:
                continue
            key, line = verdict
            e = agg[key]
            e["tool_calls"].add(r["tool_call_id"])
            d = (r["ts_start"] or "")[:10]
            e["days"].add(d)
            e["runs"].add(r["run_id"])
            if r["session_uuid"]:
                e["sessions"].add(r["session_uuid"][:8])
            kind = invoker_kind(r["args_json"], r["vendor"])
            e[kind] = e.get(kind, 0) + 1
            if (r["ts_start"] or "") > e["last"]:
                e["last"] = r["ts_start"]
                e["sample"] = line
    finally:
        con.close()
    out = []
    for b, v in agg.items():
        tc = len(v["tool_calls"])
        out.append({
            "cluster": b,
            "fails": tc,
            "distinct_days": len(v["days"]),
            "distinct_runs": len(v["runs"]),
            "distinct_sessions": len(v["sessions"]),
            "interactive_agent": v["interactive"],
            "harness": v["harness"],
            "unknown": v["unknown"],
            "invoker_primary": (
                "interactive_agent" if v["interactive"] >= v["harness"]
                else "harness" if v["harness"] > v["interactive"]
                else "mixed"
            ),
            "last_seen": v["last"][:16],
            "sample": v["sample"],
        })
    out.sort(key=lambda x: (x["distinct_days"], x["distinct_runs"], x["fails"]), reverse=True)
    return out


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Tier 1: deterministic broken-tool miner from agentlogs.")
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--json", action="store_true", help="emit JSON for Tier-2/3 consumers")
    ap.add_argument("--interactive-only", action="store_true",
                    help="drop clusters whose primary invoker is harness")
    args = ap.parse_args()

    rows = scan(days=args.days)
    if args.interactive_only:
        rows = [r for r in rows if r["invoker_primary"] != "harness"]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print(f"✓ no launch-failure (broken-tool) signatures in tool_calls over the last {args.days}d")
        return 0
    print(f"Broken tools (launch failures in real use, last {args.days}d), worst-first:\n")
    print(f"  {'cluster':<34}{'days':>5}{'runs':>5}{'fails':>6}{'inv':>12}  {'last':<17}sample")
    for x in rows:
        print(f"  {x['cluster']:<34}{x['distinct_days']:>5}{x['distinct_runs']:>5}{x['fails']:>6}"
              f"{x['invoker_primary']:>12}  {x['last_seen']:<17}{x['sample'][:44]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
