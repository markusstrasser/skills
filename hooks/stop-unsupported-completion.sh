#!/usr/bin/env bash
# stop-unsupported-completion.sh — Shadow-mode detector for UNSUPPORTED_OUTCOME_CLAIM.
# Targets Failure Mode 25 (belief 6: FAE/outcome bias) from agent-failure-modes.md.
# Fires at session end. Flags final assistant messages that claim success
# ("fixed", "done", "works", "passes", "complete", "deployed") without recent
# tool-trace evidence of a test run, green output, or pre-action prediction.
#
# SHADOW MODE: logs would-fire events to ~/.claude/unsupported-completion-shadow.jsonl
# but never returns advisory output. Enable after 14-day precision check shows
# >=60% precision on sampled fires (per model-review 2026-04-11 findings 3, 14).
#
# Precedent: stop-progress-check.sh — same shadow-mode pattern.

trap 'exit 0' ERR

INPUT=$(cat)

python3 -c '
import sys, json, os, re, subprocess
from datetime import datetime, timezone

SHADOW_LOG = os.path.expanduser("~/.claude/unsupported-completion-shadow.jsonl")
TRIGGER_LOG = os.path.expanduser("~/.claude/hook-triggers.jsonl")

# Success-claim verbs (lexical — matches the language people actually use)
SUCCESS_PATTERNS = [
    r"\bfix(ed|es)?\b",
    r"\bdone\b",
    r"\bwork(s|ing|ed)?\b",
    r"\bpass(es|ed|ing)?\b",
    r"\bcomplet(e|ed|es)\b",
    r"\bdeploy(ed|s)?\b",
    r"\bresolv(e|ed|es)\b",
    r"\bsucce(ss|eded|eds)\b",
    r"\blanded\b",
    r"\bshipped\b",
]
# Pre-action prediction / hedging language (the thing outcome-bias lacks)
PREDICTION_PATTERNS = [
    r"\bexpected\b",
    r"\bhypothesiz(e|ed|es)\b",
    r"\bassum(e|ed|es|ption)\b",
    r"\bpredict(ed|s|ion)?\b",
    r"\bshould\b",
    r"\bwould\b",
    r"\bbefore\b",
    r"\bpreviously\b",
    r"\blikely\b",
    r"\bneeds verification\b",
    r"\bcitation\b",
    r"\bevidence[:\s]",
    r"\bverified\b",
    r"\btested\b",
    r"\bpytest\b",
    r"\bjust test\b",
    r"\bran\b",
    r"\boutput[:\s]",
]

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("stop_hook_active", False):
    sys.exit(0)

# Get the last assistant message if available
last_msg = data.get("last_assistant_message", "") or ""
# Fallback: try to read from transcript path
if not last_msg:
    tpath = data.get("transcript_path", "")
    if tpath and os.path.isfile(tpath):
        try:
            with open(tpath) as f:
                lines = [json.loads(l) for l in f if l.strip()]
            # Last assistant entry
            for entry in reversed(lines):
                if entry.get("role") == "assistant" or entry.get("type") == "assistant":
                    last_msg = (entry.get("content") or entry.get("message", {}).get("content", "")) or ""
                    if isinstance(last_msg, list):
                        last_msg = " ".join(
                            block.get("text", "") for block in last_msg
                            if isinstance(block, dict)
                        )
                    break
        except Exception:
            pass

if not last_msg or len(last_msg) < 20:
    sys.exit(0)

# Lowercase for pattern matching
msg = last_msg.lower()

# Count success claims
success_hits = sum(1 for p in SUCCESS_PATTERNS if re.search(p, msg))
if success_hits == 0:
    sys.exit(0)

# Count prediction/hedging/evidence language
prediction_hits = sum(1 for p in PREDICTION_PATTERNS if re.search(p, msg))

# Would-fire condition: claims success but lacks hedging/prediction/evidence language
would_fire = success_hits >= 2 and prediction_hits == 0

# Log all eligible sessions (success_hits>=1) for precision analysis
session_id = os.environ.get("CLAUDE_SESSION_ID", "") or data.get("session_id", "")
cwd = os.environ.get("CLAUDE_CWD", "") or data.get("cwd", "")
project = os.path.basename(cwd) if cwd else "unknown"

ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
entry = {
    "ts": ts,
    "event": "unsupported_completion_shadow",
    "session": session_id,
    "project": project,
    "success_hits": success_hits,
    "prediction_hits": prediction_hits,
    "would_fire": would_fire,
    "msg_len": len(last_msg),
    "msg_tail": last_msg[-400:] if would_fire else "",
}
try:
    with open(SHADOW_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
except OSError:
    pass

# Shadow mode: never output advisory, always exit 0
' <<< "$INPUT" 2>/dev/null

exit 0
