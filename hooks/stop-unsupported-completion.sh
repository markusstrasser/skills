#!/usr/bin/env bash
# stop-unsupported-completion.sh — Shadow-mode detector for UNSUPPORTED_OUTCOME_CLAIM.
# Targets Failure Mode 25 manifestation 1 (belief 6: FAE/outcome bias) from
# agent-failure-modes.md. Covers ONLY the unsupported-outcome-claim branch;
# EXTERNAL_ATTRIBUTION_WITHOUT_TRACE and DISPOSITION_OVER_CONTEXT remain
# session-analyst analytical labels, not enforced by this hook.
#
# Predicate (lexical-only, last-assistant-message scope):
#   success_hit  := last message contains a success verb (fixed/done/works/...)
#   evidence_hit := last message contains an evidence marker (pytest/stdout/
#                   exit code/verified/tested/trace/output:/...)
#   would_fire   := success_hit >= 1 AND evidence_hit == 0
#
# LEXICAL-ONLY: this hook does NOT inspect tool trace output or recent command
# history. It's a text-classifier over the final assistant message. A session
# that produced green pytest output but whose final narration is a bare
# "Fixed. Done." will still fire — that is intended, because the bias is the
# failure to cite evidence in the final summary, not the absence of evidence
# upstream.
#
# SHADOW MODE: logs would-fire events to ~/.claude/unsupported-completion-shadow.jsonl
# but never returns advisory output. Internal hook errors logged separately to
# ~/.claude/unsupported-completion-errors.jsonl so silent failures are detectable.
# Promote to advisory after 14-day precision check shows >=60% precision on sampled
# fires AND recall floor of >=50% of eligible cases (per model-review
# .model-review/2026-04-11-bias-plan-close-89878c/ findings 6, 8, 15).
#
# Precedent: stop-progress-check.sh — same shadow-mode pattern.

trap 'exit 0' ERR

INPUT=$(cat)

# Redirect Python stderr to a dedicated error log so parsing/runtime failures
# are detectable during the 14-day shadow period (was: 2>/dev/null which
# silently hides all errors and corrupts precision measurement).
ERR_LOG="${HOME}/.claude/unsupported-completion-errors.jsonl"
mkdir -p "$(dirname "$ERR_LOG")" 2>/dev/null || true

python3 -c '
import sys, json, os, re, traceback
from datetime import datetime, timezone

SHADOW_LOG = os.path.expanduser("~/.claude/unsupported-completion-shadow.jsonl")
ERR_LOG = os.path.expanduser("~/.claude/unsupported-completion-errors.jsonl")

# Success-claim verbs (lexical — matches the language people actually use)
SUCCESS_PATTERNS = [
    r"\bfix(ed|es)?\b",
    r"\bdone\b",
    r"\bwork(s|ing|ed)?\b",
    r"\bpass(es|ed|ing)?\b",
    r"\bcomplet(e|ed|es)\b",
    r"\bdeploy(ed|s)?\b",
    r"\bresolv(e|ed|es)\b",
    r"\bsucce(ss|ed|eded|eds)\b",
    r"\blanded\b",
    r"\bshipped\b",
]

# Evidence markers — structural indicators of cited tool output.
# Deliberately NOT including weak hedging words (should/would/likely/ran);
# those are not evidence of a test run and their inclusion created false
# negatives. See .model-review/2026-04-11-bias-plan-close-89878c/ findings 7, 11.
EVIDENCE_PATTERNS = [
    r"\bpytest\b",
    r"\bstdout\b",
    r"\bstderr\b",
    r"\bexit code\b",
    r"\btrace\b",
    r"\boutput[:\s]",
    r"\bverified\b",
    r"\btested\b",
    r"\btest output\b",
    r"\bevidence[:\s]",
    r"\bcitation\b",
    r"\bneeds verification\b",
    r"\bgreen\b",
    r"\bred\b",
    r"\bfail(ed|ing|ure)?\s",  # self-diagnosing a failure is evidence-like
    r"\bassert",
    r"\[PASS\]",
    r"\[FAIL\]",
    r"[0-9]+\s*(pass|fail|tests?)",
]

# Pre-action prediction markers — separate from evidence. Indicates the
# agent framed the outcome in terms of a prior hypothesis, which is the
# temporal structure outcome bias lacks. Presence of any one suppresses.
PREDICTION_PATTERNS = [
    r"\bexpected\b",
    r"\bhypothesiz(e|ed|es)\b",
    r"\bpredict(ed|s|ion)?\b",
    r"\bbefore\b",
    r"\bpreviously\b",
    r"\bhypothesis\b",
]

def log_error(stage, exc):
    try:
        with open(ERR_LOG, "a") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stage": stage,
                "error": repr(exc),
                "trace": traceback.format_exc()[-800:],
            }) + "\n")
    except Exception:
        pass

try:
    raw = sys.stdin.read()
    data = json.loads(raw)
except Exception as e:
    log_error("input_parse", e)
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
            for entry in reversed(lines):
                if entry.get("role") == "assistant" or entry.get("type") == "assistant":
                    last_msg = (entry.get("content") or entry.get("message", {}).get("content", "")) or ""
                    if isinstance(last_msg, list):
                        last_msg = " ".join(
                            block.get("text", "") for block in last_msg
                            if isinstance(block, dict)
                        )
                    break
        except Exception as e:
            log_error("transcript_fallback", e)

if not last_msg:
    sys.exit(0)

msg = last_msg.lower()

try:
    success_hits = sum(1 for p in SUCCESS_PATTERNS if re.search(p, msg))
    if success_hits == 0:
        sys.exit(0)

    evidence_hits = sum(1 for p in EVIDENCE_PATTERNS if re.search(p, msg))
    prediction_hits = sum(1 for p in PREDICTION_PATTERNS if re.search(p, msg))

    # Would-fire condition: claims success, no evidence markers, no prediction.
    # Threshold lowered to success_hits >= 1 per plan-close review findings 1, 3.
    # Terse unsupported claims ("Fixed.", "Done.") were previously excluded by
    # success_hits >= 2 AND len(msg) < 20 — both removed.
    would_fire = success_hits >= 1 and evidence_hits == 0 and prediction_hits == 0

    session_id = os.environ.get("CLAUDE_SESSION_ID", "") or data.get("session_id", "")
    cwd = os.environ.get("CLAUDE_CWD", "") or data.get("cwd", "")
    project = os.path.basename(cwd) if cwd else "unknown"

    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": "unsupported_completion_shadow",
        "session": session_id,
        "project": project,
        "success_hits": success_hits,
        "evidence_hits": evidence_hits,
        "prediction_hits": prediction_hits,
        "would_fire": would_fire,
        "msg_len": len(last_msg),
        "msg_tail": last_msg[-400:] if would_fire else "",
    }
    try:
        with open(SHADOW_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        log_error("shadow_write", e)
except Exception as e:
    log_error("scan", e)
    sys.exit(0)

# Shadow mode: never output advisory, always exit 0
' <<< "$INPUT" 2>>"$ERR_LOG"

exit 0
