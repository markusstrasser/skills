#!/usr/bin/env bash
# Preserve the configured hook entrypoint; command classification has one Python owner.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$HOOK_DIR/pretool_streaming_cli_guard.py"
result=$?
# Shared PreToolUse contract: only an intentional denial propagates.
if [ "$result" = 2 ]; then exit 2; fi
exit 0
