#!/usr/bin/env bash
# stop-research-gate.sh — Stop hook that gates research sessions on source tags.
# Blocks stop (exit 2) if research files were modified without source tags.
# Soft reminder (exit 0) if research files have tags but quality checklist applies.
# Checks stop_hook_active to prevent infinite loops. Fails open on error.
#
# Deploy as Stop hook. Configurable via env:
#   RESEARCH_PATHS="docs/|analysis/" ~/Projects/skills/hooks/stop-research-gate.sh

INPUT=$(cat) || exit 0

RESEARCH_PATHS="${RESEARCH_PATHS:-docs/research/|analysis/|docs/entities/}"
EXCLUDE_PATTERN="${EXCLUDE_PATTERN:-MEMORY\.md|CLAUDE\.md|maintenance-checklist\.md|improvement-log\.md|README\.md}"

echo "$INPUT" | python3 -c "
import sys, json, os, re, subprocess

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

# Prevent infinite loops: if we already forced a continue, let it stop
if data.get('stop_hook_active', False):
    sys.exit(0)

cwd = data.get('cwd', '')
if not cwd or not os.path.isdir(os.path.join(cwd, '.git')):
    sys.exit(0)

research_pattern = os.environ.get('RESEARCH_PATHS', 'docs/research/|analysis/|docs/entities/')
exclude_pattern = os.environ.get('EXCLUDE_PATTERN', r'MEMORY\.md|CLAUDE\.md|maintenance-checklist\.md|improvement-log\.md|README\.md')

# Session-scoped diff: only check files modified THIS session, not pre-existing dirty files.
# Read session ID from .claude/current-session-id, then load base SHA and dirty baseline from /tmp/.
base_sha = 'HEAD'
session_id = ''
baseline_dirty = set()
try:
    sid_path = os.path.join(cwd, '.claude', 'current-session-id')
    with open(sid_path) as f:
        session_id = f.read().strip()
    with open(f'/tmp/session-base-sha-{session_id}.txt') as f:
        base_sha = f.read().strip()
except (OSError, FileNotFoundError):
    pass  # No baseline = fall back to HEAD (pre-fix behavior)

# Load dirty-file baseline from session start (written by 02-git-baseline.sh).
# Files dirty at session start belong to another agent or pre-existing state — exclude them.
try:
    with open(f'/tmp/session-baseline-{session_id}.txt') as f:
        for line in f:
            # git status --short format: 'XY filename' where X/Y may be space.
            # Strip only trailing newline — leading space is significant (e.g. ' M path').
            line = line.rstrip('\n')
            if line.strip():
                path = line[3:].split(' -> ')[-1]
                baseline_dirty.add(path)
except (OSError, FileNotFoundError):
    pass  # No baseline = check everything (first-run safety)

changed = []
try:
    r1 = subprocess.run(['git', 'diff', '--name-only', base_sha], cwd=cwd, capture_output=True, text=True, timeout=5)
    changed += [l for l in r1.stdout.strip().split('\n') if l]
    r2 = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], cwd=cwd, capture_output=True, text=True, timeout=5)
    changed += [l for l in r2.stdout.strip().split('\n') if l]
except Exception:
    sys.exit(0)

# Exclude files that were already dirty at session start (other agents' work)
if baseline_dirty:
    changed = [f for f in changed if f not in baseline_dirty]

# Filter to research-path markdown files, excluding known non-research files
research_files = [
    f for f in set(changed)
    if re.search(research_pattern, f)
    and f.endswith(('.md', '.txt', '.org'))
    and not re.search(exclude_pattern, os.path.basename(f))
]

if not research_files:
    sys.exit(0)

# Check each research file for source tags
SOURCE_TAG = re.compile(
    # Explicit bracket-tagged provenance
    r'\[SOURCE:|\[DATABASE:|\[DATA[\]:]|\[INFERENCE[\]:]|\[TRAINING-DATA[\]:]|'
    r'\[PREPRINT[\]:]|\[FRONTIER[\]:]|\[UNVERIFIED[\]:]|\[[A-F][1-6]\]|'
    # Equivalent identifier-bracket forms: [DOI:...], [PMID:...], [PMC######]
    r'\[DOI:\s*10\.\d{4,}|\[PMID:\s*\d+|\[PMC\d{4,}\]|'
    # Markdown links to canonical citation hosts count as provenance
    r'\]\(https?://(?:dx\.)?doi\.org/|'
    r'\]\(https?://(?:www\.)?ncbi\.nlm\.nih\.gov/(?:pubmed|pmc)|'
    # Prose DOI/PMID (e.g. "DOI 10.1038/..." or "PMID 12345678")
    r'(?:\bDOI[:\s]\s*10\.\d{4,}/|\bPMID[:\s]\s*\d{6,})'
)

missing = []
for f in research_files:
    fpath = os.path.join(cwd, f)
    if not os.path.isfile(fpath):
        continue
    with open(fpath) as fh:
        content = fh.read()
    if not content.strip():
        continue  # Skip empty files (e.g., llmx -o placeholder before model finishes)
    if not SOURCE_TAG.search(content):
        missing.append(f)

if missing:
    import subprocess as _sp
    _sp.run([os.path.expanduser('~/Projects/skills/hooks/hook-trigger-log.sh'),
             'research-gate', 'block', f'{len(missing)} files without tags'],
            capture_output=True, timeout=5)
    print('BLOCKED: Research files modified without source tags:', file=sys.stderr)
    for f in missing:
        print(f'  - {f}', file=sys.stderr)
    print('Add provenance tags: [SOURCE: url], [DATABASE: name], [DATA], [INFERENCE],', file=sys.stderr)
    print('[TRAINING-DATA], [PREPRINT], [FRONTIER], [UNVERIFIED], or Admiralty [A1]-[F6].', file=sys.stderr)
    sys.exit(2)

# Soft reminder: files have tags, but check quality
print('Research files have source tags. CHECKLIST: (1) Did you fetch primary sources '
      'or only use training data? (2) Did you search for contradictory evidence? '
      '(3) Are all claims source-graded?', file=sys.stderr)
sys.exit(0)
"
