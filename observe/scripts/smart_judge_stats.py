#!/usr/bin/env python3
"""smart_judge_stats.py — read the smart-judge Stop-hook shadow log and report the
firing rate, per-vector counts, and fired cases for precision eyeballing.

The closed-loop measurement view for stop-smart-judge.sh (the LLM adjudication layer
for judgment-class disciplines: verify_before_claim / partial_completion / over_caution).
Use during the shadow period to read PPV before graduating a vector to enforce.

  uv run python3 smart_judge_stats.py [path-to-shadow.jsonl]
  (default: ~/.claude/smart-judge-shadow.jsonl)
"""
import json, os, sys, collections

LOG = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.claude/smart-judge-shadow.jsonl")
try:
    rows = [json.loads(l) for l in open(os.path.expanduser(LOG)) if l.strip()]
except FileNotFoundError:
    print("no shadow log yet:", LOG); sys.exit(0)

n = len(rows)
fired = [r for r in rows if r.get("fired")]
vc = collections.Counter(v for r in fired for v in r["fired"])
proj = collections.Counter(r.get("project", "?") for r in fired)
lat = [r.get("latency_s", 0) for r in rows]

print(f"=== smart-judge shadow: {n} judged (post pre-filter) ===")
print(f"fired >=1 vector: {len(fired)} ({100*len(fired)//max(n,1)}%)   clean: {n-len(fired)}")
print(f"by vector: {dict(vc)}")
print(f"by project (fired): {dict(proj.most_common(8))}")
print(f"latency: avg {sum(lat)/max(n,1):.1f}s  max {max(lat) if lat else 0}s")
print()
print("=== FIRED CASES (eyeball: TRUE violation or false-positive?) ===")
for i, r in enumerate(fired):
    print(f"--- {i+1}. {r['fired']}  [{r.get('project','?')}] {r.get('ts','')} ---")
    for v, w in r.get("why", {}).items():
        print(f"   {v}: {w}")
    print(f"   MSG: ...{r['msg_excerpt'][-220:]}")
    print()
