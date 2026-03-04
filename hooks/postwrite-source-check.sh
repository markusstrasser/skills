#!/usr/bin/env bash
# postwrite-source-check.sh — Provenance tag validator for research files.
# Deploy as PostToolUse hook on Write|Edit.
#
# Mode: PROVENANCE_MODE=warn (default, advisory) or PROVENANCE_MODE=block (exit 2).
# Paths: RESEARCH_PATHS env var overrides defaults (pipe-separated regex).
#
# Validates:
#   1. Diff-level density — only checks new/changed content (not whole file)
#   2. Structural type checks — [SOURCE: url] must have URL, [DATA: x] must have qualifier
#   3. TRAINING-DATA cap — max 30% of tags in file
#
# Provenance tags:
#   [SOURCE: url]      — linked external source (must contain URL/DOI/PMID)
#   [DATABASE: name]   — named database/dataset (must name it)
#   [DATA]             — empirical observation
#   [INFERENCE]        — agent reasoning (file must have [SOURCE] or [DATA] premises)
#   [SPEC]             — speculation or hypothesis
#   [CALC]             — derived computation
#   [QUOTE]            — direct quotation
#   [TRAINING-DATA]    — from model training knowledge (capped at 30% of tags)
#   [PREPRINT]         — pre-peer-review source
#   [FRONTIER]         — cutting-edge, limited verification
#   [UNVERIFIED]       — not yet checked
#   [A1]-[F6]          — NATO Admiralty grading

# Fail open
trap 'exit 0' ERR

INPUT=$(cat)

# Extract file path (fast grep, no Python startup for non-matching paths)
FPATH=$(echo "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"//')

[ -z "$FPATH" ] && exit 0

# Path filter — only research-adjacent files
RESEARCH_PATHS="${RESEARCH_PATHS:-docs/|analysis/|research/|entities/|briefs/}"
echo "$FPATH" | grep -qE "$RESEARCH_PATHS" || exit 0

# Skip non-prose files
case "$FPATH" in
    *.py|*.sh|*.json|*.yaml|*.yml|*.toml|*.cfg|*.ini|*.sql|*.csv|*.tsv|*.parquet)
        exit 0
        ;;
esac

[ ! -f "$FPATH" ] && exit 0

# Delegate to Python validator — disable trap so exit 2 propagates
trap - ERR
echo "$INPUT" | python3 "$(dirname "$0")/source-check-validator.py"
