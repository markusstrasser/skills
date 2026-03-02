#!/usr/bin/env bash
# postwrite-source-check-semantic.sh — Semantic source citation check via Haiku.
# PostToolUse:Write|Edit command hook. Uses additionalContext for reliable injection.
# Exit 0 always (advisory, never blocks). Fails open on any error.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract file path — disable trap for Python call
trap - ERR
FPATH=$(echo "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    fp = d.get("file_path", "") or d.get("tool_input", {}).get("file_path", "")
    print(fp)
except Exception:
    print("")
' 2>/dev/null)
trap 'exit 0' ERR

[[ -z "$FPATH" ]] && exit 0

# Skip plan files
echo "$FPATH" | grep -q '\.claude/plans/' && exit 0

# Only check research-adjacent paths (configurable)
RESEARCH_PATHS="${RESEARCH_PATHS:-docs/|analysis/|research/|\.model-review/|entities/}"
echo "$FPATH" | grep -qE "$RESEARCH_PATHS" || exit 0

# Skip non-text files
case "$FPATH" in
    *.py|*.sh|*.json|*.yaml|*.yml|*.toml|*.cfg|*.ini|*.sql|*.csv|*.tsv|*.parquet)
        exit 0
        ;;
esac

[[ ! -f "$FPATH" ]] && exit 0

# Quick pre-check: if file has reasonable tag density, skip the API call
if grep -qE '\[SOURCE:|\[DATABASE:|\[DATA\]|\[INFERENCE\]|\[TRAINING-DATA\]|\[PREPRINT\]|\[FRONTIER\]|\[UNVERIFIED\]|\[[A-F][1-6]\]|\[PubMed\]|\[arXiv\]|\[Exa\]|\[S2\]|\[ClinGen\]|\[CPIC\]|\[gnomAD\]|\[OMIM\]' "$FPATH"; then
    TAG_COUNT=$(grep -cE '\[SOURCE:|\[DATABASE:|\[[A-F][1-6]\]|\[PubMed\]|\[arXiv\]|\[Exa\]|\[S2\]|\[ClinGen\]|\[CPIC\]|\[gnomAD\]|\[OMIM\]|\[DATA\]|\[INFERENCE\]' "$FPATH" || true)
    CLAIM_LINES=$(wc -l < "$FPATH")
    if (( TAG_COUNT * 30 >= CLAIM_LINES )); then
        exit 0
    fi
fi

# Delegate to Python for Haiku API call — disable trap
trap - ERR
head -150 "$FPATH" | python3 "$(dirname "$0")/source-check-haiku.py" "$(basename "$FPATH")" 2>/dev/null

exit 0
