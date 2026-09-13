"""Regression: tool-shell group cleanup must not erase a detached job's receipt."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

BGRUN = Path(__file__).resolve().parents[1] / "bin/bgrun"


def wait_file(path: Path) -> str:
    deadline = time.monotonic() + 5
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert path.exists(), f"missing {path}"
    return path.read_text()


@pytest.fixture
def job(tmp_path: Path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    caffeinate = fake_bin / "caffeinate"
    caffeinate.write_text('#!/bin/sh\n[ "$1" = -i ] && shift\nexec "$@"\n')
    caffeinate.chmod(0o755)
    env = {
        **os.environ,
        "BGRUN_DIR": str(tmp_path),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
    }
    supervisors: list[int] = []

    def run(*args: str, **kwargs):
        result = subprocess.run(
            [str(BGRUN), *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=8,
            **kwargs,
        )
        pid_file = tmp_path / "case.pid"
        if pid_file.exists():
            supervisors.append(int(pid_file.read_text()))
        return result

    yield tmp_path, env, run
    # Only groups returned by this fixture's own harmless launches are eligible.
    for pid in set(supervisors):
        if pid <= 1 or pid == os.getpgrp():
            continue
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


@pytest.mark.parametrize("exit_code", [0, 7])
def test_completion_preserves_status_and_log(job, exit_code: int) -> None:
    directory, _, run = job
    result = run(
        "case",
        "--",
        sys.executable,
        "-c",
        f"print('JOB_OUTPUT'); raise SystemExit({exit_code})",
    )
    assert result.returncode == 0, result.stderr
    waited = run("--wait", "case")
    assert waited.returncode == exit_code, waited.stderr
    assert (directory / "case.done").read_text() == f"{exit_code}\n"
    assert "JOB_OUTPUT" in (directory / "case.log").read_text()
    assert not (directory / "case.log.tmp").exists()


def test_child_stdin_is_closed(job) -> None:
    directory, _, run = job
    result = run(
        "case",
        "--",
        sys.executable,
        "-c",
        "import sys; print(repr(sys.stdin.read()))",
        input="not child input",
    )
    assert result.returncode == 0, result.stderr
    assert run("--wait", "case").returncode == 0
    assert "''" in (directory / "case.log").read_text()


def test_live_same_name_preserves_all_existing_bytes(job) -> None:
    directory, _, run = job
    result = run(
        "case",
        "--",
        sys.executable,
        "-c",
        "import time; print('RUNNING', flush=True); time.sleep(20)",
    )
    assert result.returncode == 0, result.stderr
    output = directory / "case.log.tmp"
    deadline = time.monotonic() + 5
    while (
        not output.exists() or "RUNNING" not in output.read_text()
    ) and time.monotonic() < deadline:
        time.sleep(0.02)
    assert "RUNNING" in output.read_text()
    original = {
        path.name: path.read_bytes()
        for path in directory.glob("case.*")
        if path.is_file()
    }
    refused = run("case", "--", "false")
    assert refused.returncode == 125
    assert "already running" in refused.stderr
    assert original == {
        path.name: path.read_bytes()
        for path in directory.glob("case.*")
        if path.is_file()
    }


def test_concurrent_same_name_launches_do_not_replace_each_other(job) -> None:
    _, _, run = job
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                run, "case", "--", sys.executable, "-c", "import time; time.sleep(20)"
            )
            for _ in range(2)
        ]
        results = [future.result() for future in futures]
    assert sorted(result.returncode for result in results) == [0, 125]


def test_dead_supervisor_without_marker_fails_loudly(job) -> None:
    directory, _, run = job
    result = run("case", "--", sys.executable, "-c", "import time; time.sleep(20)")
    assert result.returncode == 0, result.stderr
    pid = int((directory / "case.pid").read_text())
    os.killpg(pid, signal.SIGKILL)
    waited = run("--wait", "case")
    assert waited.returncode == 125
    assert "died without completion" in waited.stderr
    assert not (directory / "case.done").exists()


def test_orphaned_child_group_is_not_clobbered(job) -> None:
    directory, _, run = job
    assert (
        run(
            "case", "--", sys.executable, "-c", "import time; time.sleep(20)"
        ).returncode
        == 0
    )
    pid = int((directory / "case.pid").read_text())
    os.kill(pid, signal.SIGKILL)  # only this test's supervisor; its child remains
    refused = run("case", "--", "false")
    assert refused.returncode == 125
    assert "already running" in refused.stderr
    assert (directory / "case.pid").read_text() == f"{pid}\n"


def test_legacy_live_pid_without_start_identity_is_not_clobbered(job) -> None:
    directory, _, run = job
    assert (
        run(
            "case", "--", sys.executable, "-c", "import time; time.sleep(20)"
        ).returncode
        == 0
    )
    (directory / "case.started").unlink()
    original_pid = (directory / "case.pid").read_bytes()
    refused = run("case", "--", "false")
    assert refused.returncode == 125
    assert (directory / "case.pid").read_bytes() == original_pid


def test_wait_refuses_a_changed_job_identity(job) -> None:
    directory, env, run = job
    assert (
        run(
            "case", "--", sys.executable, "-c", "import time; time.sleep(20)"
        ).returncode
        == 0
    )
    waiter = subprocess.Popen(
        [str(BGRUN), "--wait", "case"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(0.2)
    (directory / "case.started").write_text("different launch identity\n")
    _, stderr = waiter.communicate(timeout=5)
    assert waiter.returncode == 125
    assert "identity changed" in stderr


def test_tool_process_group_cleanup_does_not_kill_the_job(job, tmp_path: Path) -> None:
    directory, env, run = job
    # This harness owns a new group, exactly the cleanup scope used by exec tools.
    # Its only descendants are our launcher and a short marker child.
    harness_script = tmp_path / "harness.py"
    child = "from pathlib import Path; import time; Path('started').touch(); time.sleep(0.6); Path('finished').touch()"
    harness_script.write_text(
        "import subprocess, sys, time\n"
        f"result = subprocess.run({[str(BGRUN), 'case', '--', sys.executable, '-c', child]!r}, capture_output=True)\n"
        "assert result.returncode == 0, result.stderr\n"
        "time.sleep(20)\n"
    )
    harness = subprocess.Popen(
        [sys.executable, str(harness_script)],
        env=env,
        cwd=directory,
        start_new_session=True,
    )
    try:
        wait_file(directory / "started")
        supervisor = int(wait_file(directory / "case.pid"))
        assert os.getpgid(supervisor) == supervisor
        assert supervisor != harness.pid
        os.killpg(harness.pid, signal.SIGKILL)
        harness.wait(timeout=5)
        wait_file(directory / "finished")
        assert run("--wait", "case").returncode == 0
        assert (directory / "case.done").read_text() == "0\n"
    finally:
        if harness.poll() is None:
            os.killpg(harness.pid, signal.SIGKILL)
            harness.wait(timeout=5)


def test_killed_launch_owner_does_not_leave_a_stale_lock(job) -> None:
    directory, env, run = job
    pause = directory / "pause-rm"
    pause.touch()
    (directory / "bin/rm").write_text(
        '#!/bin/sh\nif test -e "$BGRUN_DIR/pause-rm"; then\n'
        '  touch "$BGRUN_DIR/lock-acquired"\n  sleep 20\nfi\nexec /bin/rm "$@"\n'
    )
    (directory / "bin/rm").chmod(0o755)
    launcher = subprocess.Popen(
        [str(BGRUN), "case", "--", "true"],
        env=env,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_file(directory / "lock-acquired")
        os.killpg(launcher.pid, signal.SIGKILL)
        launcher.wait(timeout=5)
    finally:
        if launcher.poll() is None:
            os.killpg(launcher.pid, signal.SIGKILL)
            launcher.wait(timeout=5)
        pause.unlink(missing_ok=True)
    replacement = run("case", "--", "true")
    assert replacement.returncode == 0, replacement.stderr
    assert run("--wait", "case").returncode == 0


def test_wait_cannot_consume_a_replacement_jobs_receipt(job) -> None:
    directory, env, run = job
    assert (
        run("case", "--", sys.executable, "-c", "raise SystemExit(7)").returncode == 0
    )
    assert wait_file(directory / "case.done") == "7\n"
    time.sleep(0.1)  # the completed supervisor finishes its final exit
    pause = directory / "pause-wait"
    pause.touch()
    shell_env = directory / "wait-barrier.sh"
    # Force the real check/read interleaving, without editing the launcher under test.
    shell_env.write_text(
        'if test "${1:-}" = --wait; then\n'
        "  function [() {\n"
        '    if test "$#" = 3 && test "$1" = -f && test "$2" = "$BGRUN_DIR/case.done" && test -e "$BGRUN_DIR/pause-wait"; then\n'
        '      touch "$BGRUN_DIR/wait-reading"\n'
        '      while test -e "$BGRUN_DIR/pause-wait"; do sleep 0.02; done\n'
        '    fi\n    builtin [ "$@"\n  }\nfi\n'
    )
    waiter = subprocess.Popen(
        [str(BGRUN), "--wait", "case"],
        env={**env, "BASH_ENV": str(shell_env)},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        wait_file(directory / "wait-reading")
        replacement = run("case", "--", "true")
        if replacement.returncode == 0:
            assert wait_file(directory / "case.done") == "0\n"
        pause.unlink()
        _, stderr = waiter.communicate(timeout=5)
        assert waiter.returncode == 7, stderr
        assert replacement.returncode == 125
    finally:
        pause.unlink(missing_ok=True)
        if waiter.poll() is None:
            waiter.communicate(timeout=5)


@pytest.mark.parametrize("marker", ["", "SUCCESS\n", "999\n"])
def test_invalid_completion_is_not_success(job, marker: str) -> None:
    directory, _, run = job
    (directory / "case.pid").write_text("99999999\n")
    (directory / "case.done").write_text(marker)
    result = run("--wait", "case")
    assert result.returncode == 125
    assert "invalid completion" in result.stderr
