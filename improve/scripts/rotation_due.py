#!/usr/bin/env python3
"""rotation_due.py — derive /improve maintain P3 rotation due-ness from the action ledger.

The P3 table's "what ran when" used to live in the agent's head each tick
(state-externalization gap, flagged 2026-07-05). This script is the single
source of truth for rotation CADENCES; the SKILL.md table documents HOW to
run each task and defers to this for due-ness. `just freshness` still owns
the sweep sources (trending-scout, agent-infra-sweep); per-tick and
event-driven rows are deliberately absent here.

Logging contract (SKILL.md maintain): when a tick picks a rotation task,
append {"ts": ..., "action": "rotation", "target": "<task-key>"} to
maintenance-actions.jsonl. Legacy rows where action == task-key also count.

Usage:
    uv run python3 rotation_due.py [--ledger PATH] [--json]

Output: one row per task — last run, age, DUE/ok/never — plus denominators
(ledger rows scanned/parsed) per the harvest denominator rule.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path.home() / "Projects" / "agent-infra" / "maintenance-actions.jsonl"

# task-key -> (cadence_days, how)  — the table of record for rotation cadence.
ROTATION: dict[str, tuple[int, str]] = {
    "sessions-observe": (1, "/observe sessions"),
    "supervision-observe": (1, "/observe supervision"),
    "blindspot-convert": (1, "read .claude/blindspot-digest.md -> detector proposal"),
    "gov-report-act": (1, "read artifacts/gov/gov-report.md, act on 3 invariants"),
    "maintain-motor": (1, "uv run python3 scripts/maintain_tick.py [--subtract --ablate]"),
    "act-drain": (1, "just act-drain (or read ~/.claude/act-drain-digest.md)"),
    "db-freshness": (1, "check DB timestamps, flag >30d"),
    "cross-check-outputs": (1, "pick T1/T2 variant, cross-check vs biomedical MCP"),
    "doctor-health": (1, "uv run python3 scripts/doctor.py"),
    "session-cost": (1, "flag cost/no-commit anomalies in recent sessions"),
    "steer-mine": (7, "just steer-mine"),
    "finding-drain": (7, "/improve harvest"),
    "failures-observe": (7, "/observe failures"),
    "shell-env": (7, "doctor.py global:shell-env-* checks"),
    "architecture-observe": (7, "/observe architecture"),
    "leverage-scan": (7, "/leverage"),
    "memo-staleness": (7, "ACTIVE research memos vs recent file changes"),
    "code-quality": (7, "/project-upgrade --quick"),
    "calibration-canary": (7, "calibration-canary.py --mode sampling --difficulty hard"),
    "infra-coverage": (30, "git log -> categorize fixes by detection source"),
}


def load_last_runs(ledger: Path) -> tuple[dict[str, datetime], int, int]:
    last: dict[str, datetime] = {}
    scanned = parsed = 0
    if not ledger.exists():
        return last, scanned, parsed
    for line in ledger.read_text().splitlines():
        scanned += 1
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict):
            continue
        parsed += 1
        action = d.get("action", "")
        target = d.get("target", "")
        key = target if action == "rotation" and target in ROTATION else (
            action if action in ROTATION else None
        )
        if key is None:
            continue
        try:
            ts = datetime.fromisoformat(str(d.get("ts", "")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if key not in last or ts > last[key]:
            last[key] = ts
    return last, scanned, parsed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    last, scanned, parsed = load_last_runs(a.ledger)
    now = datetime.now(timezone.utc)
    rows = []
    for key, (cadence, how) in ROTATION.items():
        ts = last.get(key)
        if ts is None:
            age, status = None, "never"
        else:
            age = (now - ts).days
            status = "DUE" if age >= cadence else "ok"
        rows.append(
            {
                "task": key,
                "cadence_days": cadence,
                "last_run": ts.isoformat() if ts else None,
                "age_days": age,
                "status": status,
                "how": how,
            }
        )
    rows.sort(key=lambda r: (r["status"] == "ok", -(r["age_days"] if r["age_days"] is not None else 10**6)))

    if a.json:
        json.dump({"scanned": scanned, "parsed": parsed, "rows": rows}, sys.stdout, indent=2)
        return 0

    print(f"rotation_due — ledger rows scanned {scanned} / parsed {parsed}")
    print(f"  {'task':24s} {'cad':>4s} {'age':>5s}  status  how")
    for r in rows:
        age = "-" if r["age_days"] is None else f"{r['age_days']}d"
        print(f"  {r['task']:24s} {r['cadence_days']:3d}d {age:>5s}  {r['status']:6s}  {r['how']}")
    due = [r for r in rows if r["status"] in ("DUE", "never")]
    print(f"\n  {len(due)} due/never — pick the top one this tick (ONE task per tick).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
