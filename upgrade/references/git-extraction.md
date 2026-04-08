<!-- Reference file for evolution-forensics skill. Loaded on demand. -->

# Git History Extraction & Cross-Reference Sources

## Phase 1a: Git History + Session Attribution

Extract commits with Session-ID trailers for session→commit joining:

```bash
DAYS=${DAYS:-14}
ARTIFACT_DIR="$HOME/Projects/meta/artifacts/evolution-forensics"
mkdir -p "$ARTIFACT_DIR"

for PROJECT in meta intel selve genomics skills; do
  PROJECT_DIR="$HOME/Projects/$PROJECT"
  [ -d "$PROJECT_DIR/.git" ] || continue

  echo "=== $PROJECT ===" >> "$ARTIFACT_DIR/git-history.md"
  git -C "$PROJECT_DIR" log \
    --since="$DAYS days ago" \
    --format="COMMIT|%H|%ai|%an|%s|%(trailers:key=Session-ID,valueonly)" \
    --numstat \
    >> "$ARTIFACT_DIR/git-history.md"
  echo "" >> "$ARTIFACT_DIR/git-history.md"
done
```

## Phase 1e: Cross-Reference Sources

```bash
# Improvement log findings with status
grep -E '^### \[|^\- \*\*Status' ~/Projects/meta/improvement-log.md > "$ARTIFACT_DIR/findings-status.txt"

# Hook trigger data
uv run python3 ~/Projects/meta/scripts/hook-roi.py --days $DAYS 2>/dev/null > "$ARTIFACT_DIR/hook-triggers.txt" || echo "hook-roi unavailable"

# Agent failure modes reference
cp ~/Projects/meta/agent-failure-modes.md "$ARTIFACT_DIR/failure-modes-ref.md" 2>/dev/null || true

# Vetoed decisions
cat ~/Projects/meta/.claude/rules/vetoed-decisions.md > "$ARTIFACT_DIR/vetoed.txt" 2>/dev/null || true
```
