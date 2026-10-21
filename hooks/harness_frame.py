"""harness_frame.py — is this UserPromptSubmit prompt a harness-injected frame?

One definition: loads agent-infra's src/agentlogs/authorship.py by path (same rule the
transcript miners use). Fails open: a missing or broken file means "not a frame".
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

AUTHORSHIP = Path(
    os.environ.get(
        "AGENTLOGS_AUTHORSHIP_PATH",
        str(Path.home() / "Projects/agent-infra/src/agentlogs/authorship.py"),
    )
)
_MOD = None


def _authorship():
    global _MOD
    if _MOD is None:
        spec = importlib.util.spec_from_file_location("agentlogs_authorship", AUTHORSHIP)
        if spec is None or spec.loader is None:
            raise ImportError(AUTHORSHIP)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MOD = mod
    return _MOD


def is_harness_frame(prompt: str) -> bool:
    head = (prompt or "").lstrip()
    if head.startswith("<task-notification>"):
        return True
    try:
        return bool(_authorship().is_claude_harness_text(head))
    except Exception:
        return False
