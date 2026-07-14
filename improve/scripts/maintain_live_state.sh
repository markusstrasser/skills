#!/bin/bash
# Live-state snapshot + noop hash for `/improve maintain` ticks.
# Extracted from improve/SKILL.md "Live State" inline heredoc (2026-07-06, Native-First).
# Behavior-preserving: writes ~/.claude/maintain-state-hash.txt; on unchanged state prints
# a noop line, appends a noop row to $(pwd)/maintenance-actions.jsonl, and exits 0.
# Runs in the invoking project's cwd — MAINTAIN.md / maintenance-actions.jsonl are cwd-relative.

HASH_FILE="$HOME/.claude/maintain-state-hash.txt"
RECEIPT_HASH=$(tail -3 "$HOME/.claude/session-receipts.jsonl" 2>/dev/null | md5 || echo "na")
FINDING_HASH=$(grep -c "Status:\*\* \[ \]" "$HOME/Projects/agent-infra/improvement-log.md" 2>/dev/null || echo "0")
MAINTAIN_HASH=$(md5 2>/dev/null < "$(pwd)/MAINTAIN.md" || echo "na")
# shellcheck disable=SC2012  # ls -la as a cheap dir-state fingerprint, output only hashed
PROPOSAL_HASH=$(ls -la "$HOME/.claude/steward-proposals/" 2>/dev/null | md5 || echo "na")
DB_HASH=$(for db in ClinVar gnomAD PharmCAT CPIC; do
  f=$(find "$HOME/Projects/genomics/databases/" -iname "*${db}*" 2>/dev/null | head -1)
  [ -n "$f" ] && stat -f%m "$f" 2>/dev/null
done | md5 || echo "na")
GIT_HASH=$(for p in agent-infra intel genomics personal hutter substrate; do
  cd "$HOME/Projects/$p" 2>/dev/null && git log --oneline -1 2>/dev/null
done | md5 || echo "na")
CURRENT_HASH="${RECEIPT_HASH}|${FINDING_HASH}|${MAINTAIN_HASH}|${PROPOSAL_HASH}|${DB_HASH}|${GIT_HASH}"
PREV_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
echo "$CURRENT_HASH" > "$HASH_FILE"
if [ "$CURRENT_HASH" = "$PREV_HASH" ]; then
  echo "NO STATE CHANGE since last tick. Logging noop."
  echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%S)\",\"action\":\"noop\",\"target\":\"state-unchanged\",\"result\":\"ok\",\"detail\":\"hash match\"}" >> "$(pwd)/maintenance-actions.jsonl" 2>/dev/null
  exit 0
fi

echo "=== RECENT SESSIONS ==="
# shellcheck disable=SC2016  # single quotes intentional: python code, no shell expansion wanted
tail -8 "$HOME/.claude/session-receipts.jsonl" 2>/dev/null | python3 -c '
import sys, json
for line in sys.stdin:
    try:
        r = json.loads(line.strip())
        cost = "${:.2f}".format(r.get("cost_usd", 0))
        nc = len(r.get("commits", []))
        ts = r.get("ts", "?")[:16]
        proj = r.get("project", "?")
        reason = r.get("reason", "?")
        print(f"  {ts} | {proj:10} | {cost:>6} | {nc}c | {reason:12}")
    except Exception:
        pass
' || echo "(no receipts)"

echo ""
echo "=== UNIMPLEMENTED FINDINGS ==="
grep -B2 "Status:\*\* \[ \]" "$HOME/Projects/agent-infra/improvement-log.md" 2>/dev/null | grep -E "(###|\*\*Status)" | head -10 || echo "(all clear)"

echo ""
echo "=== PROPOSALS ==="
proposal_found=0
for f in "$HOME"/.claude/steward-proposals/*.md; do
  [ -e "$f" ] || continue
  echo "  $(basename "$f")"
  proposal_found=1
done
[ "$proposal_found" = 1 ] || echo "(none)"

echo ""
echo "=== DB FRESHNESS ==="
for db in ClinVar gnomAD PharmCAT CPIC; do
  f=$(find "$HOME/Projects/genomics/databases/" -iname "*${db}*" 2>/dev/null | head -1)
  if [ -n "$f" ]; then
    days=$(( ($(date +%s) - $(stat -f%m "$f" 2>/dev/null || echo 0)) / 86400 ))
    echo "  $db: ${days}d old"
  else
    echo "  $db: not found"
  fi
done

echo ""
echo "=== MAINTAIN STATE ==="
if [ -f "$(pwd)/MAINTAIN.md" ]; then
  findings=$(grep -c "^\- \*\*M[0-9]" "$(pwd)/MAINTAIN.md" 2>/dev/null)
  queued=$(grep -c "\[queued\]" "$(pwd)/MAINTAIN.md" 2>/dev/null)
  echo "  $findings findings, $queued queued"
else
  echo "  (no MAINTAIN.md -- first run, create from template)"
fi

echo ""
echo "=== RECENT ACTIONS ==="
tail -5 "$(pwd)/maintenance-actions.jsonl" 2>/dev/null || echo "(none yet)"

echo ""
echo "=== GIT (last 2h) ==="
for proj in agent-infra intel genomics personal hutter substrate; do
  dir="$HOME/Projects/$proj"
  [ -d "$dir/.git" ] || continue
  out=$(cd "$dir" && git log --oneline --since="2 hours ago" 2>/dev/null | head -3)
  # shellcheck disable=SC2001  # multi-line indent; ${var//} substitution is less readable here
  [ -n "$out" ] && echo "  $proj:" && echo "$out" | sed "s/^/    /"
done
exit 0
