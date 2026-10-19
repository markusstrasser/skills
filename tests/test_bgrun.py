"""Regression: tool-shell group cleanup must not erase a detached job's receipt."""

from __future__ import annotations

import json
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
def job(tmp_path: Path, request):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    caffeinate = fake_bin / "caffeinate"
    if getattr(request, "param", "exec") == "exec":
        caffeinate.write_text('#!/bin/sh\n[ "$1" = -i ] && shift\nexec "$@"\n')
        caffeinate.chmod(0o755)
    else:
        assert Path("/usr/bin/caffeinate").is_file()
        caffeinate.symlink_to("/usr/bin/caffeinate")
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
            check=False,
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


@pytest.mark.parametrize("job", ["exec", "native"], indirect=True)
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


@pytest.mark.parametrize("job", ["exec", "native"], indirect=True)
def test_launch_names_live_output_before_completion(job) -> None:
    directory, _, run = job
    release = directory / "release"
    launched = run(
        "case", "--", sys.executable, "-c",
        "from pathlib import Path; import sys,time; print('LIVE_OUTPUT',flush=True)\n"
        "while not Path(sys.argv[1]).exists(): time.sleep(0.02)\n"
        "print('FINAL_OUTPUT',flush=True)",
        str(release),
    )
    try:
        assert launched.returncode == 0, launched.stderr
        lines = [line for line in launched.stdout.splitlines() if line.startswith("  live-log: ")]
        assert len(lines) == 1, launched.stdout
        live = Path(lines[0].removeprefix("  live-log: "))
        assert live == directory / "case.log.tmp"
        deadline = time.monotonic() + 5
        while (
            not live.exists() or "LIVE_OUTPUT" not in live.read_text()
        ) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert "LIVE_OUTPUT" in live.read_text()
        assert not (directory / "case.done").exists()
        assert "LIVE_OUTPUT" not in (directory / "case.log").read_text()
    finally:
        release.touch()
        waited = run("--wait", "case")
    assert waited.returncode == 0, waited.stderr
    assert "LIVE_OUTPUT" in (directory / "case.log").read_text()
    assert "FINAL_OUTPUT" in (directory / "case.log").read_text()
    assert not live.exists()


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


def kill_session(sid: int) -> None:
    """SIGKILL every process whose session is `sid` (macOS pkill has no -s)."""
    listing = subprocess.run(["ps", "-axo", "pid="], capture_output=True, text=True, check=True)
    for pid in (int(token) for token in listing.stdout.split()):
        try:
            if os.getsid(pid) == sid:
                os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def test_tool_session_cleanup_does_not_kill_the_job(job, tmp_path: Path) -> None:
    # 2026-09-29: closing a Claude Code session SIGTERMed a bgrun replay whose supervisor led its
    # own group but shared the tool shell's session. The harness leads a new session; killing
    # every process in that session must leave the job running to completion.
    directory, env, run = job
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
        assert os.getsid(supervisor) != harness.pid
        assert os.getpgid(supervisor) == supervisor
        kill_session(harness.pid)
        harness.wait(timeout=5)
        wait_file(directory / "finished")
        assert run("--wait", "case").returncode == 0
        assert (directory / "case.done").read_text() == "0\n"
    finally:
        if harness.poll() is None:
            kill_session(harness.pid)
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


@pytest.mark.parametrize("job", ["exec", "native"], indirect=True)
def test_sigint_interrupts_the_command_and_publishes_its_status(job) -> None:
    directory, _env, run = job
    child_script = directory / "int-child.py"
    child_script.write_text(
        "from pathlib import Path\n"
        "import json, os, signal, time\n"
        "Path('child-ready').write_text(json.dumps(dict(pid=os.getpid(), "
        "default=signal.getsignal(signal.SIGINT) is signal.default_int_handler)))\n"
        "try:\n"
        "    deadline = time.monotonic() + 12\n"
        "    while time.monotonic() < deadline: time.sleep(0.02)\n"
        "except KeyboardInterrupt:\n"
        "    print('CHILD_INTERRUPTED', flush=True)\n"
        "    raise SystemExit(3)\n"
        "raise SystemExit(92)\n"
    )
    launched = run("case", "--", sys.executable, str(child_script), cwd=directory)
    assert launched.returncode == 0, launched.stderr
    supervisor = int(wait_file(directory / "case.pid"))
    child = json.loads(wait_file(directory / "child-ready"))
    # An asynchronous child of a noninteractive shell starts with SIGINT ignored.
    assert child["default"] is True
    os.killpg(supervisor, signal.SIGINT)
    assert wait_file(directory / "case.done").strip() == "3"
    assert "CHILD_INTERRUPTED" in (directory / "case.log").read_text()


