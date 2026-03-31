#!/usr/bin/env bash
# permission-log.sh — Log permission decisions for autonomy measurement.
# Deploy on PermissionRequest (denominator) and PermissionDenied (numerator).
# Logging-only, non-blocking. Always exit 0.
#
# Env: HOOK_EVENT — set by settings.json env field ("request" or "denied")

trap 'exit 0' ERR

INPUT=$(cat)
LOG="$HOME/.claude/permission-decisions.jsonl"
EVENT="${HOOK_EVENT:-unknown}"

echo "$INPUT" | python3 -c "
import sys, json, datetime
data = json.load(sys.stdin)
out = {
    'ts': datetime.datetime.now().isoformat(),
    'event': '$EVENT',
    'tool': data.get('tool_name', ''),
}
# Include tool input summary (command or file_path, not full content)
ti = data.get('tool_input', {})
if isinstance(ti, dict):
    if 'command' in ti:
        out['command'] = ti['command'][:200]
    if 'file_path' in ti:
        out['file_path'] = ti['file_path']
    if 'pattern' in ti:
        out['pattern'] = ti['pattern'][:100]
# Include denial reason if present (PermissionDenied events)
if 'reason' in data:
    out['reason'] = data['reason'][:200]
print(json.dumps(out))
" >> "$LOG" 2>/dev/null

exit 0
