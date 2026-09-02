<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Phase 1: Codebase Dump

## Diff-Aware Mode (recommended for repeat runs)

If a `.project-upgrade/last-baseline.sha` file exists, only analyze changed files + their import graph. 10x cheaper, can run daily.

```bash
LAST_SHA_FILE="$PROJECT_ROOT/.project-upgrade/last-baseline.sha"
DIFF_MODE="false"

if [ -f "$LAST_SHA_FILE" ]; then
  LAST_SHA=$(cat "$LAST_SHA_FILE")
  if git rev-parse --verify "$LAST_SHA" >/dev/null 2>&1; then
    CHANGED_FILES=$(git diff --name-only "$LAST_SHA" HEAD -- '*.py' '*.js' '*.ts' '*.rs' '*.go' '*.sh')
    if [ -n "$CHANGED_FILES" ]; then
      DIFF_MODE="true"
      echo "$CHANGED_FILES" > "$UPGRADE_DIR/changed-files.txt"
      echo "Diff-aware mode: $(echo "$CHANGED_FILES" | wc -l | tr -d ' ') files changed since $(echo $LAST_SHA | head -c 8)"
    else
      echo "No files changed since last run. Nothing to analyze."
      exit 0
    fi
  fi
fi
```

## Full Dump (first run or when --full flag is passed)

Bundle the codebase into a structured document for Gemini.

```bash
if [ "$DIFF_MODE" = "true" ]; then
  # Dump only changed files + their direct importers
  uv run python3 "$(dirname "$0")/scripts/dump_codebase.py" \
    "$PROJECT_ROOT" \
    --output "$UPGRADE_DIR/codebase.md" \
    --max-tokens 400000 \
    --files-from "$UPGRADE_DIR/changed-files.txt"
else
  uv run python3 "$(dirname "$0")/scripts/dump_codebase.py" \
    "$PROJECT_ROOT" \
    --output "$UPGRADE_DIR/codebase.md" \
    --max-tokens 400000
fi
```

## Inline Fallback

If `dump_codebase.py` doesn't exist or fails:

```bash
{
  echo "# Codebase: $PROJECT_NAME"
  echo ""

  # Project config files first
  for f in CLAUDE.md pyproject.toml Cargo.toml package.json Makefile; do
    [ -f "$f" ] && echo -e "\n## $f\n\`\`\`\n$(cat "$f")\n\`\`\`"
  done

  # All source files, sorted by modification time (newest first)
  find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.rs" -o -name "*.go" -o -name "*.sh" \) \
    -not -path "./.git/*" \
    -not -path "./node_modules/*" \
    -not -path "./__pycache__/*" \
    -not -path "./.venv/*" \
    -not -path "./target/*" \
    -not -path "./.project-upgrade/*" \
    -printf '%T@ %p\n' 2>/dev/null | sort -rn | cut -d' ' -f2- | while read filepath; do
      echo -e "\n## $filepath"
      echo '```'
      cat "$filepath"
      echo '```'
  done
} > "$UPGRADE_DIR/codebase.md"
```

## Token Budget Check

```bash
TOKEN_EST=$(wc -c < "$UPGRADE_DIR/codebase.md" | awk '{print int($1/4)}')
echo "Estimated tokens: $TOKEN_EST"
if [ "$TOKEN_EST" -gt 500000 ]; then
  echo "WARNING: >500K tokens. Consider splitting or truncating large files."
fi
```
