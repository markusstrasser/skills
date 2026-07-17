#!/usr/bin/env python3
# Gov-ID: hook:stop-llmx-child-guard
# goal: block/nudge SubagentStop when a nohup llmx child is still running and the
#       protocol memo/output is unfinished (observe architecture 2026-07-15 P72)
# verifier: --selftest
# blast_radius: shared (SubagentStop; default SHADOW — measure before enforce)
"""stop-llmx-child-guard.py — SubagentStop: don't yield while llmx child is live.

Instruction-only "wait for llmx" failed twice in one arc-agi wave (2026-07-14).
This externalizes the check: if scratchpad has a live llmx pid / fresh log and
the -o output is empty/stale, surface a block (enforce) or shadow row.

Modes (env LLMX_CHILD_GUARD_MODE):
  shadow   (default) — log would-fire; never block
  advisory — additionalContext only
  enforce  — decision:block

Fail-open on any parse/IO error.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

SHADOW_LOG = Path.home() / ".claude" / "llmx-child-guard-shadow.jsonl"
MODE = os.environ.get("LLMX_CHILD_GUARD_MODE", "shadow").strip().lower()


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _find_scratchpads(cwd: str) -> list[Path]:
    if not cwd:
        return []
    root = Path(cwd).expanduser()
    cands: list[Path] = []
    for name in ("scratchpad", ".scratchpad", "tmp"):
        p = root / name
        if p.is_dir():
            cands.append(p)
    # Claude worktree scratchpads under /tmp/claude-*
    tmp = Path("/tmp")
    if tmp.is_dir():
        for p in tmp.glob("claude-*/**"):
            if p.is_dir() and p.name in ("scratchpad",) and cwd.replace("/", "-") in str(p):
                cands.append(p)
    return cands


def _scan_dispatch(scratch: Path) -> dict | None:
    """Prefer explicit registry file written by llmx dispatch wrappers."""
    for name in ("dispatch.json", "llmx-dispatch.json", "in-flight.json"):
        path = scratch / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            data["_path"] = str(path)
            return data
    return None


def _scan_logs(scratch: Path, max_age_s: float = 3600.0) -> dict | None:
    """Heuristic: recent *.log mentioning llmx + empty/missing paired -o."""
    now = time.time()
    for log in scratch.glob("*.log"):
        try:
            st = log.stat()
        except OSError:
            continue
        if now - st.st_mtime > max_age_s:
            continue
        try:
            head = log.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        if "llmx" not in head.lower() and "LLMX" not in head:
            continue
        # paired output: same stem .md / .json / -o sibling
        outs = [
            log.with_suffix(".md"),
            log.with_suffix(".json"),
            Path(str(log).removesuffix(".log") + ".out"),
        ]
        unfinished = False
        for out in outs:
            if out.is_file():
                try:
                    if out.stat().st_size == 0:
                        unfinished = True
                        break
                except OSError:
                    unfinished = True
                    break
            else:
                unfinished = True
        if unfinished:
            return {
                "log": str(log),
                "mtime_age_s": int(now - st.st_mtime),
                "reason": "recent_llmx_log_unfinished_output",
            }
    return None


def verdict(cwd: str = "", env: dict | None = None) -> tuple[str, str]:
    """Return (action, reason). action ∈ pass|fire."""
    env = env or {}
    # Explicit env from dispatch wrappers
    pid_s = env.get("LLMX_CHILD_PID") or os.environ.get("LLMX_CHILD_PID") or ""
    if pid_s.isdigit() and _pid_alive(int(pid_s)):
        return "fire", f"LLMX_CHILD_PID={pid_s} still alive"
    for scratch in _find_scratchpads(cwd):
        disp = _scan_dispatch(scratch)
        if disp:
            pid = disp.get("pid") or disp.get("llmx_pid")
            status = (disp.get("status") or "").lower()
            if status in ("running", "in_flight", "started") or (
                isinstance(pid, int) and _pid_alive(pid)
            ):
                if status not in ("done", "complete", "ok"):
                    return "fire", f"dispatch registry {disp.get('_path')}: pid={pid} status={status or 'unknown'}"
        hit = _scan_logs(scratch)
        if hit:
            return "fire", f"{hit['reason']}: {hit['log']} (age={hit['mtime_age_s']}s)"
    return "pass", ""


def _shadow(row: dict) -> None:
    try:
        SHADOW_LOG.parent.mkdir(parents=True, exist_ok=True)
        with SHADOW_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0
    if data.get("stop_hook_active"):
        return 0
    cwd = data.get("cwd") or os.getcwd()
    action, reason = verdict(cwd=cwd, env=data)
    if action != "fire":
        return 0
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "mode": MODE,
        "cwd": cwd,
        "session_id": data.get("session_id"),
        "agent_id": data.get("agent_id"),
        "reason": reason,
    }
    _shadow(row)
    msg = (
        "LLMX CHILD STILL RUNNING: " + reason
        + " — bounded wait/poll the child (or kill if wedged) before yielding. "
        "Do not SendMessage-nudge the parent as a substitute for waiting."
    )
    if MODE == "enforce":
        print(json.dumps({"decision": "block", "reason": msg}))
        return 0
    if MODE == "advisory":
        print(json.dumps({"additionalContext": msg}))
        return 0
    # shadow: silent to the model
    return 0


def _selftest() -> None:
    # no cwd → pass
    assert verdict(cwd="")[0] == "pass"
    # dead pid env → pass
    assert verdict(cwd="/tmp", env={"LLMX_CHILD_PID": "99999999"})[0] == "pass"
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        raise SystemExit(0)
    raise SystemExit(main())
