#!/bin/bash
# lib_hook_identity.sh — who is calling this hook. Source it, then: hook_identity "$INPUT"
#
# Claude Code passes identity in the hook ENVELOPE, not the hook's environment. Probed
# 2026-09-21 (pretool-universal-dispatch.py probe_envelope): a subagent's tool calls carry
# .agent_id/.agent_type and the main loop's do not; every call carries .session_id. The hook
# process environment has CLAUDE_CODE_SESSION_ID but neither CLAUDE_AGENT_ID nor
# CLAUDE_SESSION_ID (only the Bash tool's shell gets CLAUDE_SESSION_ID), and in-process
# subagents share the CLI's PID. Hooks that tested those variables or keyed state on $PPID
# alone saw every sibling agent as one caller, and every session as "default".
#
# Sets:
#   HOOK_AGENT_ID    filename-safe agent id; "" for the main loop
#   HOOK_SESSION_ID  filename-safe session id; "" if unknown
#   HOOK_OWNER       "<agent>-<ppid>" or "<ppid>": suffix for per-caller state files. The PID
#                    stays last because reap_stale_trackers.py reads the owner PID from there.
# Python twin: lib_hook_identity.py. test_hook_identity.py holds the two together.

hook_identity() {
    local raw
    raw=$(printf '%s' "$1" | jq -r '[(.agent_id // "" | tostring), (.session_id // "" | tostring)] | join("|")' 2>/dev/null) || raw=""
    # "|" rather than a tab: read collapses leading whitespace separators, which would move the
    # session id into the agent slot for every main-loop call.
    IFS='|' read -r HOOK_AGENT_ID HOOK_SESSION_ID <<< "$raw"
    HOOK_AGENT_ID=${HOOK_AGENT_ID//[^A-Za-z0-9]/}
    HOOK_AGENT_ID=${HOOK_AGENT_ID:0:32}
    [ -z "$HOOK_SESSION_ID" ] && HOOK_SESSION_ID="${CLAUDE_CODE_SESSION_ID:-${CLAUDE_SESSION_ID:-}}"
    HOOK_SESSION_ID=${HOOK_SESSION_ID//[^A-Za-z0-9-]/}
    HOOK_SESSION_ID=${HOOK_SESSION_ID:0:64}
    HOOK_OWNER="${HOOK_AGENT_ID:+$HOOK_AGENT_ID-}$PPID"
}
