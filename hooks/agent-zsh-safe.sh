#!/usr/bin/env zsh
# agent-zsh-safe.sh — zsh footgun fixes for agent shells (Cursor / Claude Code / Codex).
#
# Sourced twice:
#   ~/.zshenv (phase=env) — unset nomatch before .zshrc
#   ~/.zshrc end (phase=rc) — unalias short names after .zshrc defines them
#
# Fixes (30d agentlogs): nomatch on empty globs (~214), alias t/dl vs function defs (~20).

_agent_shell=0
[[ "${TERM:-}" == "dumb" ]] && _agent_shell=1
[[ "${TERM_PROGRAM:-}" == "cursor" ]] && _agent_shell=1
[[ -n "${CLAUDE_CODE:-}${CLAUDE_CODE_SESSION_ID:-}${CLAUDE_SESSION_ID:-}" ]] && _agent_shell=1

_phase="${AGENT_ZSH_SAFE_PHASE:-env}"

case "$_phase" in
  env)
    if (( _agent_shell )); then
      unsetopt nomatch 2>/dev/null
      export AGENT_SHELL=1
    else
      unset AGENT_SHELL 2>/dev/null
    fi
    ;;
  rc)
    if (( _agent_shell || ${AGENT_SHELL:-0} )); then
      unalias t dl 2>/dev/null
    fi
    ;;
esac

unset _agent_shell _phase
