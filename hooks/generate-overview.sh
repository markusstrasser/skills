#!/usr/bin/env bash
# generate-overview.sh — Shared overview generator: repomix → prompt → llmx/Gemini → markdown
# Used by sessionend-overview-trigger.sh and manual invocation.
#
# Config: reads .claude/overview.conf from project root (or env vars).
# Prompts: reads from $OVERVIEW_PROMPT_DIR/<type>.md
#
# Usage:
#   generate-overview.sh --type source       # Single overview type
#   generate-overview.sh --auto              # All configured types in parallel
#   generate-overview.sh --dry-run --auto    # Log what would happen, don't generate

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Defaults (overridden by .claude/overview.conf or env) ---
OVERVIEW_TYPES="${OVERVIEW_TYPES:-source}"
OVERVIEW_MODEL="${OVERVIEW_MODEL:-gemini-3-flash-preview}"
OVERVIEW_OUTPUT_DIR="${OVERVIEW_OUTPUT_DIR:-.claude/overviews}"
OVERVIEW_PROMPT_DIR="${OVERVIEW_PROMPT_DIR:-.claude/overview-prompts}"
OVERVIEW_EXCLUDE="${OVERVIEW_EXCLUDE:-}"

# --- Parse arguments ---
TYPE=""
AUTO=false
DRY_RUN=false
PROJECT_ROOT=""
COMMIT_HASH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)
      TYPE="$2"; shift 2 ;;
    --auto)
      AUTO=true; shift ;;
    --dry-run)
      DRY_RUN=true; shift ;;
    --project-root)
      PROJECT_ROOT="$2"; shift 2 ;;
    --commit-hash)
      COMMIT_HASH="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: generate-overview.sh [--type TYPE|--auto] [--dry-run] [--project-root DIR] [--commit-hash SHA]"
      echo "  --type TYPE        Generate single overview (source, tooling, structure, etc.)"
      echo "  --auto             Generate all types from OVERVIEW_TYPES config"
      echo "  --dry-run          Log what would happen without generating"
      echo "  --project-root DIR Project root (default: git root or cwd)"
      echo "  --commit-hash SHA  Commit hash for marker (default: HEAD at execution time)"
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# --- Resolve project root ---
if [[ -z "$PROJECT_ROOT" ]]; then
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
fi
cd "$PROJECT_ROOT"

# --- Resolve commit hash (for marker writes) ---
if [[ -z "$COMMIT_HASH" ]]; then
  COMMIT_HASH=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
fi

# --- Load config ---
CONF_FILE="$PROJECT_ROOT/.claude/overview.conf"
if [[ -f "$CONF_FILE" ]]; then
  # Source as shell vars (simple key=value, no export needed)
  while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ "$key" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$key" ]] && continue
    key=$(echo "$key" | xargs)  # trim whitespace
    value=$(echo "$value" | xargs | sed 's/^"//;s/"$//')  # trim + unquote
    export "$key=$value"
  done < "$CONF_FILE"
fi

# Re-read after config load (env vars may have been set)
OVERVIEW_TYPES="${OVERVIEW_TYPES:-source}"
OVERVIEW_MODEL="${OVERVIEW_MODEL:-gemini-3-flash-preview}"
OVERVIEW_OUTPUT_DIR="${OVERVIEW_OUTPUT_DIR:-.claude/overviews}"
OVERVIEW_PROMPT_DIR="${OVERVIEW_PROMPT_DIR:-.claude/overview-prompts}"
OVERVIEW_EXCLUDE="${OVERVIEW_EXCLUDE:-}"

# --- Check dependencies ---
check_deps() {
  local missing=()
  command -v repomix &>/dev/null || missing+=("repomix")
  command -v llmx &>/dev/null || missing+=("llmx")
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Missing dependencies: ${missing[*]}" >&2
    exit 1
  fi
}

