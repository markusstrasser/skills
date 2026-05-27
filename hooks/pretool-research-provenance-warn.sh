#!/usr/bin/env bash
# pretool-research-provenance-warn.sh — PreToolUse Write/Edit warn-mode for
# missing provenance tags on research files.
#
# Sibling to stop-research-gate.sh (which blocks at Stop time, after the
# write is committed). This one fires at Write/Edit time so the agent can
# add tags BEFORE committing — eliminates the round-trip cost discovered
# in the 2026-05-27 substrate-close session.
#
# Mode: WARN only (exit 1 with stderr). Stop-time hook still BLOCKs as
# final guard. Set PRETOOL_RESEARCH_PROVENANCE_MODE=block to escalate.
#
# Configurable via env:
#   RESEARCH_PATHS="docs/research/|analysis/" overrides the default file scope
#   PRETOOL_RESEARCH_PROVENANCE_MODE=warn|shadow|block (default warn)

INPUT=$(cat) || exit 0

echo "$INPUT" | python3 -c "
import sys, json, os, re

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool = data.get('tool_name', '')
if tool not in ('Write', 'Edit', 'MultiEdit'):
    sys.exit(0)

tool_input = data.get('tool_input', {}) or {}
file_path = tool_input.get('file_path', '')
if not file_path:
    sys.exit(0)

research_pattern = os.environ.get(
    'RESEARCH_PATHS',
    'docs/research/|analysis/(?:research|investments|entities|themes)/|docs/entities/'
)
exclude_pattern = (
    r'MEMORY\.md|CLAUDE\.md|maintenance-checklist\.md|'
    r'improvement-log\.md|README\.md|checkpoint\.md'
)

if not re.search(research_pattern, file_path):
    sys.exit(0)
if re.search(exclude_pattern, file_path):
    sys.exit(0)

# Extract content from the appropriate field
if tool == 'Write':
    content = tool_input.get('content', '')
elif tool == 'Edit':
    content = tool_input.get('new_string', '')
elif tool == 'MultiEdit':
    edits = tool_input.get('edits', []) or []
    content = '\n'.join(e.get('new_string', '') for e in edits)
else:
    content = ''

if not content.strip():
    sys.exit(0)

# Strip HTML comments — invisible-to-reader provenance is guard evasion.
content_visible = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

SOURCE_TAG = re.compile(
    r'\[SOURCE:|\[DATABASE:|\[DATA[\]:]|\[INFERENCE[\]:]|\[TRAINING-DATA[\]:]|'
    r'\[PREPRINT[\]:]|\[FRONTIER[\]:]|\[UNVERIFIED[\]:]|\[[A-F][1-6](?::[^\]]+)?\]|'
    r'https?://(?:doi\.org|pubmed\.ncbi|ncbi\.nlm\.nih\.gov|arxiv\.org)',
    re.IGNORECASE,
)

if SOURCE_TAG.search(content_visible):
    sys.exit(0)

mode = os.environ.get('PRETOOL_RESEARCH_PROVENANCE_MODE', 'warn').lower()
if mode == 'shadow':
    sys.exit(0)

msg_lines = [
    f'Research file write missing provenance tags: {file_path}',
    'Add at least one before stop-research-gate blocks at session end:',
    '  [SOURCE: url], [DATABASE: name], [DATA], [INFERENCE],',
    '  [TRAINING-DATA], [PREPRINT], [FRONTIER], [UNVERIFIED],',
    '  or NATO Admiralty [A1]-[F6].',
    '(WARN mode — set PRETOOL_RESEARCH_PROVENANCE_MODE=block to enforce.)',
]
print('\n'.join(msg_lines), file=sys.stderr)
if mode == 'block':
    sys.exit(2)
sys.exit(1)
"
