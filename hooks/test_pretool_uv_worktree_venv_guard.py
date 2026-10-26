#!/usr/bin/env python3
"""Test pretool-uv-worktree-venv-guard.py on a throwaway main checkout and linked worktree.

Run: python3 <thisfile> (or pytest). Exit 0 = all cases pass.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK = HERE / "pretool-uv-worktree-venv-guard.py"
DISPATCH = HERE / "pretool-bash-dispatch.py"
VIRTUAL = '[project]\nname = "demo"\nversion = "0"\nrequires-python = ">=3.11"\n'
PACKAGED = VIRTUAL + '\n[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n'


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _repo(root: Path, pyproject: str = VIRTUAL) -> tuple[Path, Path]:
    main = root / "main"
    main.mkdir()
    (main / "pyproject.toml").write_text(pyproject)
    (main / "uv.lock").write_text("version = 1\n")
    _git("init", "-q", cwd=main)
    _git("add", "pyproject.toml", "uv.lock", cwd=main)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init", cwd=main)
    worktree = root / "wt"
    _git("worktree", "add", "-q", "--detach", str(worktree), cwd=main)
    (main / ".venv").mkdir()
    return main.resolve(), worktree.resolve()


def _run(command: str, cwd: Path | str, hook: Path = HOOK) -> dict:
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}
    env = dict(os.environ, HOOK_TRIGGER_LOG=os.devnull)
    proc = subprocess.run(
        [sys.executable, str(hook)], input=json.dumps(envelope),
        capture_output=True, text=True, timeout=30, env=env,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _command(out: dict) -> str | None:
    return ((out.get("hookSpecificOutput") or {}).get("updatedInput") or {}).get("command")


def _prefix(main: Path) -> str:
    return f"env UV_PROJECT_ENVIRONMENT={main / '.venv'} UV_NO_SYNC=1 "


def test_rewrites_uv_run_bound_for_a_linked_worktree() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, wt = _repo(Path(tmp))
        prefix = _prefix(main)
        out = _run("uv run python3 x.py", wt)
        assert _command(out) == prefix + "uv run python3 x.py"
        assert "uv-worktree-venv-guard" in out["hookSpecificOutput"]["additionalContext"]
        assert _command(_run(f"cd {wt} && uv run python3 x.py", main)) == (
            f"cd {wt} && {prefix}uv run python3 x.py"
        )
        assert _command(_run(f"W={wt}; cd $W && uv run pytest", main)) == (
            f"W={wt}; cd $W && {prefix}uv run pytest"
        )
        assert _command(_run(f'cd "{wt}/sub" 2>/dev/null; uv run x', main)) == (
            f'cd "{wt}/sub" 2>/dev/null; {prefix}uv run x'
        )
        assert _command(_run(f"uv run --directory {wt} python3", main)) == (
            f"{prefix}uv run --directory {wt} python3"
        )
        # Only the worktree-bound call of two is prefixed.
        assert _command(_run(f"cd {wt} && uv run a; cd {main} && uv run b", main)) == (
            f"cd {wt} && {prefix}uv run a; cd {main} && uv run b"
        )


def test_passes_where_a_separate_environment_is_right_or_unknown() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, wt = _repo(Path(tmp))
        assert _run("uv run python3 x.py", main) == {}  # the main checkout itself
        assert _run("UV_PROJECT_ENVIRONMENT=/x uv run python3", wt) == {}  # caller chose
        assert _run("uv run --no-project python3 -c 1", wt) == {}  # no project env
        assert _run("echo 'uv run x'", wt) == {}  # quoted text
        assert _run("cat <<'EOF'\nuv run x\nEOF", wt) == {}  # heredoc body
        assert _run("cd $UNSET_DIR && uv run x", main) == {}  # unresolvable cd
        assert _run("ls", wt) == {}
        (wt / "uv.lock").write_text("version = 2\n")  # dependency files differ
        assert _run("uv run python3 x.py", wt) == {}
        (wt / "uv.lock").write_text("version = 1\n")
        (wt / ".venv").mkdir()  # the worktree already has its own environment
        assert _run("uv run python3 x.py", wt) == {}
    with tempfile.TemporaryDirectory() as tmp:
        _, wt = _repo(Path(tmp), PACKAGED)  # uv installs the package: main's venv points at main
        assert _run("uv run python3 x.py", wt) == {}
    with tempfile.TemporaryDirectory() as tmp:
        main, wt = _repo(Path(tmp))
        (main / ".venv").rmdir()  # nothing to share
        assert _run("uv run python3 x.py", wt) == {}


def test_rewritten_command_delivers_the_variables_through_wrappers() -> None:
    """Positive control: a fake `uv` sees the shared venv even behind `exec` and `nohup`."""
    with tempfile.TemporaryDirectory() as tmp:
        main, wt = _repo(Path(tmp))
        bin_dir = Path(tmp) / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "uv"
        fake.write_text('#!/bin/sh\necho "env=$UV_PROJECT_ENVIRONMENT nosync=$UV_NO_SYNC"\n')
        fake.chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
        for original in ("uv run x", "exec uv run x", "nohup uv run x 2>/dev/null"):
            command = _command(_run(original, wt))
            assert command, original
            proc = subprocess.run(
                ["bash", "-c", command], cwd=wt, env=env, capture_output=True, text=True, timeout=30
            )
            assert f"env={main / '.venv'} nosync=1" in proc.stdout, (original, proc.stdout, proc.stderr)
        (Path(wt) / "nohup.out").unlink(missing_ok=True)


def test_dispatcher_runs_the_gate_after_the_bare_python_rewrite() -> None:
    """A bare `python3` in a worktree becomes `uv run python3` first, then gets the shared venv."""
    with tempfile.TemporaryDirectory() as tmp:
        main, wt = _repo(Path(tmp))
        out = _run("python3 x.py", wt, hook=DISPATCH)
        assert _command(out) == _prefix(main) + "uv run python3 x.py"
        assert "uv-worktree-venv-guard" in out.get("additionalContext", "")


if __name__ == "__main__":
    failed = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  ok   {name}")
            except AssertionError as error:
                failed += 1
                print(f"  FAIL {name}: {error}")
    print("FAIL" if failed else "PASS", f"{failed} failed")
    raise SystemExit(1 if failed else 0)
