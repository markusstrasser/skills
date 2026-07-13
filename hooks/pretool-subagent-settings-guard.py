#!/usr/bin/env python3
"""pretool-subagent-settings-guard.py — subagents may not rewire live hook config.

PreToolUse (Write|Edit|MultiEdit). Blocks a SUBAGENT (CLAUDE_AGENT_ID set)
writing to any live Claude settings file (~/.claude/settings.json or any
<repo>/.claude/settings[.local].json). Main sessions are unaffected.

Why: 2026-07-13, twice in one day, hook-consolidation subagents swapped the
live settings.json to their new (then-unverified) dispatcher and went idle
without reporting — every tool call in every repo ran unverified gate code
until the parent discovered it by disk inspection. The dispatch contract is
"build + test, parent reviews parity, PARENT applies the wiring"; this makes
that contract architectural instead of prose (improvement-log 2026-07-13,
SUBAGENT-REWIRED-LIVE-CONFIG, 2nd occurrence -> hook per critique-to-hooks).

Known gap (accepted): a subagent editing settings.json via Bash (redirect,
python -c) bypasses this Write|Edit guard. Both observed incidents used the
Edit/Write tools; widen to the Bash dispatcher's gate list if the Bash
vector is ever observed.

Fail-open on any internal error.
"""

import json
import os
import re
import sys

# Live-wiring files only. settings.local.json also wires hooks; scratch
# copies, snapshots, and fixtures (e.g. _*_snapshot.json) do not match.
_SETTINGS_RE = re.compile(r"(^|/)\.claude/settings(\.local)?\.json$")


def main() -> int:
    if not os.environ.get("CLAUDE_AGENT_ID"):
        return 0  # main session: not our concern

    try:
        envelope = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(envelope, dict):
        return 0

    tool_input = envelope.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    fpath = tool_input.get("file_path") or ""
    if not isinstance(fpath, str) or not fpath:
        return 0

    if _SETTINGS_RE.search(fpath):
        print(
            "BLOCKED: subagents don't rewire live hook config. Leave "
            f"{os.path.basename(fpath)} untouched; return the exact proposed "
            "settings edit (old entries -> new entry) in your report instead — "
            "the parent applies the wiring AFTER verifying your parity tests. "
            "(Two live-config swaps by subagents on 2026-07-13 ran unverified "
            "gate code on every tool call; this guard is that incident's fix.)",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
