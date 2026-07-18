#!/usr/bin/env bash
# hook-trigger-log.sh — Log hook triggers to JSONL for ROI analysis.
# Called by decision-making hooks when they fire (warn or block).
#
# Usage: source this or call directly:
#   echo '{"hook":"search-burst","action":"block","count":8}' | ~/Projects/skills/hooks/hook-trigger-log.sh
# Or from another hook:
#   log_hook_trigger "bash-failure-loop" "warn" "5 consecutive failures"
#   log_hook_trigger "git-stash-guard" "block" "peers=2" "git stash"   # 4th arg: raw command
#
# Env: HOOK_TRIGGER_LOG (default: ~/.claude/hook-triggers.jsonl)
#
# Command fingerprinting (2026-07-18, guard-forcerate-study /
# rescue-class-surface-closure-loop — arc-agi loop/backlog.jsonl rows 906/909):
# an optional 4th positional arg (args mode) or "cmd" key (pipe mode) is
# fingerprinted into cmd_tok (coarse first token, e.g. "git"/"llmx") + cmd_fp
# (8-hex sha256 of the whitespace-normalized command) via
# hook_cmd_fingerprint.py — the RAW command is NEVER written to the log, only
# the two derived fields, and only when the command was non-empty. A row
# missing cmd_tok is either pre-enrichment or not command-shaped in the first
# place; the outcome analyzer (agent-infra scripts/hook-roi.py) treats both
# the same way — outcome=unknown, never guessed.

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${HOOK_TRIGGER_LOG:-$HOME/.claude/hook-triggers.jsonl}"

# If called with args: hook_name, action, detail, [cmd]
if [ $# -ge 2 ]; then
    HOOK_NAME="$1"
    ACTION="$2"  # warn, block, allow, remind
    DETAIL="${3:-}"
    CMD="${4:-}"
    PROJECT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
    PROJECT=$(basename "$PROJECT")
    # Read session ID from file (env var is never set by Claude Code)
    SESSION="unknown"
    for _sid_path in ".claude/current-session-id" "$HOME/.claude/current-session-id"; do
        if [ -f "$_sid_path" ]; then
            SESSION=$(cat "$_sid_path" 2>/dev/null | tr -d '[:space:]')
            [ -n "$SESSION" ] && break
            SESSION="unknown"
        fi
    done
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    # Build the record via json.dumps — a raw printf "%s" of $DETAIL injected
    # unescaped newlines/quotes and produced 800+ broken JSONL lines that crashed
    # the telemetry report. Pass fields through the environment (no shell-quoting).
    _HT_TS="$TS" _HT_HOOK="$HOOK_NAME" _HT_ACTION="$ACTION" _HT_DETAIL="$DETAIL" \
    _HT_PROJECT="$PROJECT" _HT_SESSION="$SESSION" _HT_TOOL="${CLAUDE_TOOL_NAME:-}" \
    _HT_CMD="$CMD" _HT_HOOKSDIR="$HOOK_DIR" \
    python3 -c "
import os, json, sys
rec = {
    'ts': os.environ['_HT_TS'], 'hook': os.environ['_HT_HOOK'],
    'action': os.environ['_HT_ACTION'], 'detail': os.environ['_HT_DETAIL'],
    'project': os.environ['_HT_PROJECT'], 'session': os.environ['_HT_SESSION'],
    'tool': os.environ['_HT_TOOL'],
}
cmd = os.environ.get('_HT_CMD', '')
if cmd.strip():
    sys.path.insert(0, os.environ.get('_HT_HOOKSDIR', ''))
    try:
        from hook_cmd_fingerprint import fingerprint_command
        tok, fp = fingerprint_command(cmd)
        if tok:
            rec['cmd_tok'] = tok
        if fp:
            rec['cmd_fp'] = fp
    except Exception:
        pass
print(json.dumps(rec))" >> "$LOG_FILE" 2>/dev/null
    exit 0
fi

# If called via pipe (stdin JSON). An optional "cmd" key is fingerprinted the
# same way as args-mode and then DROPPED — never persisted raw.
INPUT=$(cat)
if [ -n "$INPUT" ]; then
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    PROJECT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
    PROJECT=$(basename "$PROJECT")
    # Read session ID from file
    _SID="unknown"
    for _sp in ".claude/current-session-id" "$HOME/.claude/current-session-id"; do
        if [ -f "$_sp" ]; then
            _SID=$(cat "$_sp" 2>/dev/null | tr -d '[:space:]')
            [ -n "$_SID" ] && break
            _SID="unknown"
        fi
    done
    # Merge timestamp, project, session into the JSON
    echo "$INPUT" | _HT_HOOKSDIR="$HOOK_DIR" python3 -c "
import sys, json, os
try:
    data = json.load(sys.stdin)
    data['ts'] = '$TS'
    data['project'] = '$PROJECT'
    data['session'] = '$_SID'
    cmd = data.pop('cmd', '') or ''
    if cmd.strip():
        sys.path.insert(0, os.environ.get('_HT_HOOKSDIR', ''))
        try:
            from hook_cmd_fingerprint import fingerprint_command
            tok, fp = fingerprint_command(cmd)
            if tok:
                data['cmd_tok'] = tok
            if fp:
                data['cmd_fp'] = fp
        except Exception:
            pass
    print(json.dumps(data))
except:
    pass
" >> "$LOG_FILE" 2>/dev/null
fi
exit 0
