#!/usr/bin/env bash
# pretool-source-remind.sh — Remind agent about source tags BEFORE writing to research paths.
# PreToolUse hook on Write|Edit. Outputs additionalContext so the agent sees the reminder
# before the write happens (vs postwrite-source-check.sh which warns after).
#
# Deploy: PreToolUse matcher "Write|Edit"
# Env: RESEARCH_PATHS (pipe-separated regex, default: docs/|analysis/|research/|entities/|briefs/)

trap 'exit 0' ERR

INPUT=$(cat)

FPATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except:
    print('')
" 2>/dev/null || echo "")

[ -z "$FPATH" ] && exit 0

# Skip non-prose files
case "$FPATH" in
    *.py|*.sh|*.json|*.yaml|*.yml|*.toml|*.cfg|*.ini|*.sql|*.csv|*.tsv|*.parquet)
        exit 0
        ;;
esac

RESEARCH_PATHS="${RESEARCH_PATHS:-docs/|analysis/|research/|entities/|briefs/}"
if ! echo "$FPATH" | grep -qE "$RESEARCH_PATHS"; then
    exit 0
fi

# Decision records document choices, not claims — skip
echo "$FPATH" | grep -qE '/decisions/' && exit 0

# Check if the content being written already has source tags
CONTENT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {})
    # For Write: check content. For Edit: check new_string.
    print(ti.get('content', '') or ti.get('new_string', ''))
except:
    print('')
" 2>/dev/null || echo "")

if echo "$CONTENT" | grep -qE '\[SOURCE:|\[DATABASE:|\[DATA\]|\[INFERENCE\]|\[SPEC\]|\[CALC\]|\[QUOTE\]|\[TRAINING-DATA\]|\[PREPRINT\]|\[FRONTIER\]|\[UNVERIFIED\]|\[[A-F][1-6]\]'; then
    exit 0
fi

~/Projects/skills/hooks/hook-trigger-log.sh "source-remind" "remind" "$FPATH" 2>/dev/null || true
cat <<'JSON'
{"additionalContext": "PROVENANCE REQUIRED for research paths. Tag factual claims inline:\n\n  Bad:  Scrotal cooling raises testosterone by 20%.\n  Good: Scrotal cooling raises testosterone by 20% [SOURCE: https://doi.org/10.xxxx/yyyy]\n  Good: No RCT confirms magnitude beyond 5% [INFERENCE]\n  Good: gnomAD AF 0.03 for EUR [DATABASE: gnomAD v4.1]\n\nTags: [SOURCE: url], [DATABASE: name], [DATA], [INFERENCE], [SPEC], [TRAINING-DATA]. Post-write check flags untagged claims."}
JSON
exit 0
