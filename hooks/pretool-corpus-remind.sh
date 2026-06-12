#!/usr/bin/env bash
# pretool-corpus-remind.sh — Advisory: check ~/Projects/corpus/ store
# before fetching a paper from the web.
#
# PreToolUse hook on WebFetch, mcp__research__fetch_paper, mcp__research__save_paper,
# and Bash commands invoking paper downloads. Advisory only (exit 0); prints
# a one-line nudge if the URL/DOI/PMID resembles a paper identifier and the
# agent hasn't already consulted corpus_lookup this session.
#
# Triggers exactly once per (session, identifier-prefix). Suppressible via
# CORPUS_REMIND=0.

set +e

# Suppression
if [ "${CORPUS_REMIND:-1}" = "0" ]; then
  exit 0
fi

# Session-scoped state — one reminder per identifier-prefix
SESSION_ID="${CLAUDE_SESSION_ID:-default}"
STATE_DIR="/tmp/corpus-remind-${SESSION_ID}"
mkdir -p "$STATE_DIR" 2>/dev/null

already_reminded() { [ -f "$STATE_DIR/$1" ]; }
mark_reminded() { touch "$STATE_DIR/$1" 2>/dev/null; }

INPUT="${CLAUDE_TOOL_INPUT:-$(cat)}"
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")

# Extract a likely paper identifier from the tool input. We accept:
#   - DOI: \b10\.[0-9]{4,9}/[^\s"<>]+
#   - PMID inside a pubmed URL: /pubmed/([0-9]+) or pmid=([0-9]+)
#   - arXiv IDs: arxiv.org/abs/(\d{4}\.\d{4,5}) — already a DOI variant
#   - bioRxiv/medRxiv: /content/(10\.1101/[0-9.]+)
#
# We don't parse the URL formally — a single regex scan over the input JSON
# is enough.
MATCH_SCRIPT='
import re, sys
inp = sys.stdin.read()
m = re.search(r"\b10\.\d{4,9}/[\w.\-()/:_]+", inp)
if m:
    doi = m.group(0).rstrip(".,;:)\"")
    # Strip medRxiv/bioRxiv version suffixes (URL path artifact, not canonical DOI)
    doi = re.sub(r"v\d+$", "", doi)
    print(doi)
    sys.exit(0)
m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", inp, re.IGNORECASE)
if m:
    print("10.48550/arXiv." + m.group(1))
    sys.exit(0)
m = re.search(r"(?:pubmed/|pmid=)(\d{6,9})", inp, re.IGNORECASE)
if m:
    print("pmid:" + m.group(1))
    sys.exit(0)
sys.exit(1)
'

IDENT="$(printf '%s' "$INPUT" | python3 -c "$MATCH_SCRIPT" 2>/dev/null)"
if [ -z "$IDENT" ]; then
  exit 0
fi

# Tool filter — only nudge on paper-relevant tools
case "$TOOL" in
  WebFetch | mcp__research__fetch_paper | mcp__research__save_paper)
    ;;
  Bash)
    # Bash command must include a paper-fetch verb to bother us
    CMD=$(printf '%s' "$INPUT" | jq -r '(if has("tool_input") then (.tool_input // {}) else . end) | .command // ""' 2>/dev/null)
    case "$CMD" in
      *curl*sci-hub*|*curl*doi.org*|*curl*biorxiv*|*curl*medrxiv*|*curl*pubmed*|*wget*doi.org*) ;;
      *) exit 0 ;;
    esac
    ;;
  *)
    exit 0
    ;;
esac

# Sanitize identifier for filename — at most one nudge per identifier per session
SAFE_IDENT=$(echo "$IDENT" | tr '/.: ' '____' | head -c 80)
if already_reminded "$SAFE_IDENT"; then
  exit 0
fi
mark_reminded "$SAFE_IDENT"

# Check if the paper is already in the local store — short-circuit the nudge
# if it is, since the agent should obviously use it.
STORE_ROOT="${CORPUS_ROOT:-$HOME/Projects/corpus}"
case "$IDENT" in
  pmid:*)
    PID="pmid_${IDENT#pmid:}"
    ;;
  *)
    # Put '-' last to avoid range interpretation; otherwise tr eats digits
    SLUG=$(echo "$IDENT" | tr '[:upper:]' '[:lower:]' | tr '/.:-' '____')
    PID="doi_${SLUG}"
    ;;
esac

if [ -d "$STORE_ROOT/$PID" ]; then
  echo "[corpus] Already in canonical store: ~/Projects/corpus/$PID/" >&2
  echo "[corpus]   Use: corpus show $PID  (or corpus_lookup MCP tool) instead of re-fetching." >&2
else
  echo "[corpus] About to fetch $IDENT — local store doesn't have it yet (corpus_lookup $IDENT)." >&2
  echo "[corpus]   After fetch, prefer: corpus ingest --pdf <path> --doi $IDENT  (canonical store)." >&2
fi

# Telemetry — log the trigger for ROI measurement
~/Projects/skills/hooks/hook-trigger-log.sh "corpus-remind" "advise" "fetch" 2>/dev/null || true

exit 0
