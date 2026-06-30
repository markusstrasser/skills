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
# HUMAN.md = the loop's human-escalation OUTBOX (wakeup-cadence.md), not a sourced
# memo — it has no claims to provenance. It was the single worst cry-wolf source
# (fired 32x on one HUMAN.md in the 2026-06-29 session). Mirrored into the Stop
# gate's EXCLUDE_PATTERN too, so an outbox is never blocked at session end either.
exclude_pattern = (
    r'MEMORY\.md|CLAUDE\.md|maintenance-checklist\.md|'
    r'improvement-log\.md|README\.md|checkpoint\.md|HUMAN\.md'
)

if not re.search(research_pattern, file_path):
    sys.exit(0)
if re.search(exclude_pattern, file_path):
    sys.exit(0)

# Incoming content from the appropriate field.
if tool == 'Write':
    incoming = tool_input.get('content', '')
elif tool == 'Edit':
    incoming = tool_input.get('new_string', '')
elif tool == 'MultiEdit':
    edits = tool_input.get('edits', []) or []
    incoming = '\n'.join(e.get('new_string', '') for e in edits)
else:
    incoming = ''

if not incoming.strip():
    sys.exit(0)

# FILE-LEVEL check (2026-06-30): provenance is a whole-FILE invariant, and the Stop
# gate (stop-research-gate.sh) blocks on the FULL file — so an Edit must be judged
# against the file, not the edited chunk. Checking only new_string cried wolf 144x
# across substrate sessions (26x on ONE handoff doc, 20x on _done.md): every edit to
# an already-tagged file re-warned, disagreeing with the Stop gate that would pass it.
# For Edit/MultiEdit a tag anywhere in the on-disk file satisfies the requirement;
# Write replaces the whole file, so only its incoming content counts.
existing = ''
if tool in ('Edit', 'MultiEdit') and file_path:
    try:
        existing = open(file_path, encoding='utf-8', errors='ignore').read()
    except OSError:
        existing = ''

# Strip HTML comments — invisible-to-reader provenance is guard evasion.
content_visible = re.sub(r'<!--.*?-->', '', incoming + '\n' + existing, flags=re.DOTALL)

try:  # canonical claim-tag taxonomy (SSOT: provenance_tags.re) — load so [Exa]/[S2]/
    _canon = open(os.path.expanduser('~/Projects/skills/hooks/provenance_tags.re')).read().strip()
except OSError:  # [gnomAD]/[OMIM] etc. count here too; prepend only if non-empty (no empty-OR)
    _canon = ''
# MIRROR of stop-research-gate.sh's SOURCE_TAG research-specific tail. The two research
# gates share the canonical HEAD (provenance_tags.re, drift-tested by test_provenance_tags.py)
# but each inlines this TAIL by design (the test deliberately covers only the head). This
# copy had drifted STALE — it missed the comma-qualified forms ([DATA, src, date]) and the
# [DOI:/[PMID:/[PMC] + prose-DOI/markdown-link forms the gate accepts, so it warned at
# write-time about provenance the Stop gate would have PASSED. Kept verbatim-in-lockstep
# (case-sensitive, like the gate) so a write-time warning means a real stop-time block; if
# this tail ever grows a third consumer, single-source it (#9).
SOURCE_TAG = re.compile(
    ((_canon + '|') if _canon else '') +
    r'\[SOURCE:|\[DATABASE:|\[DATA[\]:,]|\[INFERENCE[\]:,]|\[TRAINING-DATA[\]:,]|'
    r'\[PREPRINT[\]:,]|\[FRONTIER[\]:,]|\[UNVERIFIED[\]:,]|\[[A-F][1-6](?:[:,][^\]]+)?\]|'
    r'\[DOI:\s*10\.\d{4,}|\[PMID:\s*\d+|\[PMC\d{4,}\]|'
    r'\]\(https?://(?:dx\.)?doi\.org/|'
    r'\]\(https?://(?:www\.)?ncbi\.nlm\.nih\.gov/(?:pubmed|pmc)|'
    r'(?:\bDOI[:\s]\s*10\.\d{4,}/|\bPMID[:\s]\s*\d{6,})'
)

if SOURCE_TAG.search(content_visible):
    sys.exit(0)

mode = os.environ.get('PRETOOL_RESEARCH_PROVENANCE_MODE', 'warn').lower()
if mode == 'shadow':
    sys.exit(0)

msg = (
    f'PROVENANCE: research file written without source tags: {file_path}. '
    'Add at least one now (before stop-research-gate blocks at session end): '
    '[SOURCE: url], [DATABASE: name], [DATA], [INFERENCE], [TRAINING-DATA], '
    '[PREPRINT], [FRONTIER], [UNVERIFIED], or NATO Admiralty [A1]-[F6].'
)
if mode == 'block':
    print(msg, file=sys.stderr)
    sys.exit(2)
# ERGONOMIC FIX (2026-06-17): emit additionalContext so the AGENT actually sees the
# reminder at write time and tags in-flight — exit-1 stderr never reaches the model
# (same lesson stop-research-gate learned for itself; 17 recurring 'wrote memo →
# blocked at stop → retry' misses were this warning being invisible).
# research/2026-06-17-embed-once-validated-recurring-mistakes.md
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'additionalContext': msg}}))
sys.exit(0)
"
