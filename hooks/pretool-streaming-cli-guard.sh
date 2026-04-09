#!/usr/bin/env bash
# pretool-streaming-cli-guard.sh — block streaming CLI commands without timeout wrapper.
# Streaming commands (modal app logs, tail -f, docker logs -f) without timeout
# leak exec processes and burn context on unchanging output.
# Evidence: 200+ exec-limit warnings in Codex session 019d6d86.

trap 'exit 0' ERR
INPUT=$(cat)

CMD=$(echo "$INPUT" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
print(data.get("tool_input", {}).get("command", ""))
' 2>/dev/null) || exit 0

[ -z "$CMD" ] && exit 0

# Streaming commands that need timeout wrapping
if echo "$CMD" | grep -qE '(modal app logs|modal container exec|tail -f|docker logs -f)'; then
    if ! echo "$CMD" | grep -qE '(timeout |gtimeout |--timeout)'; then
        echo "WARN: Streaming command without timeout wrapper." >&2
        echo "  Add: timeout 60 $CMD" >&2
        echo "  Or: $CMD | head -100" >&2
        echo "  Streaming commands without timeout leak exec processes and burn context." >&2
        exit 2
    fi
fi

exit 0
