#!/usr/bin/env bash
# postcommit-propagate-check.sh — PostToolUse:Bash hook.
# After a git commit, checks if changed files match any entry in dependency-manifest.json.
# Advisory: warns about downstream consumers that may need updating.
# Fails open (exit 0 on error).

trap 'exit 0' ERR

INPUT=$(cat)

# Only trigger on git commit commands
CMD=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    # Check tool_result for commit confirmation, or command for git commit
    cmd = d.get('command', '')
    result = str(d.get('tool_result', d.get('stdout', '')))
    if 'git commit' in cmd or ('create mode' in result and 'insertions' in result):
        print('commit')
    else:
        print('skip')
except Exception:
    print('skip')
" 2>/dev/null)

[ "$CMD" = "skip" ] && exit 0

MANIFEST="$HOME/.claude/dependency-manifest.json"
[ -f "$MANIFEST" ] || exit 0

# Get changed files from last commit
CHANGED=$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null) || exit 0
[ -z "$CHANGED" ] && exit 0

# Check against manifest
WARN=$(python3 -c "
import json, sys

manifest = json.load(open('$MANIFEST'))
changed = '''$CHANGED'''.strip().split('\n')

warnings = []
for asset, info in manifest.items():
    # Check if any changed file matches the asset name or its path patterns
    for f in changed:
        fname = f.split('/')[-1].rsplit('.', 1)[0]  # basename without ext
        # Match by asset name in path, or exact consumer path match
        if asset.lower() in f.lower() or asset.replace('-', '_') in f.lower():
            consumers = info.get('consumers', [])
            if consumers:
                names = ', '.join(c.split('/')[-1] for c in consumers[:5])
                warnings.append(f'{asset}: {len(consumers)} consumers ({names})')
            break

if warnings:
    print('DEPENDENCY UPDATE CHECK: You changed files that others depend on. Affected: ' + ' | '.join(warnings))
" 2>/dev/null)

if [ -n "$WARN" ]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "propagate-check" "warn" "${WARN:0:100}" 2>/dev/null || true
    SAFE=$(echo "$WARN" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)
    echo "{\"additionalContext\": ${SAFE}}"
fi

exit 0
