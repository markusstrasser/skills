#!/usr/bin/env bash
# overview-staleness-cron.sh — Daily check for stale overviews.
# Run via launchd. For each opted-in project in live mode, regenerates
# overviews if marker is >7 days old and there are changes since.

set -euo pipefail

GENERATE_SCRIPT="$HOME/Projects/skills/hooks/generate-overview.sh"
MAX_AGE_DAYS=7
# Surface failures instead of swallowing them. The old `2>/dev/null || true`
# discarded BOTH the error text and the exit code, which is how a generator
# payload-overflow froze intel's overview for a month with no signal (2026-06-01).
LOG="$HOME/.cache/overview-staleness-cron.log"
mkdir -p "$(dirname "$LOG")"
regen() {  # regen <project_dir> — log stderr + a failure marker; never abort the loop
  local pd="$1"
  if ! "$GENERATE_SCRIPT" --auto --project-root "$pd" >>"$LOG" 2>&1; then
    echo "[$(date '+%Y-%m-%dT%H:%M:%S')] OVERVIEW REGEN FAILED for $pd (see above)" >>"$LOG"
  fi
}

# Projects to check (add more as they opt in)
PROJECTS=(
  "$HOME/Projects/intel"
  "$HOME/Projects/phenome"
  "$HOME/Projects/genomics"
  "$HOME/Projects/agent-infra"
)

for project_dir in "${PROJECTS[@]}"; do
  conf="$project_dir/.claude/overview.conf"
  [[ -f "$conf" ]] || continue

  # Read mode from config
  mode=$(grep -E '^OVERVIEW_MODE=' "$conf" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"' | xargs)
  [[ "$mode" == "live" ]] || continue

  mapfile -t configured_types < <(grep -E '^OVERVIEW_TYPES=' "$conf" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"' | tr ',' '\n' | xargs -n1)
  if [[ ${#configured_types[@]} -eq 0 ]]; then
    continue
  fi

  marker=""
  for overview_type in "${configured_types[@]}"; do
    candidate="$project_dir/.claude/overview-marker-${overview_type}"
    if [[ -f "$candidate" ]]; then
      marker="$candidate"
      break
    fi
  done

  if [[ -z "$marker" ]]; then
    cd "$project_dir"
    regen "$project_dir"
    continue
  fi

  # Check marker age
  if [[ "$(uname)" == "Darwin" ]]; then
    marker_mtime=$(stat -f %m "$marker")
  else
    marker_mtime=$(stat -c %Y "$marker")
  fi
  now=$(date +%s)
  age_days=$(( (now - marker_mtime) / 86400 ))

  [[ $age_days -ge $MAX_AGE_DAYS ]] || continue

  # Check if there are changes since marker
  marker_hash=$(cat "$marker")
  cd "$project_dir"
  if ! git diff --quiet "$marker_hash"..HEAD 2>/dev/null; then
    regen "$project_dir"
  fi
done