# --- Generate a single overview ---
generate_one() {
  local type="$1"

  # Support absolute paths (shared prompts) and relative paths (project-local)
  local prompt_file output_dir
  if [[ "$OVERVIEW_PROMPT_DIR" = /* ]]; then
    prompt_file="$OVERVIEW_PROMPT_DIR/${type}.md"
  else
    prompt_file="$PROJECT_ROOT/$OVERVIEW_PROMPT_DIR/${type}.md"
  fi
  if [[ "$OVERVIEW_OUTPUT_DIR" = /* ]]; then
    output_dir="$OVERVIEW_OUTPUT_DIR"
  else
    output_dir="$PROJECT_ROOT/$OVERVIEW_OUTPUT_DIR"
  fi
  local output_file="$output_dir/${type}-overview.md"

  # Validate prompt exists
  if [[ ! -f "$prompt_file" ]]; then
    echo "ERROR: Prompt template not found: $prompt_file" >&2
    return 1
  fi

  # Read type-specific dirs from config
  local dirs_var="OVERVIEW_$(echo "$type" | tr '[:lower:]' '[:upper:]')_DIRS"
  local dirs="${!dirs_var:-}"
  if [[ -z "$dirs" ]]; then
    echo "ERROR: No directories configured for type '$type' (set $dirs_var)" >&2
    return 1
  fi

  if $DRY_RUN; then
    echo "[dry-run] Would generate: $type"
    echo "  prompt: $prompt_file"
    echo "  dirs: $dirs"
    echo "  output: $output_file"
    echo "  model: $OVERVIEW_MODEL"
    return 0
  fi

  mkdir -p "$output_dir"

  local temp_prompt
  temp_prompt=$(mktemp /tmp/overview-prompt-$$-${type}-XXXXXX.txt)

  # Step 1: Extract content with repomix (--stdout avoids clipboard races)
  local include_pattern=""
  IFS=',' read -ra DIR_ARRAY <<< "$dirs"
  for d in "${DIR_ARRAY[@]}"; do
    d=$(echo "$d" | xargs)  # trim
    if [[ -n "$include_pattern" ]]; then
      include_pattern="${include_pattern},${d}**"
    else
      include_pattern="${d}**"
    fi
  done

  local repomix_args=(--stdout --include "$include_pattern")
  # Some projects blanket-gitignore .claude/ — opt in via OVERVIEW_NO_GITIGNORE=true
  if [[ "${OVERVIEW_NO_GITIGNORE:-}" == "true" ]]; then
    repomix_args+=(--no-gitignore)
  fi
  if [[ -n "$OVERVIEW_EXCLUDE" ]]; then
    repomix_args+=(--ignore "$OVERVIEW_EXCLUDE")
  fi

  # Step 2: Build prompt (instructions + repomix output)
  {
    echo '<instructions>'
    cat "$prompt_file"
    echo '</instructions>'
    echo ''
    echo '<codebase>'
    repomix "${repomix_args[@]}" 2>/dev/null
    echo '</codebase>'
  } > "$temp_prompt"

  # Step 3: Token estimate
  local prompt_size prompt_tokens
  prompt_size=$(wc -c < "$temp_prompt")
  prompt_tokens=$((prompt_size / 4))

  echo "[$type] Generating (~${prompt_tokens} tokens, model: $OVERVIEW_MODEL)..."

  # Step 4: Check token estimate against model limits
  if [[ $prompt_tokens -gt 900000 ]]; then
    echo "[$type] ERROR: prompt (~${prompt_tokens} tokens) exceeds safe limit for $OVERVIEW_MODEL. Tighten OVERVIEW_EXCLUDE or dirs." >&2
    rm -f "$temp_prompt"
    return 1
  fi

  # Step 5: Generate via llmx (atomic write — temp file, mv on success)
  local llmx_stderr llmx_output
  llmx_stderr=$(mktemp /tmp/overview-llmx-stderr-XXXXXX)
  llmx_output=$(mktemp "${output_dir}/.overview-tmp-${type}-XXXXXX")

  # Disable errexit to capture exit code (set -e would skip cleanup on failure)
  set +e
  cat "$temp_prompt" | timeout 300 llmx chat -m "$OVERVIEW_MODEL" 2>"$llmx_stderr" > "$llmx_output"
  local llmx_exit=$?
  set -e

  # Cleanup prompt (no longer needed)
  rm -f "$temp_prompt"

  # Check for failure: non-zero exit or empty output
  if [[ $llmx_exit -ne 0 ]] || [[ ! -s "$llmx_output" ]]; then
    echo "[$type] ERROR: llmx failed (exit=$llmx_exit). stderr:" >&2
    cat "$llmx_stderr" >&2
    rm -f "$llmx_stderr" "$llmx_output"
    return 1
  fi
  rm -f "$llmx_stderr"

  # Step 6: Prepend freshness metadata to temp output, then atomic mv
  local git_sha gen_ts meta_line
  git_sha=$(echo "$COMMIT_HASH" | head -c 7)
  gen_ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  meta_line="<!-- Generated: ${gen_ts} | git: ${git_sha} | model: ${OVERVIEW_MODEL} -->"

  local tmp_final
  tmp_final=$(mktemp "${output_dir}/.overview-final-${type}-XXXXXX")
  { echo "$meta_line"; echo ""; cat "$llmx_output"; } > "$tmp_final"
  rm -f "$llmx_output"

  # Atomic move — old overview preserved until this succeeds
  mv "$tmp_final" "$output_file"

  # Step 7: Write per-type success marker
  echo "$COMMIT_HASH" > "$PROJECT_ROOT/.claude/overview-marker-${type}"

  echo "[$type] Done → $output_file (marker: ${COMMIT_HASH:0:7})"
}

# --- Main ---
if ! $DRY_RUN; then
  check_deps
fi

if $AUTO; then
  # Generate types with capped concurrency (avoid Gemini CLI rate limits)
  # For cross-project refresh, prefer generate-overview-batch.sh (Batch API, 50% discount)
  MAX_CONCURRENT=2
  IFS=',' read -ra TYPES <<< "$OVERVIEW_TYPES"
  pids=()
  type_names=()
  running=0

  for t in "${TYPES[@]}"; do
    t=$(echo "$t" | xargs)
    # Skip types whose per-type marker already matches target commit
    local marker_file="$PROJECT_ROOT/.claude/overview-marker-${t}"
    if [[ -f "$marker_file" ]] && [[ "$(cat "$marker_file" 2>/dev/null)" == "$COMMIT_HASH" ]]; then
      echo "[$t] Already current (marker matches ${COMMIT_HASH:0:7}), skipping"
      continue
    fi
    generate_one "$t" &
    pids+=($!)
    type_names+=("$t")
    ((running++))
    if [ "$running" -ge "$MAX_CONCURRENT" ]; then
      wait "${pids[-$MAX_CONCURRENT]}" 2>/dev/null || true
      ((running--))
    fi
  done

  # Wait for remaining
  failures=0
  for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}" 2>/dev/null; then
      echo "FAILED: ${type_names[$i]}" >&2
      ((failures++))
    fi
  done

  [[ $failures -gt 0 ]] && exit 1
  exit 0
fi

if [[ -n "$TYPE" ]]; then
  generate_one "$TYPE"
  exit 0
fi

echo "Error: specify --type TYPE or --auto" >&2
exit 1
