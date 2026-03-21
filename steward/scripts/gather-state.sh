#!/usr/bin/env bash
# Gather live state for steward tick. Target: <5s.
# Called via !` in SKILL.md — output replaces the placeholder before Claude sees it.
# Noop detection: hashes key signals and skips full output if unchanged.
set -e

HASH_FILE=~/.claude/steward-state-hash.txt

# Collect hashable signals (fast — no uv run)
ORCH_HASH=$(sqlite3 ~/.claude/orchestrator.db "SELECT count(*),group_concat(status) FROM tasks WHERE status IN ('failed','blocked','pending') ORDER BY id" 2>/dev/null || echo "na")
RECEIPT_HASH=$(tail -3 ~/.claude/session-receipts.jsonl 2>/dev/null | md5 || echo "na")
FINDING_HASH=$(grep -c 'Status:\*\* \[ \]' ~/Projects/meta/improvement-log.md 2>/dev/null || echo "0")
GIT_HASH=$(for p in meta intel selve genomics; do cd ~/Projects/$p 2>/dev/null && git log --oneline -1 2>/dev/null; done | md5 || echo "na")
CURRENT_HASH="${ORCH_HASH}|${RECEIPT_HASH}|${FINDING_HASH}|${GIT_HASH}"

PREV_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
echo "$CURRENT_HASH" > "$HASH_FILE"

if [[ "$CURRENT_HASH" = "$PREV_HASH" ]]; then
    echo "NO STATE CHANGE since last tick. Nothing to do."
    # Log noop
    echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%S)\",\"action\":\"noop\",\"target\":\"state-unchanged\",\"result\":\"ok\",\"detail\":\"hash match\"}" >> ~/.claude/steward-actions.jsonl 2>/dev/null
    exit 0
fi

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
