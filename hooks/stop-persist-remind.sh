#!/bin/bash
# stop-persist-remind.sh — Stop hook: remind to persist research to DB/substrate
# Advisory (decision: approve). Fires when session modified research/docs files
# but didn't update sqlite/substrate.

trap 'exit 0' ERR

INPUT=$(cat)

echo "$INPUT" | python3 -c "
import sys, json, subprocess, os

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get('stop_hook_active', False):
    sys.exit(0)

cwd = data.get('cwd', '')
if not cwd or not os.path.isdir(os.path.join(cwd, '.git')):
    sys.exit(0)

# Delta-based: exclude files dirty at session start
session_id_file = os.path.join(cwd, '.claude', 'current-session-id')
baseline = set()
try:
    with open(session_id_file) as f:
        session_id = f.read().strip()
    with open(f'/tmp/session-baseline-{session_id}.txt') as f:
        for line in f:
            name = line[3:].rstrip('\n')
            if name:
                baseline.add(name)
except (OSError, FileNotFoundError):
    pass  # No baseline = check everything

# Get current uncommitted + recently committed changes
try:
    unstaged = subprocess.run(
        ['git', 'diff', '--name-only'], cwd=cwd,
        capture_output=True, text=True, timeout=5
    ).stdout.strip()
    recent_commits = subprocess.run(
        ['git', 'log', '--name-only', '--format=', '--since=2 hours ago'],
        cwd=cwd, capture_output=True, text=True, timeout=5
    ).stdout.strip()
except Exception:
    sys.exit(0)

session_files = set()
for section in [unstaged, recent_commits]:
    if section:
        session_files.update(f.strip() for f in section.split('\n') if f.strip())
session_files -= baseline

if not session_files:
    sys.exit(0)

# Check if research/docs files were touched
research_dirs = ('research/', 'docs/', 'interpreted/', 'memos/', 'analysis/')
research_touched = [f for f in session_files if any(f.startswith(d) for d in research_dirs)]

if not research_touched:
    sys.exit(0)

# Check if persistence was also done (DB files, sqlite3 usage, or substrate)
persist_indicators = ('.db', 'sqlite', 'substrate', 'knowledge')
db_touched = any(any(ind in f.lower() for ind in persist_indicators) for f in session_files)

if db_touched:
    sys.exit(0)

# Advisory warning
n = len(research_touched)
files_str = ', '.join(research_touched[:5])
if n > 5:
    files_str += f' +{n-5} more'
output = {
    'decision': 'block',
    'reason': f'Session modified {n} research/docs file(s) ({files_str}) but no DB/substrate updates detected. Consider persisting to sqlite/substrate before stopping.'
}
print(json.dumps(output))
" 2>/dev/null

exit 0
