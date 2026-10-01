#!/usr/bin/env bash
# posttool-codebase-map.sh — background refresh of agent codebase maps on script edits.
# Zero-API, fail-open. Bypass: SKIP_CODEBASE_MAP_REFRESH=1

set -uo pipefail
[ "${SKIP_CODEBASE_MAP_REFRESH:-}" = "1" ] && exit 0

INPUT=$(cat)
FP=$(echo "$INPUT" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null) || exit 0
[ -n "$FP" ] || exit 0
case "$FP" in
  *.py|*/justfile) ;;
  *) exit 0 ;;
esac

AGENT_INFRA="${AGENT_INFRA_ROOT:-$HOME/Projects/agent-infra}"
SCRIPT="$AGENT_INFRA/scripts/refresh_codebase_map_on_commit.py"
[ -f "$SCRIPT" ] || exit 0

(
  # Own runtime only; background advisories must never sync the caller's venv.
  if ! env -u UV_PROJECT_ENVIRONMENT -u VIRTUAL_ENV uv run --no-sync --directory "$AGENT_INFRA" python3 "$SCRIPT" --touched "$FP" >/dev/null 2>&1; then
    echo "[posttool-codebase-map] refresh failed (non-blocking)" >&2
  fi
) &
exit 0
