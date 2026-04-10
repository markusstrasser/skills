#!/usr/bin/env bash
# PreToolUse on Write: inject frontmatter template if writing a new knowledge-eligible file.
# Only fires for NEW files (not edits). Injects the template BEFORE the write so the
# agent includes frontmatter on the first attempt.

trap 'exit 0' ERR

# Quick path check from env var (fastest possible exit for non-eligible files)
FPATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    print(d.get('file_path', ''))
except: pass
" 2>/dev/null)

[ -z "$FPATH" ] && exit 0

# Only .md files in eligible directories
echo "$FPATH" | grep -qE '(analysis/entities|docs/research|docs/entities|research/|decisions/).*\.md$' || exit 0

# Only NEW files (don't inject on edits to existing files)
[ -f "$FPATH" ] && exit 0

# Check if the content already has frontmatter
echo "$CLAUDE_TOOL_INPUT" | grep -q '"---\\n' && exit 0

# Determine project from path
if echo "$FPATH" | grep -q "Projects/intel"; then
    TEMPLATE="Entity files need YAML frontmatter: ticker, name, sector, conviction, last_reviewed, conviction_journal. See .claude/rules/doc-format.md."
elif echo "$FPATH" | grep -q "Projects/phenome"; then
    TEMPLATE="Research memos need YAML frontmatter: title, date, status, tags, summary. Follow MEMO_CONTRACT.md structure. See .claude/rules/doc-format.md."
elif echo "$FPATH" | grep -q "Projects/agent-infra"; then
    TEMPLATE="Research memos need YAML frontmatter: title, date. See .claude/rules/doc-format.md."
else
    exit 0
fi

ESCAPED=$(echo "$TEMPLATE" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)
echo "{\"additionalContext\": ${ESCAPED}}"