@pytest.mark.parametrize("job", ["exec", "native"], indirect=True)
@pytest.mark.parametrize("term_scope", ["supervisor", "group"])
def test_term_reaps_child_before_publishing_nonzero(job, term_scope: str) -> None:
    directory, env, run = job
    child_script = directory / "term-child.py"
    child_script.write_text(
        "from pathlib import Path\n"
        "import json, os, signal, time\n"
        "def stop(signum, frame):\n"
        "    signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "    Path('child-term').touch()\n"
        "    deadline = time.monotonic() + 12\n"
        "    while not Path('release-child').exists():\n"
        "        if time.monotonic() > deadline: raise SystemExit(91)\n"
        "        time.sleep(0.02)\n"
        "    Path('child-finished').touch()\n"
        "    print('CHILD_FINISHED', flush=True)\n"
        "    raise SystemExit(0)\n"
        "signal.signal(signal.SIGTERM, stop)\n"
        "Path('child-ready').write_text(json.dumps(dict(pid=os.getpid(), ppid=os.getppid(), "
        "pgid=os.getpgrp(), sid=os.getsid(0))))\n"
        "deadline = time.monotonic() + 12\n"
        "while time.monotonic() < deadline: time.sleep(0.02)\n"
        "raise SystemExit(92)\n"
    )
    supervisor = 0
    owned_identities: dict[int, str] = {}

    def started_identity(process_pid: int) -> str:
        return subprocess.run(
            ["ps", "-p", str(process_pid), "-o", "lstart="],
            env={**env, "TZ": "UTC", "LC_ALL": "C"},
            capture_output=True,
            text=True,
            check=False,
        ).stdout

    try:
        launched = run("case", "--", sys.executable, str(child_script), cwd=directory)
        assert launched.returncode == 0, launched.stderr
        supervisor = int(wait_file(directory / "case.pid"))
        recorded_started = (directory / "case.started").read_text()
        owned_identities[supervisor] = recorded_started
        child = json.loads(wait_file(directory / "child-ready"))
        child_pid = child["pid"]
        owned_identities[child_pid] = started_identity(child_pid)
        assert supervisor > 1 and supervisor != os.getpgrp()
        assert os.getpgid(supervisor) == os.getsid(supervisor) == supervisor
        assert child["pgid"] == child["sid"] == supervisor
        assert child["ppid"] == supervisor
        assert started_identity(supervisor) == recorded_started
        assert owned_identities[child_pid]
        if term_scope == "supervisor":
            os.kill(supervisor, signal.SIGTERM)
        else:
            os.killpg(supervisor, signal.SIGTERM)
        wait_file(directory / "child-term")
        # Keep the child alive after TERM: any terminal marker now is premature.
        assert not (directory / "case.done").exists()
        assert os.getpgid(child_pid) == supervisor
        original = {
            path.name: path.read_bytes()
            for path in directory.glob("case.*")
            if path.is_file()
        }
        refused = run("case", "--", "false", cwd=directory)
        assert refused.returncode == 125
        assert "already running" in refused.stderr
        assert original == {
            path.name: path.read_bytes()
            for path in directory.glob("case.*")
            if path.is_file()
        }
        assert not (directory / "case.done").exists()
        (directory / "release-child").touch()
        waited = run("--wait", "case", cwd=directory)
        assert waited.returncode == 143, waited.stderr
        assert (directory / "case.done").read_text() == "143\n"
        assert (directory / "child-finished").exists()
        assert "CHILD_FINISHED" in (directory / "case.log").read_text()
        assert not (directory / "case.log.tmp").exists()
        assert (directory / "case.pid").read_text() == f"{supervisor}\n"
        assert (directory / "case.started").read_text() == recorded_started
        assert not started_identity(child_pid), "receipt published before child was reaped"
    finally:
        (directory / "release-child").touch()
        # Cleanup can signal only this fixture group with a surviving PID/start match.
        for process_pid, expected_started in owned_identities.items():
            if expected_started and started_identity(process_pid) == expected_started:
                try:
                    if os.getpgid(process_pid) == supervisor:
                        os.killpg(supervisor, signal.SIGKILL)
                        break
                except ProcessLookupError:
                    pass
