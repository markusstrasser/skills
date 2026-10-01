#!/usr/bin/env bash
# pre-commit-codebase-map.sh — keep agent-facing .claude/rules/codebase-map.md fresh.
#
# Zero-API (repo-summary --no-llm + codebase-map.py). Runs only when staged paths
# touch a repo's mapped source dirs (config/codebase-map-repos.json). Outputs are
# gitignored — nothing to stage. Fail-open on errors so a broken refresh never
# blocks an otherwise-valid commit.
#
# Bypass: SKIP_CODEBASE_MAP_REFRESH=1

set -uo pipefail
[ "${SKIP_CODEBASE_MAP_REFRESH:-}" = "1" ] && exit 0

AGENT_INFRA="${AGENT_INFRA_ROOT:-$HOME/Projects/agent-infra}"
SCRIPT="$AGENT_INFRA/scripts/refresh_codebase_map_on_commit.py"
[ -f "$SCRIPT" ] || exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$REPO_ROOT" || exit 0

# A caller may select its own shared venv. This advisory must neither target
# that environment nor install/remove packages beneath concurrent processes.
if ! env -u UV_PROJECT_ENVIRONMENT -u VIRTUAL_ENV uv run --no-sync --directory "$AGENT_INFRA" python3 "$SCRIPT" --repo-root "$REPO_ROOT"; then
  echo "[pre-commit-codebase-map] refresh failed (non-blocking)" >&2
fi
exit 0
