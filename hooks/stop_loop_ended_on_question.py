#!/usr/bin/env python3
"""stop_loop_ended_on_question.py — SHADOW detector: autonomous loop ended its turn on a question.

Backs the rule `~/.claude/rules/wakeup-cadence.md` → "Escalation is a file, never a block":
an autonomous loop must NEVER yield on a question to the human (= AutoResearch "ready means
execute"; = our measured `over_caution` blindspot cluster). It should append the ask to the
loop-root `HUMAN.md` and keep going instead.

Architecture (P1: a rule alone is ~0% reliable — this is the hook that backs it). Precedent +
pattern cloned from `stop-unsupported-completion.sh`: a lexical predicate over the FINAL assistant
message, SHADOW MODE first (log would-fire, never act), promote to advisory only after a 14-day
precision check.

THE CONDITIONAL (why this can't fire in interactive sessions): a human session ending on a
question is CORRECT — the gate is `session_crons` non-empty, the documented Stop-input signal that
a `/loop` / ScheduleWakeup / CronCreate is armed (verified: hutter's Dreamer runs `/loop /dream`,
so its sessions carry session_crons; an interactive session carries none). We log the gate signals
on EVERY question-ending so the 14-day review can confirm session_crons cleanly separates
loop-from-interactive before any promotion — measure the discriminator, don't trust it blind.

Stop-input fields used (verified present in our Claude Code version — multiple live hooks read them):
  last_assistant_message, session_crons[], permission_mode, stop_hook_active, transcript_path,
  background_tasks[]. last_assistant_message is primary; transcript_path is the fallback.

SHADOW: appends would-fire rows to ~/.claude/loop-ended-on-question-shadow.jsonl, returns nothing.
Promote to advisory (`additionalContext`: "you ended on a question — append it to HUMAN.md and
continue") after >=60% precision on sampled fires. NEVER promote straight to `decision: block`
without the precision gate — forcing continuation on a false positive is the costly failure.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

SHADOW_LOG = os.path.expanduser("~/.claude/loop-ended-on-question-shadow.jsonl")
ERR_LOG = os.path.expanduser("~/.claude/loop-ended-on-question-errors.jsonl")

# Trailing markdown/quote wrappers to peel before testing the final char (so "**…?**" still reads
# as a question). Backtick excluded on purpose: a trailing ` means inline code / a fence, not prose.
_TRAILING_WRAP = "*_\"' \t)]}>"


def _last_assistant_from_transcript(path: str) -> str:
    """Fallback when last_assistant_message is absent: last assistant text block in the JSONL."""
    if not path:
        return ""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return ""
    last = ""
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "assistant":
                continue
            msg = obj.get("message", {})
            content = msg.get("content", "")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = " ".join(
                    c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
                )
            else:
                text = ""
            if text.strip():
                last = text
    return last


def ended_on_question(text: str) -> bool:
    """Lexical v0 (shadow): does the final meaningful sentence address a question to the user?

    Loose on purpose — shadow LOGS, never acts, so the 14-day review tightens against real tails.
    Excludes: empty; ends in a code fence (```); the trailing `?` sitting inside an open code fence.
    """
    if not text or not text.strip():
        return False
    t = text.rstrip()
    # Ended with a closing/opening code fence → not a prose question to the user.
    if t.endswith("```"):
        return False
    # If an odd number of ``` fences appear, the tail is inside a code block → ignore.
    if t.count("```") % 2 == 1:
        return False
    # Peel trailing wrapper punctuation/emphasis, then test the final char.
    stripped = t
    while stripped and stripped[-1] in _TRAILING_WRAP:
        stripped = stripped[:-1]
    return stripped.endswith("?")


def evaluate(inp: dict) -> dict:
    """Pure: map a Stop-hook input dict → a shadow record (no I/O). Importable for tests."""
    crons = inp.get("session_crons") or []
    crons_len = len(crons) if isinstance(crons, list) else 0
    msg = inp.get("last_assistant_message") or ""
    if not msg:
        msg = _last_assistant_from_transcript(inp.get("transcript_path", ""))
    q = ended_on_question(msg)
    tail = msg.rstrip()[-200:] if msg else ""
    bg = inp.get("background_tasks") or []
    return {
        "ended_on_question": q,
        "session_crons_len": crons_len,
        "permission_mode": inp.get("permission_mode"),
        "stop_hook_active": bool(inp.get("stop_hook_active")),
        "has_background_tasks": bool(bg),
        "would_fire": bool(q and crons_len > 0 and not inp.get("stop_hook_active")),
        "last_msg_tail": tail,
    }


def _log(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(obj) + "\n")


def main() -> int:
    try:
        inp = json.load(sys.stdin)
    except Exception as exc:  # noqa: BLE001 — never break the Stop event
        try:
            _log(ERR_LOG, {"ts": datetime.now(timezone.utc).isoformat(), "error": f"stdin: {exc}"})
        except Exception:
            pass
        return 0
    try:
        rec = evaluate(inp)
        # Shadow: record only question-endings (bounded), with the gate signals, so the review can
        # confirm session_crons separates loop-from-interactive before promotion.
        if rec["ended_on_question"]:
            rec["ts"] = datetime.now(timezone.utc).isoformat()
            rec["session_id"] = inp.get("session_id")
            _log(SHADOW_LOG, rec)
    except Exception as exc:  # noqa: BLE001
        try:
            _log(ERR_LOG, {"ts": datetime.now(timezone.utc).isoformat(), "error": f"eval: {exc}"})
        except Exception:
            pass
    return 0  # SHADOW: never act.


if __name__ == "__main__":
    sys.exit(main())
