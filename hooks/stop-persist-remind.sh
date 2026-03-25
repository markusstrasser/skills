#!/bin/bash
# stop-persist-remind.sh — Stop hook: remind to persist research to DB/substrate
# Advisory: detects research/docs file modifications without corresponding DB/sqlite updates.
# Uses session baseline from SessionStart hook (02-git-baseline.sh).

INPUT=$(cat)

# Check stop_hook_active to prevent infinite loops
echo "$INPUT" | python3 -c "
import sys, json, subprocess, os

data = json.load(sys.stdin)
if data.get('stop_hook_active', False):
    sys.exit(0)

cwd = data.get('cwd', '')
if not cwd or not os.path.isdir(os.path.join(cwd, '.git')):
    sys.exit(0)

# Load session baseline (created by 02-git-baseline.sh at SessionStart)
session_id_file = os.path.join(cwd, '.claude', 'current-session-id')
try:
    with open(session_id_file) as f:
        session_id = f.read().strip()
    with open(f'/tmp/session-baseline-{session_id}.txt') as f:
        baseline = set(l[3:].rstrip() for l in f if len(l) > 3)
except (OSError, FileNotFoundError):
    baseline = set()

# Compute session-modified files
try:
    result = subprocess.run(['git', 'diff', '--name-only'], cwd=cwd,
                          capture_output=True, text=True, timeout=5)
    current = set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
    result2 = subprocess.run(['git', 'log', '--name-only', '--format=', '-1'], cwd=cwd,
                           capture_output=True, text=True, timeout=5)
    committed = set(result2.stdout.strip().split('\n')) if result2.stdout.strip() else set()
except (subprocess.TimeoutExpired, OSError):
    sys.exit(0)

session_files = (current | committed) - baseline

# Check if research/docs dirs were touched
research_dirs = ('research/', 'docs/', 'interpreted/', 'memos/')
research_touched = [f for f in session_files if any(f.startswith(d) for d in research_dirs)]

if not research_touched:
    sys.exit(0)

# Check if DB/substrate was also updated (file-based or command-based)
db_touched = any('sqlite' in f or 'substrate' in f or '.db' in f for f in session_files)
if db_touched:
    sys.exit(0)

# Advisory: research touched but no DB update
output = {
    'decision': 'allow',
    'additionalContext': f'Session modified {len(research_touched)} research/docs file(s) ({research_touched[0]}...) but did not update sqlite/substrate. Consider persisting before stopping.'
}
print(json.dumps(output))
" 2>/dev/null

exit 0
