#!/usr/bin/env python3
# Gov-ID: hook:cursor-shell-guards
# goal: Cursor preToolUse/beforeShellExecution parity with Claude PreToolUse:Bash guards
# verifier: --selftest
# blast_radius: shared
"""Cursor shell guard adapter — uv-python rewrite + multiline loop block.

Reads Cursor hook JSON on stdin; emits Cursor-shaped stdout (permission/updated_input).
Reuses pretool-uv-python-guard.verdict and pretool-bash-loop-guard logic."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "pretool_uv_python_guard", _HOOKS / "pretool-uv-python-guard.py"
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
verdict = _mod.verdict


def _project_has_uv(cwd: str) -> bool:
    """True if cwd (or an ancestor) looks like a uv/python project."""
    if not cwd:
        return False
    p = Path(cwd).expanduser().resolve()
    for cand in (p, *p.parents):
        if (cand / "uv.lock").exists() or (cand / "pyproject.toml").exists():
            return True
        if cand == cand.parent:
            break
    return False


def _strip_heredocs(cmd: str) -> str:
    out, skip_until = [], None
    for ln in cmd.split("\n"):
        if skip_until is not None:
            if ln.strip() == skip_until:
                skip_until = None
            continue
        m = re.search(r"<<-?\s*(['\"]?)(\w+)\1", ln)
        out.append(ln)
        if m:
            skip_until = m.group(2)
    return "\n".join(out)


def _multiline_loop(cmd: str) -> bool:
    cmd = _strip_heredocs(cmd)
    return bool(re.search(r"\b(do|then)\s*\n", cmd))


def _parse(payload: dict) -> tuple[str, str]:
    ti = payload.get("tool_input") or {}
    cmd = (
        payload.get("command")
        or ti.get("command")
        or ""
    )
    cwd = (
        payload.get("cwd")
        or payload.get("working_directory")
        or payload.get("workingDirectory")
        or ti.get("working_directory")
        or ""
    )
    return cmd, cwd


def _deny(msg: str) -> None:
    print(json.dumps({
        "permission": "deny",
        "agent_message": msg,
        "user_message": msg,
    }))
    sys.exit(2)


def _allow(*, updated_command: str | None = None) -> None:
    out: dict = {"permission": "allow"}
    if updated_command is not None:
        out["updated_input"] = {"command": updated_command}
    print(json.dumps(out))


def handle(mode: str, payload: dict) -> int:
    cmd, cwd = _parse(payload)
    if not cmd.strip():
        _allow()
        return 0

    if _multiline_loop(cmd):
        _deny(
            "BLOCKED: Multiline for/while/if blocks cause zsh parse errors. "
            "Use single-line syntax or a temp .sh file:\n"
            "  for x in *.txt; do echo \"$x\"; done"
        )

    can_rewrite = _project_has_uv(cwd)
    action, msg = verdict(cmd, can_rewrite=can_rewrite)
    if action == "block":
        _deny(msg)
    if action == "rewrite" and msg and mode in ("pretool", "preToolUse"):
        _allow(updated_command=msg)
        return 0
    if action == "rewrite" and msg:
        # beforeShellExecution cannot rewrite — block with guidance
        _deny(
            f"Use `uv run python3` instead of bare python. Suggested: {msg}"
        )
    _allow()
    return 0


def _selftest() -> int:
    cases = [
        ({"tool_input": {"command": "python3 foo.py"}, "cwd": "/tmp"}, "pretool", "deny"),
        ({"command": "for x in a; do\necho x\ndone"}, "before", "deny"),
        ({"tool_input": {"command": "ls"}, "cwd": "/tmp"}, "pretool", "allow"),
    ]
    bad = 0
    for payload, mode, want in cases:
        # dry-run logic without exit
        cmd, cwd = _parse(payload)
        if _multiline_loop(cmd):
            got = "deny"
        else:
            act, _ = verdict(cmd, can_rewrite=_project_has_uv(cwd))
            got = "deny" if act == "block" else "allow"
        ok = got == want
        bad += not ok
        print(f"  {'ok' if ok else 'FAIL'} want={want} got={got} {payload!r}")
    # import sibling selftest
    r = subprocess.run(
        [sys.executable, str(_HOOKS / "pretool-uv-python-guard.py"), "--selftest"],
        capture_output=True,
        text=True,
    )
    print(r.stdout, end="")
    bad += r.returncode
    print(f"{'FAIL' if bad else 'PASS'}")
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    mode = (sys.argv[1] if len(sys.argv) > 1 else "pretool").lower()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        _allow()
        return 0
    return handle(mode, payload)


if __name__ == "__main__":
    raise SystemExit(main())
