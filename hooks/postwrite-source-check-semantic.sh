#!/usr/bin/env bash
# postwrite-source-check-semantic.sh — Semantic source citation check via Haiku.
# PostToolUse:Write|Edit command hook. Uses additionalContext for reliable injection.
# Exit 0 always (advisory, never blocks). Fails open on any error.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract file path (top-level file_path, falling back to tool_input.file_path)
FPATH=$(printf '%s' "$INPUT" | jq -r '(.file_path // "") as $fp | if $fp == "" then (.tool_input.file_path // "") else $fp end' 2>/dev/null || echo "")

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
PROVENANCE_TAG_RE="$(cat "$HOME/Projects/skills/hooks/provenance_tags.re" 2>/dev/null)"  # taxonomy SSOT — references/provenance-tags.md
# Density PRE-CHECK only (skip the paid API when a file is already tag-dense). An empty/missing
# SSOT must NOT enter this block ([ -n ] guard) — bare `grep -qE ""` matches every line and would
# wrongly skip the semantic check; instead fall through to it.
if [ -n "$PROVENANCE_TAG_RE" ] && grep -qE "$PROVENANCE_TAG_RE" "$FPATH"; then
    # Deliberately a SUBSET of the SSOT, NOT the full taxonomy: counts substantive citations only.
    # Meta/hedge tags ([UNVERIFIED]/[SPEC]/[CALC]/[QUOTE]/[TRAINING-DATA]/[PREPRINT]/[FRONTIER]) are
    # excluded so they can't inflate citation-density and skip the check. Different concern → not single-sourced.
    TAG_COUNT=$(grep -cE '\[SOURCE:|\[DATABASE:|\[[A-F][1-6](:[^]]+)?\]|\[PubMed\]|\[arXiv\]|\[Exa\]|\[S2\]|\[ClinGen\]|\[CPIC\]|\[gnomAD\]|\[OMIM\]|\[DATA\]|\[INFERENCE\]' "$FPATH" || true)
    CLAIM_LINES=$(wc -l < "$FPATH")
    if (( TAG_COUNT * 30 >= CLAIM_LINES )); then
        exit 0
    fi
fi

# Delegate to Python for Haiku API call — disable trap
trap - ERR
head -150 "$FPATH" | python3 "$(dirname "$0")/source-check-haiku.py" "$(basename "$FPATH")" 2>/dev/null

exit 0
