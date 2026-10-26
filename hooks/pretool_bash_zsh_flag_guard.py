#!/usr/bin/env python3
"""pretool_bash_zsh_flag_guard.py — block zsh parameter-expansion flag groups (`${(f)x}`,
`"${(j:,:)arr}"`) before Claude Code's own command parser sees them.

Claude Code (2.1.310) cannot statically parse a `${(...)name}` flag group, so it asks for
explicit approval even under bypassPermissions: "This command could not be checked for
dangerous rm operations: the shell may read it differently than it was parsed. This
requires explicit approval." A headless run is denied. An in-process background teammate
has nobody to answer the prompt, so its call waits with no process behind it until someone
stops the lane (lane-stall-watch reports STALLED_TOOL).

Evidence: genomics lane negatives-panels, 2026-10-27. Two Bash calls (05:27:58 and 05:41:47
JST) never ran; they were the lane's only commands using `${(f)nodes}`, while all 13 of its
calls using `${=...}` returned. Probes the same morning (`claude -p --permission-mode
bypassPermissions`, haiku): `${(f)x}` and `"${(j:,:)arr}"` were denied with the text above;
`${=x}` and a quoted-delimiter heredoc body holding `${(f)x}` ran.

Contract (sidecar convention): `offending_expansion(cmd)` returns the first flag group the
shell would expand, or None; `reason(hit)` is the block text. Literal text (single quotes,
$'...', comments, quoted-delimiter heredoc bodies) is masked by lib_bash_cmd_strip.live_mask,
so writing such an expression into a file through `cat <<'EOF'` stays allowed.
"""

from __future__ import annotations

import re

from lib_bash_cmd_strip import live_mask

_FLAG_GROUP = re.compile(r"\$\{\([^)\n]*\)")


def offending_expansion(cmd: str) -> str | None:
    if "${(" not in cmd:
        return None
    match = _FLAG_GROUP.search(live_mask(cmd))
    if match is None:
        return None
    close = cmd.find("}", match.end())
    end = match.end() if close < 0 else close + 1
    return cmd[match.start() : min(end, match.start() + 60)]


def reason(hit: str) -> str:
    return (
        f"BLOCKED: zsh expansion flag {hit}. Claude Code cannot parse ${{(...)...}} flag groups and "
        "asks for explicit approval even in bypass mode; a background agent cannot answer, so the "
        "call hangs (a headless run is denied).\n"
        "Rewrite without the flag group:\n"
        "  lines as arguments:  tr '\\n' '\\0' < FILE | xargs -0 CMD\n"
        "                       (or: while IFS= read -r line; do ...; done < FILE)\n"
        "  split words:         ${=var}\n"
        "  join an array:       printf '%s,' \"${arr[@]}\"\n"
    )
