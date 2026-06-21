#!/usr/bin/env python3
"""observe_gates.py — deterministic observe preflight + promotion gates.

Subcommands (composable; each writes inspectable JSON):
  health          → stdout JSON; indexer + launchd probe
  promote-check   → promotion-verdicts.jsonl in artifact dir
  saturation      → stdout JSON; overlap vs prior runs
  preflight       → preflight.json + promotion-verdicts.jsonl (run before digest promotion)

Usage:
  python3 observe_gates.py preflight --artifact-root artifacts/observe/2026-06-21-v3
  python3 observe_gates.py promote-check --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from observe_artifacts import artifact_root
from observe_gates_lib import (
    check_health,
    promote_check,
    run_preflight,
    saturation_check,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic /observe gates (health, promotion, saturation)")
    ap.add_argument("--artifact-root", type=Path, help="Observe artifact directory")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health", help="Indexer + launchd health JSON")
    pc = sub.add_parser("promote-check", help="Mechanical promotion verdicts for candidates.jsonl")
    pc.add_argument("--json", action="store_true", help="Print verdicts JSON to stdout")
    pc.add_argument("--allow-promotions", action="store_true",
                    help="Ignore indexer health block (debug only)")
    sub.add_parser("saturation", help="Novelty vs prior observe runs")
    pf = sub.add_parser("preflight", help="health + saturation + promote-check → preflight.json")
    pf.add_argument("--quiet", action="store_true")

    args = ap.parse_args()
    root = args.artifact_root or artifact_root()

    if args.cmd == "health":
        print(json.dumps(check_health().to_dict(), indent=2))
        return 0

    if args.cmd == "saturation":
        print(json.dumps(saturation_check(root), indent=2))
        return 0

    if args.cmd == "promote-check":
        promotions_allowed = True if args.allow_promotions else None
        verdicts = promote_check(root, promotions_allowed=promotions_allowed)
        verdicts_path = root / "promotion-verdicts.jsonl"
        verdicts_path.parent.mkdir(parents=True, exist_ok=True)
        with verdicts_path.open("w", encoding="utf-8") as fh:
            for v in verdicts:
                fh.write(json.dumps(v.to_dict(), ensure_ascii=False) + "\n")
        if args.json:
            print(json.dumps([v.to_dict() for v in verdicts], indent=2))
        else:
            for v in verdicts:
                gates = " ".join(f"{k}={val}" for k, val in v.gates.items())
                print(f"{v.verdict:16} {v.candidate_id}  ({gates})")
                for r in v.reasons:
                    print(f"    · {r}")
        out = root / "promotion-verdicts.jsonl"
        if not args.json:
            print(f"\n→ {len(verdicts)} verdict(s); re-run `preflight` to refresh preflight.json")
        return 0

    if args.cmd == "preflight":
        report = run_preflight(root)
        if not args.quiet:
            h = report["health"]
            s = report["saturation"]
            c = report["promotion_counts"]
            print(f"preflight → {root / 'preflight.json'}")
            print(f"  indexer_ok={h['indexer_ok']}  promotions_allowed={report['promotions_allowed']}")
            print(f"  saturation={s['saturated']} (id_overlap={s['id_overlap']}, token={s['token_overlap']})")
            print(f"  verdicts: {c}")
            if h.get("warnings"):
                for w in h["warnings"]:
                    print(f"  ! {w}")
        return 0 if report["promotions_allowed"] else 2

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
