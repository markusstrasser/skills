"""Keep hook tests off the live telemetry files.

Hooks run by the tests log their triggers through hook-trigger-log.sh. Without this, every
suite run appended its fixtures to ~/.claude/hook-triggers.jsonl, and the per-hook volumes
read from that file counted them (research-skill-gate: every "block" row up to 2026-11-23
was one of four test snippets).
"""

import os
import tempfile

_dir = tempfile.mkdtemp(prefix="hook-tests-")
os.environ.setdefault("HOOK_TRIGGER_LOG", os.path.join(_dir, "hook-triggers.jsonl"))
os.environ.setdefault("RESEARCH_SKILL_GATE_SHADOW_LOG", os.path.join(_dir, "research-skill-gate-shadow.jsonl"))
