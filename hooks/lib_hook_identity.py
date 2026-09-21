"""Who is calling this hook: agent and session identity, read from the hook envelope.

Claude Code passes identity in the ENVELOPE, not the hook's environment. Probed 2026-09-21
(pretool-universal-dispatch.py probe_envelope): a subagent's tool calls carry
`agent_id`/`agent_type` and the main loop's do not; every call carries `session_id`. The hook
process environment has CLAUDE_CODE_SESSION_ID but neither CLAUDE_AGENT_ID nor
CLAUDE_SESSION_ID (only the Bash tool's shell gets CLAUDE_SESSION_ID), and in-process subagents
share the CLI's PID. Hooks that tested those variables or keyed state on the parent PID alone
saw every sibling agent as one caller, and every session as "default".

Bash twin: lib_hook_identity.sh. test_hook_identity.py holds the two together.
"""

import os
import re


def agent_id(envelope) -> str:
    """Filename-safe id of the calling subagent; "" for the main loop."""
    raw = envelope.get("agent_id") if isinstance(envelope, dict) else None
    return re.sub(r"[^A-Za-z0-9]", "", str(raw or ""))[:32]


def session_id(envelope) -> str:
    """Filename-safe session id; "" if neither the envelope nor the environment has one."""
    raw = envelope.get("session_id") if isinstance(envelope, dict) else None
    raw = raw or os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
    return re.sub(r"[^A-Za-z0-9-]", "", str(raw or ""))[:64]


def owner(envelope, ppid=None) -> str:
    """Suffix for per-caller state files: "<agent>-<ppid>" or "<ppid>".

    The PID stays last because reap_stale_trackers.py reads the owner PID from there.
    """
    pid = os.getppid() if ppid is None else ppid
    agent = agent_id(envelope)
    return f"{agent}-{pid}" if agent else str(pid)
