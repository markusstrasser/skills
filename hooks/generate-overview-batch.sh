#!/usr/bin/env bash
# generate-overview-batch.sh — Batch all project overviews into one Gemini Batch API job
#
# Runs repomix for each project×type, builds JSONL, submits via llmx batch.
# 50% cost discount vs individual calls. Results distributed to each project's output dir.
#
# Usage:
#   generate-overview-batch.sh                    # Submit and wait
#   generate-overview-batch.sh --submit-only      # Submit, print job ID, exit
#   generate-overview-batch.sh --get JOB_NAME     # Fetch results from prior job
#   generate-overview-batch.sh --dry-run          # Show what would be submitted

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_DIR="$SCRIPT_DIR/overview-prompts"
PROJECTS_DIR="$HOME/Projects"

# Projects with overview.conf
PROJECTS=(meta intel selve genomics)

# Temp workspace
WORK_DIR=$(mktemp -d /tmp/overview-batch-XXXXXX)
JSONL_FILE="$WORK_DIR/batch-input.jsonl"
MANIFEST="$WORK_DIR/manifest.json"

# --- Parse arguments ---
MODE="submit-wait"  # submit-wait | submit-only | get | dry-run
JOB_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --submit-only) MODE="submit-only"; shift ;;
    --get) MODE="get"; JOB_NAME="$2"; shift 2 ;;
    --dry-run) MODE="dry-run"; shift ;;
    -h|--help)
      echo "Usage: generate-overview-batch.sh [--submit-only|--get JOB_NAME|--dry-run]"
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# --- Parse a project's overview.conf ---
parse_conf() {
  local conf_file="$1"
  # Reset to defaults
  OVERVIEW_TYPES="source"
  OVERVIEW_MODEL="gemini-3-flash-preview"
  OVERVIEW_OUTPUT_DIR=".claude/overviews"
  OVERVIEW_PROMPT_DIR="$PROMPT_DIR"
  OVERVIEW_EXCLUDE=""
  OVERVIEW_NO_GITIGNORE=""
  OVERVIEW_SOURCE_DIRS=""
  OVERVIEW_TOOLING_DIRS=""

  if [[ -f "$conf_file" ]]; then
    while IFS='=' read -r key value; do
      [[ "$key" =~ ^[[:space:]]*# ]] && continue
      [[ -z "$key" ]] && continue
      key=$(echo "$key" | xargs)
      value=$(echo "$value" | xargs | sed 's/^"//;s/"$//')
      # Only set known variables
      case "$key" in
        OVERVIEW_TYPES|OVERVIEW_MODEL|OVERVIEW_OUTPUT_DIR|OVERVIEW_PROMPT_DIR|\
        OVERVIEW_EXCLUDE|OVERVIEW_NO_GITIGNORE|OVERVIEW_SOURCE_DIRS|OVERVIEW_TOOLING_DIRS)
          eval "$key=\"$value\""
          ;;
      esac
    done < "$conf_file"
  fi
}

# --- Run repomix and build prompt for one project×type ---
build_prompt() {
  local project="$1"
  local type="$2"
  local project_root="$PROJECTS_DIR/$project"

  # Read config
  parse_conf "$project_root/.claude/overview.conf"

  # Get type-specific dirs
  local dirs_var="OVERVIEW_$(echo "$type" | tr '[:lower:]' '[:upper:]')_DIRS"
  local dirs="${!dirs_var:-}"
  if [[ -z "$dirs" ]]; then
    echo "SKIP: $project/$type — no dirs configured ($dirs_var)" >&2
    return 1
  fi

  # Resolve prompt file
  local prompt_file
  if [[ "$OVERVIEW_PROMPT_DIR" = /* ]]; then
    prompt_file="$OVERVIEW_PROMPT_DIR/${type}.md"
  else
    prompt_file="$project_root/$OVERVIEW_PROMPT_DIR/${type}.md"
  fi
  if [[ ! -f "$prompt_file" ]]; then
    echo "SKIP: $project/$type — prompt not found: $prompt_file" >&2
    return 1
  fi

  # Build repomix include pattern
  local include_pattern=""
  IFS=',' read -ra DIR_ARRAY <<< "$dirs"
  for d in "${DIR_ARRAY[@]}"; do
    d=$(echo "$d" | xargs)
    if [[ -n "$include_pattern" ]]; then
      include_pattern="${include_pattern},${d}**"
    else
      include_pattern="${d}**"
    fi
  done

  local repomix_args=(--stdout --include "$include_pattern")
  if [[ "${OVERVIEW_NO_GITIGNORE:-}" == "true" ]]; then
    repomix_args+=(--no-gitignore)
  fi
  if [[ -n "$OVERVIEW_EXCLUDE" ]]; then
    repomix_args+=(--ignore "$OVERVIEW_EXCLUDE")
  fi

  # Run repomix from project root
  local temp_prompt="$WORK_DIR/${project}-${type}-prompt.txt"
  {
    echo '<instructions>'
    cat "$prompt_file"
    echo '</instructions>'
    echo ''
    echo '<codebase>'
    (cd "$project_root" && repomix "${repomix_args[@]}" 2>/dev/null)
    echo '</codebase>'
  } > "$temp_prompt"

  local prompt_size=$(wc -c < "$temp_prompt")
  local prompt_tokens=$((prompt_size / 4))
  echo "  $project/$type: ~${prompt_tokens} tokens" >&2

  echo "$temp_prompt"
}

# --- Build JSONL from all project×type combinations ---
build_jsonl() {
  echo "Building prompts..." >&2

  # Track manifest for result distribution: array of {key, project, type, output_path}
  echo "[" > "$MANIFEST"
  local first=true
  local count=0

  for project in "${PROJECTS[@]}"; do
    local project_root="$PROJECTS_DIR/$project"
    [[ -f "$project_root/.claude/overview.conf" ]] || continue

    parse_conf "$project_root/.claude/overview.conf"
    IFS=',' read -ra TYPES <<< "$OVERVIEW_TYPES"

    for type in "${TYPES[@]}"; do
      type=$(echo "$type" | xargs)
      local key="${project}-${type}"

      local prompt_file
      prompt_file=$(build_prompt "$project" "$type" 2>/dev/null) || continue

      # Resolve output path
      local output_dir
      if [[ "$OVERVIEW_OUTPUT_DIR" = /* ]]; then
        output_dir="$OVERVIEW_OUTPUT_DIR"
      else
        output_dir="$project_root/$OVERVIEW_OUTPUT_DIR"
      fi
      local output_path="$output_dir/${type}-overview.md"

      # Write JSONL line
      python3 -c "
import json, sys
obj = {
    'key': sys.argv[1],
    'prompt': open(sys.argv[2]).read(),
}
print(json.dumps(obj))
" "$key" "$prompt_file" >> "$JSONL_FILE"

      # Write manifest entry
      if ! $first; then echo "," >> "$MANIFEST"; fi
      first=false
      python3 -c "
import json, sys
entry = {'key': sys.argv[1], 'project': sys.argv[2], 'type': sys.argv[3], 'output': sys.argv[4]}
print(json.dumps(entry))
" "$key" "$project" "$type" "$output_path" >> "$MANIFEST"

      count=$((count + 1))
    done
  done

  echo "]" >> "$MANIFEST"
  echo "Built $count requests → $JSONL_FILE" >&2
  echo "$count"
}

# --- Distribute results to project output dirs ---
distribute_results() {
  local results_file="$1"

  # Load manifest
  local manifest_json
  manifest_json=$(cat "$MANIFEST")

  # Parse results JSONL and match to manifest by key
  python3 - "$results_file" "$MANIFEST" <<'PYEOF'
import json, sys, os

results_file = sys.argv[1]
manifest_file = sys.argv[2]

# Load manifest
with open(manifest_file) as f:
    manifest = json.load(f)
manifest_by_key = {m["key"]: m for m in manifest}

# Load results
results = []
with open(results_file) as f:
    for line in f:
        line = line.strip()
        if line:
            results.append(json.loads(line))

distributed = 0
errors = 0
for r in results:
    key = r.get("key", "")
    m = manifest_by_key.get(key)
    if not m:
        print(f"  WARN: no manifest entry for key '{key}'", file=sys.stderr)
        continue

    if "error" in r:
        print(f"  ERROR: {m['project']}/{m['type']}: {r['error']}", file=sys.stderr)
        errors += 1
        continue

    content = r.get("content", "")
    if not content:
        print(f"  WARN: empty content for {m['project']}/{m['type']}", file=sys.stderr)
        continue

    output = m["output"]
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w") as f:
        f.write(content)
    print(f"  {m['project']}/{m['type']} → {output}")
    distributed += 1

print(f"\nDistributed {distributed} overviews, {errors} errors", file=sys.stderr)
PYEOF
}

# --- Main ---

case "$MODE" in
  dry-run)
    echo "=== DRY RUN ===" >&2
    for project in "${PROJECTS[@]}"; do
      local_root="$PROJECTS_DIR/$project"
      [[ -f "$local_root/.claude/overview.conf" ]] || continue
      parse_conf "$local_root/.claude/overview.conf"
      IFS=',' read -ra TYPES <<< "$OVERVIEW_TYPES"
      for type in "${TYPES[@]}"; do
        type=$(echo "$type" | xargs)
        echo "$project/$type (model: $OVERVIEW_MODEL)"
      done
    done
    echo "Would submit as one Gemini Batch API job (50% discount)"
    ;;

  submit-only|submit-wait)
    count=$(build_jsonl)
    if [[ "$count" -eq 0 ]]; then
      echo "No overviews to generate" >&2
      exit 0
    fi

    if [[ "$MODE" == "submit-only" ]]; then
      echo "Submitting batch job..." >&2
      JOB_NAME=$(cd "$PROJECTS_DIR/llmx" && uv run llmx batch submit "$JSONL_FILE" -m gemini-3.1-pro-preview 2>/dev/null)

      # Save manifest alongside job name for later retrieval
      cp "$MANIFEST" "/tmp/overview-batch-manifest-$(echo "$JOB_NAME" | tr '/' '-').json"
      echo "Job: $JOB_NAME"
      echo "Manifest: /tmp/overview-batch-manifest-$(echo "$JOB_NAME" | tr '/' '-').json"
      echo "Use: $0 --get $JOB_NAME"
      exit 0
    fi

    # Submit with --wait (blocks until complete)
    echo "Submitting batch job and waiting..." >&2
    cd "$PROJECTS_DIR/llmx"
    RESULTS_FILE="$WORK_DIR/results.jsonl"
    # Capture job name from stderr while --wait runs
    uv run llmx batch submit "$JSONL_FILE" -m gemini-3.1-pro-preview --wait -o "$RESULTS_FILE" 2>&1 | \
      tee /dev/stderr | grep "^Submitted:" | head -1 | awk '{print $2}' > "$WORK_DIR/job_name.txt" || true

    JOB_NAME=$(cat "$WORK_DIR/job_name.txt" 2>/dev/null || echo "")
    if [[ -n "$JOB_NAME" ]]; then
      cp "$MANIFEST" "/tmp/overview-batch-manifest-$(echo "$JOB_NAME" | tr '/' '-').json"
    fi

    if [[ -s "$RESULTS_FILE" ]]; then
      echo "Distributing results..." >&2
      distribute_results "$RESULTS_FILE"
    else
      echo "Job submitted but results not ready. Check llmx batch list" >&2
      exit 1
    fi
    ;;

  get)
    if [[ -z "$JOB_NAME" ]]; then
      echo "Error: --get requires JOB_NAME" >&2
      exit 1
    fi

    # Find manifest
    MANIFEST_PATH="/tmp/overview-batch-manifest-$(echo "$JOB_NAME" | tr '/' '-').json"
    if [[ ! -f "$MANIFEST_PATH" ]]; then
      echo "Error: manifest not found at $MANIFEST_PATH" >&2
      echo "The manifest is saved when you submit. Cannot distribute without it." >&2
      exit 1
    fi
    MANIFEST="$MANIFEST_PATH"

    RESULTS_FILE="$WORK_DIR/results.jsonl"
    cd "$PROJECTS_DIR/llmx"
    uv run llmx batch get "$JOB_NAME" -o "$RESULTS_FILE" 2>/dev/null

    if [[ -s "$RESULTS_FILE" ]]; then
      echo "Distributing results..." >&2
      distribute_results "$RESULTS_FILE"
    else
      echo "No results yet or job failed. Check: llmx batch status $JOB_NAME" >&2
      exit 1
    fi
    ;;
esac

# Cleanup temp files (keep manifest in /tmp for --get)
rm -rf "$WORK_DIR"
