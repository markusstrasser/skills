#!/usr/bin/env bash
# posttool-citation-remind.sh — Advisory: remind to verify citations in research files.
# Deploy as PostToolUse hook on Write|Edit.
#
# Env: CITATION_PATHS (pipe-separated regex for monitored paths, default: docs/research/|docs/entities/)
#
# Lightweight file-path check only, no network calls. Exit 0 always (advisory).

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null)
[[ -z "$FILE_PATH" ]] && exit 0

CITATION_PATHS="${CITATION_PATHS:-docs/research/|docs/entities/}"

# Only fire for matching paths
echo "$FILE_PATH" | grep -qE "$CITATION_PATHS" || exit 0
# Only fire for markdown files
case "$FILE_PATH" in *.md) ;; *) exit 0 ;; esac

# Check if the file has citation patterns (DOI/PMID) without [VERIFIED] tag
if grep -qE '(10\.\d{4,}/|PMID:?\s*\d{5,}|doi\.org/)' "$FILE_PATH" 2>/dev/null; then
  CITE_COUNT=$(grep -cE '(10\.\d{4,}/|PMID:?\s*\d{5,}|doi\.org/)' "$FILE_PATH" 2>/dev/null || echo 0)
  ~/Projects/skills/hooks/hook-trigger-log.sh "citation-remind" "advise" "$FILE_PATH" 2>/dev/null || true
  echo "Advisory: $CITE_COUNT citation references detected in $(basename "$FILE_PATH"). Verify IDs are resolvable." >&2
fi
exit 0
