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
OVERVIEW_MODEL="${OVERVIEW_MODEL:-gemini-2.5-flash}"
OVERVIEW_OUTPUT_DIR="${OVERVIEW_OUTPUT_DIR:-.claude/overviews}"
OVERVIEW_PROMPT_DIR="${OVERVIEW_PROMPT_DIR:-.claude/overview-prompts}"
OVERVIEW_EXCLUDE="${OVERVIEW_EXCLUDE:-}"

# --- Parse arguments ---
TYPE=""
AUTO=false
DRY_RUN=false
PROJECT_ROOT=""

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
    -h|--help)
      echo "Usage: generate-overview.sh [--type TYPE|--auto] [--dry-run] [--project-root DIR]"
      echo "  --type TYPE        Generate single overview (source, tooling, structure, etc.)"
      echo "  --auto             Generate all types from OVERVIEW_TYPES config"
      echo "  --dry-run          Log what would happen without generating"
      echo "  --project-root DIR Project root (default: git root or cwd)"
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# --- Resolve project root ---
if [[ -z "$PROJECT_ROOT" ]]; then
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
fi
cd "$PROJECT_ROOT"

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
OVERVIEW_MODEL="${OVERVIEW_MODEL:-gemini-2.5-flash}"
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
  local prompt_file="$PROJECT_ROOT/$OVERVIEW_PROMPT_DIR/${type}.md"
  local output_dir="$PROJECT_ROOT/$OVERVIEW_OUTPUT_DIR"
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

  local temp_content temp_prompt
  temp_content=$(mktemp /tmp/overview-content-XXXXXX.txt)
  temp_prompt=$(mktemp /tmp/overview-prompt-XXXXXX.txt)

  # Step 1: Extract content with repomix
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

  local repomix_args=(--copy --output /dev/null --include "$include_pattern")
  if [[ -n "$OVERVIEW_EXCLUDE" ]]; then
    repomix_args+=(--ignore "$OVERVIEW_EXCLUDE")
  fi

  repomix "${repomix_args[@]}" >/dev/null 2>&1
  pbpaste > "$temp_content"

  # Step 2: Build prompt
  {
    echo '<instructions>'
    cat "$prompt_file"
    echo '</instructions>'
    echo ''
    echo '<codebase>'
    cat "$temp_content"
    echo '</codebase>'
  } > "$temp_prompt"

  # Step 3: Token estimate
  local prompt_size prompt_tokens
  prompt_size=$(wc -c < "$temp_prompt")
  prompt_tokens=$((prompt_size / 4))

  echo "[$type] Generating (~${prompt_tokens} tokens, model: $OVERVIEW_MODEL)..."

  # Step 4: Generate via llmx
  cat "$temp_prompt" | llmx chat -m "$OVERVIEW_MODEL" > "$output_file" 2>&1

  # Cleanup
  rm -f "$temp_content" "$temp_prompt"

  echo "[$type] Done → $output_file"
}

# --- Main ---
if ! $DRY_RUN; then
  check_deps
fi

if $AUTO; then
  # Generate all configured types in parallel
  IFS=',' read -ra TYPES <<< "$OVERVIEW_TYPES"
  pids=()
  type_names=()

  for t in "${TYPES[@]}"; do
    t=$(echo "$t" | xargs)
    generate_one "$t" &
    pids+=($!)
    type_names+=("$t")
  done

  # Wait and report
  failures=0
  for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}"; then
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
