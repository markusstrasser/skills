#!/usr/bin/env bash
# PreToolUse:Bash — catch common llmx dispatch mistakes
# Advisory (exit 0) — warns but doesn't block

if [ "$CLAUDE_TOOL_NAME" != "Bash" ]; then exit 0; fi

INPUT="$CLAUDE_TOOL_INPUT"
CMD=$(echo "$INPUT" | jq -r '.command // empty' 2>/dev/null)
[ -z "$CMD" ] && exit 0

# Only check commands that invoke llmx
echo "$CMD" | grep -q 'llmx' || exit 0

WARNINGS=""

# 1. Shell redirect with llmx output (not context file building with cat/echo)
if echo "$CMD" | grep -qE 'llmx\s+chat.*>\s*["\$/"a-zA-Z]'; then
  WARNINGS="${WARNINGS}[llmx-guard] Shell redirect detected. Use --output/-o instead of > file — shell redirects buffer until process exit.\n"
fi

# 2. PYTHONUNBUFFERED cargo cult
if echo "$CMD" | grep -qE 'PYTHONUNBUFFERED.*llmx|llmx.*PYTHONUNBUFFERED'; then
  WARNINGS="${WARNINGS}[llmx-guard] PYTHONUNBUFFERED does nothing for llmx output capture. Use --output/-o flag instead.\n"
fi

# 3. stdbuf/script with llmx
if echo "$CMD" | grep -qE '(stdbuf|script\s+-q).*llmx'; then
  WARNINGS="${WARNINGS}[llmx-guard] stdbuf/script won't fix output buffering. Use --output/-o flag instead.\n"
fi

if [ -n "$WARNINGS" ]; then
  echo -e "$WARNINGS" >&2
fi
exit 0
