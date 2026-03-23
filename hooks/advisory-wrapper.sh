#!/bin/bash
# advisory-wrapper.sh — converts a prompt hook from blocking to advisory
# Usage in settings.json: "command": "advisory-wrapper.sh /path/to/original-hook.sh"
# The wrapped hook runs normally. If it outputs {ok: false} or {decision: block},
# this wrapper logs the advisory and outputs a pass instead.

trap 'exit 0' ERR

INPUT=$(cat)
HOOK="$1"
shift

# Run the actual hook
RESULT=$(echo "$INPUT" | "$HOOK" "$@" 2>/dev/null)

# Check if hook blocked, convert to advisory
echo "$RESULT" | python3 -c "
import sys, json, datetime, os

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)  # Not JSON — pass through as-is

blocked = d.get('ok') is False or d.get('decision', '') == 'block'
if not blocked:
    # Hook passed — forward as-is
    print(json.dumps(d))
    sys.exit(0)

# Log the advisory
ts = datetime.datetime.now().isoformat()
hook = os.path.basename('$HOOK')
msg = d.get('message', d.get('reason', d.get('additionalContext', 'blocked')))
log = os.path.expanduser('~/.claude/hook-advisory.log')
with open(log, 'a') as f:
    f.write(f'{ts} ADVISORY {hook}: {msg[:200]}\n')

# Convert to pass
d['ok'] = True
d['decision'] = 'allow'
if 'reason' in d:
    d.pop('reason')
d['additionalContext'] = f'[advisory] {msg}'
print(json.dumps(d))
" 2>/dev/null || echo "$RESULT"

exit 0
