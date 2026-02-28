#!/usr/bin/env bash
# postwrite-source-check.sh — Blocks writes to research paths without source tags.
# Deploy as PostToolUse hook on Write|Edit.
# Exit 2 = block (forces agent to add sources). Exit 0 = pass.
# Fails open: if this script errors, exit 0 (don't block all work).

# Trap errors — fail open
trap 'exit 0' ERR

INPUT=$(cat)

# Extract file path from hook input JSON
FPATH=$(echo "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"//')

# No file path found — pass through
[ -z "$FPATH" ] && exit 0

# Check if file matches research paths (configurable via RESEARCH_PATHS env var)
RESEARCH_PATHS="${RESEARCH_PATHS:-docs/|analysis/|docs/research/|docs/entities/}"
if ! echo "$FPATH" | grep -qE "$RESEARCH_PATHS"; then
    exit 0
fi

# Skip non-markdown/non-text files
case "$FPATH" in
    *.py|*.sh|*.json|*.yaml|*.yml|*.toml|*.cfg|*.ini|*.sql)
        exit 0
        ;;
esac

# File must exist to check content
[ ! -f "$FPATH" ] && exit 0

# Check for source tags in the file content
# Matches: [SOURCE:...], [A1]-[F6] (Admiralty), [DATABASE:...], [DATA], [INFERENCE],
# [TRAINING-DATA], [PREPRINT], [FRONTIER], [UNVERIFIED]
if grep -qE '\[SOURCE:|\[DATABASE:|\[DATA\]|\[INFERENCE\]|\[TRAINING-DATA\]|\[PREPRINT\]|\[FRONTIER\]|\[UNVERIFIED\]|\[[A-F][1-6]\]' "$FPATH"; then
    exit 0
fi

echo "BLOCKED: Research file written without source tags." >&2
echo "Add at least one provenance tag: [SOURCE: url], [DATABASE: name], [DATA], [INFERENCE], [TRAINING-DATA], [PREPRINT], [FRONTIER], [UNVERIFIED], or Admiralty [A1]-[F6]." >&2
echo "File: $FPATH" >&2
exit 2
