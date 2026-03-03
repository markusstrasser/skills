#!/usr/bin/env bash
# postwrite-source-check.sh — Warns/blocks writes to research paths without source tags.
# Deploy as PostToolUse hook on Write|Edit.
#
# Mode: PROVENANCE_MODE=warn (default, advisory) or PROVENANCE_MODE=block (exit 2).
# Paths: RESEARCH_PATHS env var overrides defaults (pipe-separated regex).
#
# Provenance tags:
#   [SOURCE: url]      — linked external source
#   [DATABASE: name]   — named database/dataset
#   [DATA]             — empirical observation
#   [INFERENCE]        — agent reasoning from sourced premises
#   [SPEC]             — speculation or hypothesis (unlabeled = inference promotion)
#   [CALC]             — derived computation (prevents unsourced arithmetic)
#   [QUOTE]            — direct quotation
#   [TRAINING-DATA]    — from model training knowledge
#   [PREPRINT]         — pre-peer-review source
#   [FRONTIER]         — cutting-edge, limited verification
#   [UNVERIFIED]       — not yet checked
#   [A1]-[F6]          — NATO Admiralty grading

# Trap errors — fail open
trap 'exit 0' ERR

MODE="${PROVENANCE_MODE:-warn}"
INPUT=$(cat)

# Extract file path from hook input JSON
FPATH=$(echo "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"//')

# No file path found — pass through
[ -z "$FPATH" ] && exit 0

# Check if file matches research paths (configurable via RESEARCH_PATHS env var)
# Default covers: docs/, analysis/, research/, entities/, briefs/ at any depth
RESEARCH_PATHS="${RESEARCH_PATHS:-docs/|analysis/|research/|entities/|briefs/}"
if ! echo "$FPATH" | grep -qE "$RESEARCH_PATHS"; then
    exit 0
fi

# Skip non-prose files
case "$FPATH" in
    *.py|*.sh|*.json|*.yaml|*.yml|*.toml|*.cfg|*.ini|*.sql|*.csv|*.tsv|*.parquet)
        exit 0
        ;;
esac

# File must exist to check content
[ ! -f "$FPATH" ] && exit 0

# Check for provenance tags — require DENSITY, not just presence.
# A file with 1 tag and 50 untagged claims should still warn.
TAG_COUNT=$(grep -cE '\[SOURCE:|\[DATABASE:|\[DATA\]|\[INFERENCE\]|\[SPEC\]|\[CALC\]|\[QUOTE\]|\[TRAINING-DATA\]|\[PREPRINT\]|\[FRONTIER\]|\[UNVERIFIED\]|\[[A-F][1-6]\]' "$FPATH" 2>/dev/null || echo 0)

if [ "$TAG_COUNT" -gt 0 ]; then
    # Estimate claim density: lines with numbers, percentages, dates, author-year patterns
    CLAIM_COUNT=$(grep -cE '[0-9]+%|[0-9]{4}-[0-9]{2}|\$[0-9]|PMID|et al\.|[A-Z][a-z]+ [0-9]{4}|confirmed|refuted|showed|found that|OR [0-9]|P[=<>]' "$FPATH" 2>/dev/null || echo 0)
    # Threshold: at least 1 tag per 5 claim-bearing lines
    if [ "$CLAIM_COUNT" -gt 0 ] && [ "$TAG_COUNT" -gt 0 ]; then
        RATIO=$(( CLAIM_COUNT / TAG_COUNT ))
        if [ "$RATIO" -le 5 ]; then
            exit 0
        fi
        # Sparse — fall through to warning
    else
        exit 0
    fi
fi

TAG_LIST="[SOURCE: url], [DATABASE: name], [DATA], [INFERENCE], [SPEC], [CALC], [QUOTE], [TRAINING-DATA], [PREPRINT], [FRONTIER], [UNVERIFIED], or Admiralty [A1]-[F6]"

if [ "$MODE" = "block" ]; then
    echo "BLOCKED: Research file written without provenance tags." >&2
    echo "Add at least one: $TAG_LIST" >&2
    echo "File: $FPATH" >&2
    ~/Projects/skills/hooks/hook-trigger-log.sh "source-check" "block" "$FPATH" 2>/dev/null || true
    exit 2
else
    # Advisory mode — warn via additionalContext (injected into conversation)
    ~/Projects/skills/hooks/hook-trigger-log.sh "source-check" "warn" "$FPATH" 2>/dev/null || true
    echo "{\"additionalContext\": \"PROVENANCE WARNING: Research file written without source tags. File: $FPATH. Add at least one provenance tag: $TAG_LIST. Use [SPEC] to explicitly label speculation.\"}"
    exit 0
fi
