#!/usr/bin/env python3
"""scan_tool_failures.py — Tier 1 of /observe failures: which tools are actually
BROKEN, mined deterministically from agentlogs (no LLM, $0).

Why: the health loop checks proxies (hooks/launchd/indexer) and missed a dead
`corpus` CLI that errored for days. The signal was in the logs the whole time —
errored tool_calls whose result event text says `ModuleNotFoundError: No module
named 'corpus_core.cli'`. (2026-06-14, user: "don't you check the logs for what
doesn't work?")

The precision trick (learned the hard way over 4 noisy probes): filter to
LAUNCH-FAILURE error text FIRST, then group. A tool that returns nonzero by
design (ruff lint, grep no-match, `cmd || fallback`, a curl 404 inside a working
CLI) never prints `ModuleNotFoundError` / `command not found` / `ImportError`.
Those patterns mean the tool itself couldn't start — exactly "broken," not
"ran and returned nonzero."

Output: ranked broken-tool report (JSON with --json) for Tier-2 (Haiku triage)
and Tier-3 (deep dispatch) to consume. Report-only; reads agentlogs.db read-only.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB = Path.home() / ".claude" / "agentlogs.db"

# A REAL launch failure has a crash SIGNATURE, not just the keyword. The keyword
# alone matches source code an agent read (`except ImportError:`), prose, and
# commit trailers — the FP mode seen on the first run. Require the actual raised
# error / shell error, clustered by root cause.
_TRACEBACK = "Traceback (most recent call last):"
_RAISED_IMPORT = re.compile(r"(?m)^\s*(ModuleNotFoundError|ImportError|cannot import name)\b")
_NO_MODULE = re.compile(r"No module named ['\"]([A-Za-z0-9_.]+)['\"]")
_SHIM = re.compile(r'File "[^"]*/bin/([A-Za-z0-9_.-]+)", line \d+, in <module>')
# command-not-found over-matches prose; require a real shell line/eval prefix
_CMD_NOTFOUND_REAL = re.compile(
    r"(?:line \d+: ([A-Za-z0-9_.-]+): command not found"
    r"|\(eval\):\d+: command not found: ([A-Za-z0-9_.-]+)"
    r"|(?:zsh|bash): ([A-Za-z0-9_.-]+): command not found)"
)


def classify(text: str):
    """Return (cluster_key, key_line) for a REAL launch failure, else None."""
    # 1. Python crash: Traceback header + a raised import error (NOT `except ...:`)
    if _TRACEBACK in text and _RAISED_IMPORT.search(text):
        mod = _NO_MODULE.search(text)
        shim = _SHIM.search(text)
        if shim and mod:
            key = f"broken-cli:{shim.group(1)} (missing {mod.group(1)})"
        elif mod:
            key = f"missing-module:{mod.group(1)}"
        else:
            key = "import-error"
        line = next((l.strip() for l in text.splitlines()
                     if _RAISED_IMPORT.match(l) or _RAISED_IMPORT.search(l)), key)
        return key, line[:160]
    # 2. Real shell command-not-found (has a shell line/eval prefix)
    m = _CMD_NOTFOUND_REAL.search(text)
    if m:
        cmd = next(g for g in m.groups() if g)
        return f"command-not-found:{cmd}", m.group(0).strip()[:160]
    return None


def scan(days: int = 21) -> list[dict]:
    if not DB.exists():
        return []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    con = sqlite3.connect(f"file://{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    agg: dict[str, dict] = defaultdict(
        lambda: {"fails": 0, "days": set(), "runs": set(), "sample": "", "last": ""}
    )
    try:
        q = (
            "SELECT t.run_id, substr(t.ts_start,1,10) d, t.ts_start, e.text "
            "FROM tool_calls t JOIN events e ON e.tool_call_id = t.tool_call_id "
            "WHERE t.status='error' AND e.text IS NOT NULL AND t.ts_start > ?"
        )
        for r in con.execute(q, (cutoff,)):
            verdict = classify(r["text"] or "")
            if verdict is None:
                continue
            key, line = verdict
            e = agg[key]
            e["fails"] += 1
            e["days"].add(r["d"])
            e["runs"].add(r["run_id"])
            if r["ts_start"] > e["last"]:
                e["last"] = r["ts_start"]
                e["sample"] = line
    finally:
        con.close()
    out = [
        {
            "cluster": b,
            "fails": v["fails"],
            "distinct_days": len(v["days"]),
            "distinct_runs": len(v["runs"]),
            "last_seen": v["last"][:16],
            "sample": v["sample"],
        }
        for b, v in agg.items()
    ]
    out.sort(key=lambda x: (x["distinct_days"], x["distinct_runs"], x["fails"]), reverse=True)
    return out


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Tier 1: deterministic broken-tool miner from agentlogs.")
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--json", action="store_true", help="emit JSON for Tier-2/3 consumers")
    args = ap.parse_args()

    rows = scan(days=args.days)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print(f"✓ no launch-failure (broken-tool) signatures in tool_calls over the last {args.days}d")
        return 0
    print(f"Broken tools (launch failures in real use, last {args.days}d), worst-first:\n")
    print(f"  {'cluster':<34}{'days':>5}{'runs':>5}{'fails':>6}  {'last':<17}sample")
    for x in rows:
        print(f"  {x['cluster']:<34}{x['distinct_days']:>5}{x['distinct_runs']:>5}{x['fails']:>6}  "
              f"{x['last_seen']:<17}{x['sample'][:54]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
