#!/usr/bin/env bash
# pretool-goal-drift.sh — Detect goal-keyword drift in Write|Edit content.
# PreToolUse hook on Write|Edit. Advisory only (additionalContext).
# Reads <!-- goal-keywords: k1, k2, ... --> from GOALS.md, caches per session.
# Warns if content references goal-like terms not in the keyword set.

trap 'exit 0' ERR
INPUT=$(cat)
CACHE="/tmp/claude-goals-$PPID"

# --- Build keyword cache on first invocation ---
if [ ! -f "$CACHE" ]; then
    PROJ="${CLAUDE_PROJECT_DIR:-$(pwd)}"
    GOALS=""
    for f in "$PROJ/GOALS.md" "$PROJ/docs/GOALS.md"; do
        [ -f "$f" ] && GOALS="$f" && break
    done
    [ -z "$GOALS" ] && exit 0
    python3 -c "
import re, pathlib, sys
text = pathlib.Path(sys.argv[1]).read_text()
kw = set()
for m in re.findall(r'<!--\s*goal-keywords:\s*(.+?)\s*-->', text):
    for k in m.split(','):
        k = k.strip().lower()
        if k: kw.add(k)
if not kw: sys.exit(0)
print('\n'.join(sorted(kw)))
" "$GOALS" > "$CACHE" 2>/dev/null
    [ ! -s "$CACHE" ] && rm -f "$CACHE" && exit 0
fi

KEYWORDS=$(< "$CACHE")
[ -z "$KEYWORDS" ] && exit 0

# --- Check content for drift ---
DRIFTED=$(echo "$INPUT" | KW="$KEYWORDS" python3 -c "
import sys, json, re, os
try:
    ti = json.load(sys.stdin)['tool_input']
    content = ti.get('content', '') or ti.get('new_string', '')
except: sys.exit(0)
if not content: sys.exit(0)
keywords = set(os.environ['KW'].strip().splitlines())
candidates = set()
for tok in re.findall(r'\b[A-Za-z][\w-]*(?:-\d+)?\b', content):
    low = tok.lower()
    if low in keywords: continue
    for kw in keywords:
        root = re.split(r'[-_\d]+', kw)[0]
        if len(root) >= 3 and root in low:
            candidates.add(tok)
            break
if candidates: print(', '.join(sorted(candidates)[:5]))
" 2>/dev/null)

[ -z "$DRIFTED" ] && exit 0

~/Projects/skills/hooks/hook-trigger-log.sh "goal-drift" "warn" "${DRIFTED:0:80}" 2>/dev/null || true
KW_DISPLAY=$(echo "$KEYWORDS" | tr '\n' ', ' | sed 's/,$//')
printf '{"additionalContext": "GOAL-DRIFT WARNING: Content references [%s] which may be outside project scope. GOALS.md keywords: [%s]. Verify this is intentional."}\n' "$DRIFTED" "$KW_DISPLAY"
exit 0
