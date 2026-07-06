#!/usr/bin/env python3
"""Test pretool-bg-dispatch-footgun.py: codex-exec-stdin + bg relative-path advisories."""
import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "pretool-bg-dispatch-footgun.py"


def run(cmd: str, bg: bool = True, tool: str = "Bash") -> str:
    payload = {"tool_name": tool, "tool_input": {"command": cmd, "run_in_background": bg}}
    p = subprocess.run(
        ["python3", str(HOOK)], input=json.dumps(payload),
        capture_output=True, text=True, timeout=8,
    )
    assert p.returncode == 0, f"nonzero exit: {p.stderr}"
    if not p.stdout.strip():
        return ""
    return json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]


def test_codex_exec_no_devnull_fires():
    out = run("codex exec 'do the thing' > /tmp/log.txt")
    assert "close stdin" in out


def test_codex_exec_with_devnull_silent():
    assert run("codex exec 'do the thing' < /dev/null > /tmp/log.txt") == ""


def test_codex_exec_full_auto_nudge():
    out = run("codex exec --full-auto 'x' > /tmp/log 2>&1")
    assert "deprecated" in out


def test_relative_node_path_fires():
    out = run("node harness.mjs")
    assert "reset cwd" in out


def test_relative_python_path_fires():
    out = run("python3 scripts/run.py")
    assert "reset cwd" in out


def test_absolute_path_silent():
    assert run("node /Users/alien/proj/harness.mjs") == ""


def test_cd_prefix_silent():
    assert run("cd /Users/alien/proj && node harness.mjs") == ""


def test_uv_run_console_entrypoint_silent():
    # `uv run pytest` — pytest is a console entry point, not a cwd-relative file
    assert run("uv run pytest -q") == ""


def test_foreground_silent():
    assert run("codex exec 'x'", bg=False) == ""


def test_non_bash_silent():
    assert run("codex exec 'x'", tool="Write") == ""


def test_empty_stdin_fail_open():
    p = subprocess.run(["python3", str(HOOK)], input="", capture_output=True, text=True, timeout=8)
    assert p.returncode == 0
    assert p.stdout.strip() == ""


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: test_pretool_bg_dispatch_footgun")
