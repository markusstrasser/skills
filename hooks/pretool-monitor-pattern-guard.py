#!/usr/bin/env python3
"""PreToolUse guard for Monitor commands: mechanical, high-precision slice of the
watcher arm-time PAIR rule (~/.claude/rules/wakeup-cadence.md).

Born 2026-07-13 (arc-agi session b49d6a14): the prose PAIR rule was violated twice in one
session by the SAME author who had re-read it that day —
  1. a grep pattern `429` matched microsecond timestamps (`15:38:06.429275`), firing a false
     rate-limit alarm loop;
  2. `pgrep -f "a\\|b"` — `\\|` is a LITERAL pipe in ERE, so the alternation never matched and
     the liveness check reported a healthy process tree as dead.
Pair-rule: a recurring manually-flagged discipline failure gets a hook, not another prose note.

Scope (deliberately narrow — zero-false-positive slices only; the full PAIR check stays prose):
  A. `\\|` inside a pgrep/grep/egrep pattern argument → ERE literal-pipe bug. BLOCK (exit 2):
     the fix is one character and the broken form is never intended.
  B. a grep/pgrep pattern that is ONLY a short bare number (2-4 digits) → timestamp/pid/port
     collision risk. WARN (additionalContext): legitimate uses exist, so advisory only.

Non-Monitor tools pass through untouched. Fails open on any parse error (guards must never
brick the harness).
"""
import json
import re
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Monitor":
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return 0

    # A: backslash-pipe inside a quoted pgrep/grep pattern → literal '|' in ERE, never alternation.
    lit_pipe = re.search(r"""(?:pgrep|grep|egrep)\s+(?:--?[\w-]+(?:=\S+)?\s+)*["'][^"']*\\\|[^"']*["']""", cmd)
    if lit_pipe:
        print(
            "BLOCKED: Monitor command uses `\\|` inside a pgrep/grep pattern — in ERE that is a "
            "LITERAL pipe character, not alternation, so the pattern can never match what you "
            f"intend (matched: {lit_pipe.group(0)[:120]!r}). Use a plain `|` inside the quoted "
            "ERE (pgrep -f \"a|b\"), or two separate checks. This exact bug reported a healthy "
            "process tree as dead on 2026-07-13. Also run the PAIR check before re-arming: "
            "positive-control the pattern against a live/synthetic line AND zero-match it "
            "against the current log (~/.claude/rules/wakeup-cadence.md).",
            file=sys.stderr,
        )
        return 2

    # B: grep for a short bare number → timestamp/PID collision (the `429` incident). Advisory.
    bare_num = re.search(r"""grep\s+(?:--?[\w-]+(?:=\S+)?\s+)*["'](\d{2,4})["']""", cmd)
    if bare_num:
        n = bare_num.group(1)
        print(
            json.dumps(
                {
                    "additionalContext": (
                        f"MONITOR-PATTERN WARNING (advisory): grep pattern is the bare number "
                        f"'{n}' — short numerics match timestamps/PIDs/ports (a grep for '429' "
                        f"matched '15:38:06.429275' and fired a false rate-limit alarm, "
                        f"2026-07-13). Anchor it (e.g. 'status={n}' or 'HTTP {n}') and run the "
                        f"arm-time PAIR check: synthetic positive + current-log zero-match."
                    )
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
