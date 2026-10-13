#!/usr/bin/env python3
# Gov-ID: hook:stop-idle-lever-sweep
# goal: catch idle Stop wind-downs that skip cheap reversible probes (over_caution)
# verifier: --selftest
# blast_radius: shared (Stop; default SHADOW — measure before advisory)
"""stop-idle-lever-sweep.py — Stop: when last turns are summary-only, surface levers.

Blindspot CONVERT (observe 2026-07-20): operator "Why wait / Anything else / did
you stop on purpose?" — sessions end with no Bash/Agent/Skill in the last 2
assistant turns while cheap probes remain. Instructions/MEMORY failed;
architecture = Stop checklist.

Modes (env STOP_LEVER_SWEEP_MODE):
  shadow    (default) — log would-fire; silent to model
  advisory  — additionalContext with lever checklist
  enforce   — decision:block with same checklist (not licensed yet)

Scope: cwd under arc-agi, OR env RAISE_AUTONOMY_LEVER_SWEEP=1 (fleet trial).
Fail-open. Skip when stop_hook_active or headless /loop slug present.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

MODE = os.environ.get("STOP_LEVER_SWEEP_MODE", "shadow").strip().lower()
CHECKLIST = Path.home() / "Projects" / "agent-infra" / "scripts" / "stop_lever_sweep.py"
TOOL_KINDS = {"Bash", "Shell", "Agent", "Skill", "Task"}


def _in_scope(cwd: str) -> bool:
    if os.environ.get("RAISE_AUTONOMY_LEVER_SWEEP", "").strip() in ("1", "true", "yes"):
        return True
    if not cwd:
        return False
    norm = str(Path(cwd).expanduser().resolve()).replace("\\", "/")
    return "/Projects/arc-agi" in norm or norm.rstrip("/").endswith("/arc-agi")


def _headless(env: dict) -> bool:
    for key in ("CLAUDE_CODE_ENTRYPOINT", "AGENT_INFRA_LOOP", "OBSERVE_HEADLESS"):
        val = (env.get(key) or os.environ.get(key) or "").lower()
        if val in ("loop", "1", "true", "headless"):
            return True
    slug = os.environ.get("LAUNCHD_LABEL") or os.environ.get("LAUNCH_JOB_NAME") or ""
    if slug.startswith("com.agent-infra."):
        return True
    return False


def _assistant_turns_toolish(transcript_path: str, n: int = 2) -> bool | None:
    """True if any of the last n assistant turns used a tool. None = unknown."""
    if not transcript_path:
        return None
    path = Path(transcript_path).expanduser()
    if not path.is_file():
        return None
    assistants: list[bool] = []
    try:
        with path.open("r", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = obj.get("message") or {}
                role = obj.get("type") or ""
                if role != "assistant" and msg.get("role") != "assistant":
                    continue
                content = msg.get("content") if isinstance(msg, dict) else None
                used = False
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type") or ""
                        name = block.get("name") or ""
                        if btype in ("tool_use", "toolUse", "functionCall"):
                            used = True
                            break
                        if name in TOOL_KINDS or name.startswith("mcp__"):
                            used = True
                            break
                assistants.append(used)
    except OSError:
        return None
    if len(assistants) < n:
        return None
    return any(assistants[-n:])


def _checklist(cwd: str) -> str:
    if not CHECKLIST.is_file():
        return (
            "LEVER SWEEP: last turns had no tools — list 1–3 reversible probes "
            "still available (experiments, transcript reads, portfolio items), or say why none."
        )
    try:
        r = subprocess.run(
            [sys.executable, str(CHECKLIST), "--cwd", cwd],
            capture_output=True,
            text=True,
            timeout=8,
        )
        out = (r.stdout or "").strip()
        return out or "LEVER SWEEP: (checklist empty)"
    except (OSError, subprocess.TimeoutExpired):
        return (
            "LEVER SWEEP: checklist timed out — still: name 1–3 reversible probes "
            "not yet run this session, or say why none."
        )


def _shadow(row: dict) -> None:
    """No-op: stop-idle-lever-sweep-shadow.jsonl had no reader (2026-09-01 hooks audit). Call sites kept."""
    return


def verdict(*, cwd: str, transcript_path: str = "", env: dict | None = None) -> tuple[str, str]:
    env = env or {}
    if not _in_scope(cwd):
        return "pass", "out_of_scope"
    if _headless(env):
        return "pass", "headless"
    toolish = _assistant_turns_toolish(transcript_path, n=2)
    if toolish is None:
        return "pass", "unknown_transcript"
    if toolish:
        return "pass", "recent_tools"
    return "fire", "idle_wind_down_no_tools_last_2_assistant_turns"


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0
    if data.get("stop_hook_active"):
        return 0
    cwd = data.get("cwd") or os.getcwd()
    action, reason = verdict(
        cwd=cwd,
        transcript_path=data.get("transcript_path") or "",
        env=data,
    )
    if action != "fire":
        return 0
    msg = _checklist(cwd)
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "mode": MODE,
        "cwd": cwd,
        "session_id": data.get("session_id"),
        "reason": reason,
        "checklist_chars": len(msg),
    }
    _shadow(row)
    if MODE == "enforce":
        print(json.dumps({"decision": "block", "reason": msg}))
        return 0
    if MODE == "advisory":
        print(json.dumps({"additionalContext": msg}))
        return 0
    return 0


def _selftest() -> int:
    assert verdict(cwd="/Users/alien/Projects/intel")[0] == "pass"
    assert verdict(cwd="/Users/alien/Projects/arc-agi", transcript_path="")[0] == "pass"
    os.environ["RAISE_AUTONOMY_LEVER_SWEEP"] = "1"
    assert _in_scope("/tmp") is True
    del os.environ["RAISE_AUTONOMY_LEVER_SWEEP"]
    print("selftest ok")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    raise SystemExit(main())
