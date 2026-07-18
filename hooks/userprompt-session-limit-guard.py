#!/usr/bin/env python3
"""userprompt-session-limit-guard.py — nudge the resume protocol when a
session/spend-limit kill string surfaces in a prompt (a dead-lane failureReason
pasted back into the parent's context). UserPromptSubmit hook, advisory only.

Gov-ID: hook:session-limit-guard | verifier: test_userprompt_session_limit_guard.py
goal: wakeup-cadence.md "Session-limit kills carry their own reset clock" — the
reset time is IN the string; self-arm ONE ScheduleWakeup at reset+2-5min instead
of polling/asking. Spend-limit kills print NO clock — arm a periodic resume-probe
instead and keep grading on-disk artifacts meanwhile.
"""
import json
import re
import sys

SESSION_LIMIT_RE = re.compile(
    r"you'?ve hit your session limit.*?resets?\s+([0-9]{1,2}:[0-9]{2}\s*[ap]m(?:\s*\([^)]*\))?)",
    re.I | re.S,
)
SPEND_LIMIT_RE = re.compile(r"monthly spend limit", re.I)


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        return
    prompt = (json.loads(raw).get("prompt") or "")
    if not prompt:
        return

    m = SESSION_LIMIT_RE.search(prompt)
    if m:
        ctx = (
            f"SESSION-LIMIT KILL detected. Parse: reset={m.group(1).strip()}. Self-arm ONE "
            "ScheduleWakeup at reset+2-5min to redispatch the dead lane (wakeup-cadence.md); "
            "do NOT poll before it, do NOT ask the operator for the clock — it's already printed."
        )
    elif SPEND_LIMIT_RE.search(prompt):
        ctx = (
            "MONTHLY-SPEND-LIMIT KILL detected — no reset clock printed (operator account "
            "action, unknown time). Do NOT sit idle: arm ONE periodic ScheduleWakeup "
            "(1800-3600s) whose tick sends a single cheap resume-probe to one dead lane; on "
            "success, resume the fleet and report. Meanwhile grade on-disk artifacts and close "
            "what's gradeable inline — an account-dead fleet is not an idle parent."
        )
    else:
        return

    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
