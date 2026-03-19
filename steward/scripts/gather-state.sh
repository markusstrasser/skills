#!/usr/bin/env bash
# Gather live state for steward tick. Target: <5s.
# Called via !` in SKILL.md — output replaces the placeholder before Claude sees it.
set -e

echo "=== ORCHESTRATOR ==="
cd ~/Projects/meta
uv run python3 scripts/orchestrator.py status 2>/dev/null || echo "(unavailable)"

echo ""
echo "=== RECENT SESSIONS ==="
if [[ -f ~/.claude/session-receipts.jsonl ]]; then
    tail -12 ~/.claude/session-receipts.jsonl | python3 -c '
import sys, json
for line in sys.stdin:
    try:
        r = json.loads(line.strip())
        cost = "${:.2f}".format(r.get("cost_usd", 0))
        nc = len(r.get("commits", []))
        cs = "; ".join(r.get("commits", [])[:2])
        ts = r.get("ts", "?")[:16]
        proj = r.get("project", "?")
        model = r.get("model", "?")
        reason = r.get("reason", "?")
        print("  {} | {:10} | {:8} | {:>6} | {}c | {:12} | {}".format(ts, proj, model, cost, nc, reason, cs))
    except Exception:
        pass
'
else
    echo "(no receipts)"
fi

echo ""
echo "=== STEWARD LOG (my recent actions) ==="
tail -5 ~/.claude/steward-actions.jsonl 2>/dev/null || echo "(none yet)"

echo ""
echo "=== UNIMPLEMENTED FINDINGS ==="
grep -B2 'Status:\*\* \[ \]' ~/Projects/meta/improvement-log.md 2>/dev/null | grep -E '(###|\*\*Status)' | head -10 || echo "(all clear)"

echo ""
echo "=== FINDING TRIAGE ==="
cd ~/Projects/meta
uv run python3 scripts/finding-triage.py status 2>/dev/null || echo "(unavailable)"

echo ""
echo "=== GIT (last 2h) ==="
for proj in meta intel selve genomics; do
    dir=~/Projects/$proj
    [[ -d "$dir/.git" ]] || continue
    out=$(cd "$dir" && git log --oneline --since="2 hours ago" 2>/dev/null | head -3)
    [[ -n "$out" ]] && echo "  $proj:" && echo "$out" | sed 's/^/    /'
done
