#!/usr/bin/env bash
# SessionStart / PreToolUse — detect epistemic domain from project path
# Writes domain to session-scoped temp file for other scripts to read.
# Runs once per session (skips if state file already exists).
# No user-visible output — purely sets state.

STATE_FILE="/tmp/claude-epistemic-domain-${CLAUDE_SESSION_ID:-default}"

# Already routed this session — skip
[ -f "$STATE_FILE" ] && exit 0

DOMAIN="general"
PROJECT="${CLAUDE_PROJECT_DIR:-}"

# 1. Override: check for explicit domain file in project root
if [ -n "$PROJECT" ] && [ -f "$PROJECT/.claude/epistemic-domain" ]; then
  DOMAIN=$(cat "$PROJECT/.claude/epistemic-domain" | tr -d '[:space:]')
else
  # 2. Path-based detection
  case "$PROJECT" in
    /Users/alien/Projects/intel|/Users/alien/Projects/intel/*)
      DOMAIN="trading"
      ;;
    /Users/alien/Projects/genomics|/Users/alien/Projects/genomics/*|\
    /Users/alien/Projects/selve|/Users/alien/Projects/selve/*)
      DOMAIN="research"
      ;;
    /Users/alien/Projects/meta/experiments|/Users/alien/Projects/meta/experiments/*)
      DOMAIN="engineering"
      ;;
    *)
      # Check for autoresearch context (tool input or env hint)
      if [ "${CLAUDE_TOOL_INPUT:-}" != "" ]; then
        if echo "$CLAUDE_TOOL_INPUT" | grep -qiE 'autoresearch|evolutionary.search|experiment.config' 2>/dev/null; then
          DOMAIN="engineering"
        fi
      fi
      ;;
  esac
fi

# Validate domain is one of the known values
case "$DOMAIN" in
  trading|research|engineering|general) ;;
  *) DOMAIN="general" ;;
esac

echo "$DOMAIN" > "$STATE_FILE"
exit 0
