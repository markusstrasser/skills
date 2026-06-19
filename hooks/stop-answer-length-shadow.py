#!/usr/bin/env python3
"""stop-answer-length-shadow.py — SHADOW measurement: per-turn answer length + decision-first shape.

Backs `.claude/rules/canonical-answer-format.md` (dump C6/C7): replies should be SHORT and lead
with the decision, not narrate process. This is the measure-before-enforce instrument (Constitution
P3): it LOGS the final assistant message's length + a cheap decision-first heuristic on every
substantive Stop, and does NOT nudge. After a precision window, promote to an advisory
(`additionalContext`: "lead with the verdict; this ran long") — never a hard block (format
false-positives are high-friction).

Why a hook, not just the rule: "be shorter / decision-first" is the exact instruction-class that is
~0% reliable (P1). The rule sets intent; this measures whether the intent holds, so promotion runs
on real data, not vibes.

Stop-input fields (verified present — read by sibling stop_loop_ended_on_question.py):
  last_assistant_message (primary), transcript_path (fallback), session_id, stop_hook_active.

SHADOW: appends rows to ~/.claude/answer-length-shadow.jsonl, returns nothing. Fails OPEN.
Agent-infra-first: wired ONLY in agent-infra/.claude/settings.json until the window justifies global.
"""
# Gov-ID: hook:answer-length-shadow
# goal: measure per-turn reply length + decision-first shape so the canonical-answer-format rule
#       can graduate from instruction to advisory on real data (dump C6/C7)
# verifier: null  # semantic (is the reply actually decision-first?) — heuristic logged for review
# blast_radius: local  # agent-infra-only wiring; shadow (log-only), fails open
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

SHADOW_LOG = os.path.expanduser("~/.claude/answer-length-shadow.jsonl")

# Only measure substantive turns — a one-line ack carries no format signal.
MIN_CHARS = 800

# Process-narration openers: a reply that LEADS with one of these is not decision-first.
# Lexical heuristic only (logged for review, not enforced) — semantic call resists a clean predicate.
_NARRATION_OPENER = re.compile(
    r"^(let me\b|first(,| i| ,)|i'?ll\b|i'?m going to\b|i am going to\b|i'?m (now )?going\b|"
    r"now (i'?ll|let me|i am)\b|to (start|begin)\b|okay,? (let me|i'?ll)\b|"
    r"i (want|need) to (make sure|check|verify|understand)\b|alright,? (let me|i'?ll)\b)",
    re.I,
)


def _last_assistant_from_transcript(path: str) -> str:
    if not path:
        return ""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return ""
    last = ""
    try:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                msg = obj.get("message") or {}
                if obj.get("type") == "assistant" or msg.get("role") == "assistant":
                    content = msg.get("content") if isinstance(msg, dict) else None
                    if isinstance(content, list):
                        txt = "".join(
                            b.get("text", "") for b in content
                            if isinstance(b, dict) and b.get("type") == "text"
                        )
                        if txt.strip():
                            last = txt
                    elif isinstance(content, str) and content.strip():
                        last = content
    except Exception:
        return last
    return last


def _first_prose_line(text: str) -> str:
    """First non-empty, non-fence line — what the reader's eye lands on."""
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("```"):
            continue
        return s
    return ""


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        return
    env = json.loads(raw)
    if env.get("stop_hook_active"):
        return
    msg = env.get("last_assistant_message") or ""
    if not msg:
        msg = _last_assistant_from_transcript(env.get("transcript_path") or "")
    msg = (msg or "").strip()
    if len(msg) < MIN_CHARS:
        return

    first = _first_prose_line(msg)
    narrates = bool(_NARRATION_OPENER.match(first))
    # Cheap shape signals for the review window.
    has_table = "|" in msg and re.search(r"\n\s*\|.*\|", msg) is not None
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": env.get("session_id") or "",
        "cwd": env.get("cwd") or "",
        "len_chars": len(msg),
        "n_lines": msg.count("\n") + 1,
        "first_line": first[:120],
        "narrates_open": narrates,   # would-flag: leads with process narration, not a decision
        "has_table": has_table,
    }
    try:
        with open(SHADOW_LOG, "a") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
