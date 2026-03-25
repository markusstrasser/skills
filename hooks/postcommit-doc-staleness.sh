#!/usr/bin/env bash
# postcommit-doc-staleness.sh — PostToolUse:Bash hook.
# After git commit with new/deleted/renamed files, surfaces CYCLE.md queue
# items and ACTIVE research memos as additionalContext so the agent can
# check if docs need updating. No sub-model call — the agent IS the LLM.
# Deterministic pre-filter: skips most commits (edits only, doc-only).
# Advisory only — fails open.

trap 'exit 0' ERR

INPUT=$(cat)

# Only trigger on git commit commands
CMD=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
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

# Deterministic pre-filter: only fire on structural changes
RESULT=$(python3 -c "
import subprocess, sys, os
from pathlib import Path

# Must have CYCLE.md or docs/research/ to be relevant
cwd = Path.cwd()
has_cycle = (cwd / 'CYCLE.md').exists()
has_research = (cwd / 'docs' / 'research').is_dir()
if not has_cycle and not has_research:
    print('skip')
    sys.exit()

# Get changed files with status (A=added, D=deleted, R=renamed, M=modified)
try:
    out = subprocess.check_output(
        ['git', 'diff-tree', '--name-status', '--find-renames', '--no-commit-id', '-r', 'HEAD'],
        text=True, timeout=5
    ).strip()
except Exception:
    print('skip')
    sys.exit()

if not out:
    print('skip')
    sys.exit()

changes = []
structural = False
for line in out.split('\n'):
    parts = line.split('\t')
    if len(parts) < 2:
        continue
    status, *files = parts
    fname = files[-1]  # last element for renames (R has old\tnew)

    # Skip doc-only changes (prevent feedback loop)
    if fname.endswith('.md') or fname.startswith('docs/') or fname.startswith('research/'):
        continue

    if status.startswith('A') or status.startswith('D') or status.startswith('R'):
        structural = True
        changes.append(f'{status}\t{fname}')

if not structural:
    print('skip')
    sys.exit()

# Collect context for advisory
context_parts = []

# CYCLE.md queue items
if has_cycle:
    import re
    cycle_text = (cwd / 'CYCLE.md').read_text()
    queue_m = re.search(
        r'^## Queue[^\n]*\n(.*?)(?=^## [^#]|\Z)',
        cycle_text, re.MULTILINE | re.DOTALL
    )
    if queue_m:
        items = []
        for line in queue_m.group(1).split('\n'):
            s = line.strip()
            if s.startswith('- **'):
                m2 = re.match(r'- \*\*([^*]+)\*\*', s)
                if m2:
                    items.append(m2.group(1))
        if items:
            context_parts.append('CYCLE.md queue items: ' + '; '.join(items))

# ACTIVE research memos
if has_research:
    research_dir = cwd / 'docs' / 'research'
    active_memos = []
    for f in sorted(research_dir.glob('*.md')):
        try:
            head = f.read_text()[:500]
            if 'ACTIVE' in head or 'TODO' in head.upper():
                active_memos.append(f.name)
        except Exception:
            continue
    if active_memos:
        context_parts.append('ACTIVE research memos: ' + ', '.join(active_memos[:10]))

if not context_parts:
    print('skip')
    sys.exit()

# Build advisory — surface structural changes + context directly.
# The agent (already a powerful LLM) does the semantic matching itself.
import json
msg_parts = ['New/deleted/renamed files in this commit:']
msg_parts.extend(changes)
msg_parts.append('')
msg_parts.extend(context_parts)
msg_parts.append('')
msg_parts.append('Check: do any CYCLE.md queue items or ACTIVE memos need updating?')
advisory = '\n'.join(msg_parts)
print(json.dumps({'additionalContext': 'DOC STALENESS CHECK:\n' + advisory}))
" 2>>"$HOME/.claude/hooks/session-init.log")

# RESULT is either 'skip' or a JSON additionalContext object
[ -z "$RESULT" ] && exit 0
echo "$RESULT" | head -1 | grep -q '^skip$' && exit 0

~/Projects/skills/hooks/hook-trigger-log.sh "doc-staleness" "info" "structural commit detected" 2>/dev/null || true
echo "$RESULT"

exit 0
