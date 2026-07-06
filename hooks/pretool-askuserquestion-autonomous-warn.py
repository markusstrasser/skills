#!/usr/bin/env python3
# Gov-ID: hook:askuserquestion-autonomous-warn
# goal: a blocking AskUserQuestion during an autonomous/overnight run halts the WHOLE run until the
#       human returns (cost ~8h once, genomics 1cf836e3) — the over-caution anti-pattern wearing a
#       menu. Warn (never block) when an autonomous-run marker is present, nudging to /decide or HUMAN.md.
# verifier: skills/hooks/test_pretool_askuserquestion_autonomous_warn.py
# blast_radius: shared
"""PreToolUse(AskUserQuestion) advisory: warn when fired during an autonomous run. WARN only.

Autonomous-run signal (reuses existing runtime markers — invents none):
  - `.claude/goal-run` present AND not superseded by `.claude/goal-done` / `.claude/goal-blocked`
    (the overnight /goal opt-in marker, set by `just goal-night`), OR
  - `.claude/loop-enforce-no-question-stop` present (the operator's per-loop no-question opt-in), OR
  - a non-empty `session_crons` in the envelope (a /loop / ScheduleWakeup / Cron is armed), if the
    PreToolUse envelope carries it.

Warn, not block: a genuine rare autonomous need (confirm an irreversible action) still proceeds. The
warn is almost always correct in an autonomous run, so it's strictly better at negligible FP cost.
Fail-open on any error. Reversibility: delete the hook + registration.
"""
from __future__ import annotations

import json
import os
import sys

_WARN = (
    "[autonomous-run] AskUserQuestion during an autonomous/loop run BLOCKS the entire run until the "
    "human returns (cost ~8h once). Prefer: `/decide` (cross-model, no human needed) for a real fork, "
    "or append the ask to HUMAN.md and continue other fronts. Reserve AskUserQuestion for interactive "
    "sessions. If this IS a rare autonomous confirmation of an irreversible action, proceed."
)


def _project_dir(env: dict) -> str:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or env.get("cwd") or ""
    return os.path.expanduser(root) if root else ""


def is_autonomous(env: dict) -> bool:
    root = _project_dir(env)
    if root:
        cdir = os.path.join(root, ".claude")
        goal_run = os.path.exists(os.path.join(cdir, "goal-run"))
        goal_over = os.path.exists(os.path.join(cdir, "goal-done")) or os.path.exists(
            os.path.join(cdir, "goal-blocked")
        )
        if goal_run and not goal_over:
            return True
        if os.path.exists(os.path.join(cdir, "loop-enforce-no-question-stop")):
            return True
    crons = env.get("session_crons")
    if isinstance(crons, list) and len(crons) > 0:
        return True
    return False


def main() -> None:
    try:
        env = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # fail open
    if env.get("tool_name") != "AskUserQuestion":
        sys.exit(0)
    if not is_autonomous(env):
        sys.exit(0)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": _WARN}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
