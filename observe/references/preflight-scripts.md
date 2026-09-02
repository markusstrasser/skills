<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Phase 0: Pre-Flight Scripts

## Environment Setup

```bash
PROJECT_ROOT="${ARGUMENTS:-$(pwd)}"
PROJECT_ROOT=$(cd "$PROJECT_ROOT" && pwd)  # resolve to absolute
PROJECT_NAME=$(basename "$PROJECT_ROOT")
UPGRADE_DIR="$PROJECT_ROOT/.project-upgrade/$(date +%Y-%m-%d)"
mkdir -p "$UPGRADE_DIR"

cd "$PROJECT_ROOT"

# Fail if dirty working tree
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: Dirty working tree. Commit or stash first."
  exit 1
fi
```

## Check Prior Artifacts

```bash
ls ~/.claude/artifacts/$PROJECT_NAME/code-review-*.json 2>/dev/null
ls ~/.claude/artifacts/$PROJECT_NAME/model-review-*.json 2>/dev/null
```

If recent artifacts exist (within last 7 days), read them and incorporate their findings into Phase 2 triage. Don't re-scan for issues already identified by code-review or model-review.

## Backlog Gate

```bash
# Check existing finding volume
FINDING_COUNT=0
if [ -f "$PROJECT_ROOT/scripts/fix_backlog.py" ]; then
  FINDING_COUNT=$(cd "$PROJECT_ROOT" && uv run python3 scripts/fix_backlog.py count 2>/dev/null || echo 0)
elif [ -d "$PROJECT_ROOT/.project-upgrade" ]; then
  FINDING_COUNT=$(find "$PROJECT_ROOT/.project-upgrade" -name "*.json" -exec cat {} + 2>/dev/null | python3 -c "import sys,json; data=sys.stdin.read(); print(sum(len(json.loads(x)) if isinstance(json.loads(x),list) else 0 for x in data.split('}][{')))" 2>/dev/null || echo 0)
fi
```

If more than 50 unfixed findings exist, **do not generate more.** Instead:
1. Print: "Warning: Backlog has $FINDING_COUNT unfixed findings. Fix before auditing."
2. Show the top 10 by severity: `uv run python3 scripts/fix_backlog.py next 10` (if available)
3. Offer to switch to fix mode: pick the top finding and implement the fix
4. Only proceed with new audit if user explicitly overrides with `--force`

## Language & Tooling Detection

```bash
# Language detection
if [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
  LANG="python"
  RUNNER="uv run python3"
elif [ -f "package.json" ]; then
  LANG="javascript"
  RUNNER="npx"
elif [ -f "Cargo.toml" ]; then
  LANG="rust"
  RUNNER="cargo"
else
  LANG="generic"
  RUNNER=""
fi

# Test runner detection
if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ] && grep -q "pytest" pyproject.toml 2>/dev/null; then
  TEST_CMD="uv run pytest -x -q 2>&1 | tail -20"
elif [ -f "package.json" ] && grep -q '"test"' package.json; then
  TEST_CMD="npm test 2>&1 | tail -20"
elif [ -f "Cargo.toml" ]; then
  TEST_CMD="cargo test 2>&1 | tail -20"
else
  TEST_CMD=""
fi
```

## Baseline Snapshot

```bash
# Line counts
find . \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.rs" \) \
  -not -path "*/node_modules/*" -not -path "*/__pycache__/*" -not -path "*/.git/*" | \
  xargs wc -l 2>/dev/null | tail -1 > "$UPGRADE_DIR/baseline-loc.txt"

# Import check (Python)
if [ "$LANG" = "python" ]; then
  find . -name "*.py" -not -path "./.git/*" -not -path "./__pycache__/*" | while read -r f; do
    uv run python3 -c "import ast; ast.parse(open('$f', encoding='utf-8').read())" 2>&1 || echo "SYNTAX_ERROR: $f"
  done > "$UPGRADE_DIR/baseline-syntax.txt" 2>&1
fi

# Test results (if tests exist) — capture exit code explicitly
if [ -n "$TEST_CMD" ]; then
  set +e
  eval "$TEST_CMD" > "$UPGRADE_DIR/baseline-tests.txt" 2>&1
  echo "EXIT_CODE=$?" >> "$UPGRADE_DIR/baseline-tests.txt"
  set -e
fi

# Lint results (Python)
if [ "$LANG" = "python" ] && command -v ruff &>/dev/null; then
  ruff check . --select E,F,W --statistics 2>&1 | tail -20 > "$UPGRADE_DIR/baseline-lint.txt"
fi
```
