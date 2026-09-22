"""pretool-live-batch-edit-guard.py: blocks main scripts/ + config/ edits only mid-row."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).with_name("pretool-live-batch-edit-guard.py")
DEAD_PID = 2**22 - 1


def run_hook(repo: Path, envelope: dict, **env: str) -> subprocess.CompletedProcess:
    inherited = {
        key: value for key, value in os.environ.items() if key != "GENOMICS_LIVE_BATCH_EDIT_OK"
    }
    # The pytest process stands in for the batch driver whose pid in-flight.json names.
    environment = {
        **inherited,
        "LIVE_BATCH_GUARD_REPO": str(repo),
        "LIVE_BATCH_GUARD_DRIVER_MARK": "pytest",
        **env,
    }
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(envelope),
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


def in_flight(repo: Path, pid: int) -> None:
    batch = repo / ".claude/cache/drive-batches/syn7sr/batch-a"
    batch.mkdir(parents=True)
    (batch / "in-flight.json").write_text(
        json.dumps({"batch_name": "batch-a", "driver_pid": pid, "stage": "genetic_load"})
    )


def edit(path: Path) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": str(path)}, "cwd": "/"}


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    for relative in ("scripts", "config", "docs", ".claude/worktrees/lane/scripts"):
        (tmp_path / relative).mkdir(parents=True)
    return tmp_path


def test_blocks_main_source_edit_while_a_row_is_in_flight(repo: Path) -> None:
    in_flight(repo, os.getpid())
    for target in (repo / "scripts/stage.py", repo / "config/new.json"):
        result = run_hook(repo, edit(target))
        assert result.returncode == 2
        assert "batch-a:genetic_load" in result.stderr and "DirtyGitSourceError" in result.stderr


def test_relative_path_resolves_against_the_envelope_cwd(repo: Path) -> None:
    in_flight(repo, os.getpid())
    envelope = {"tool_name": "Write", "tool_input": {"file_path": "scripts/x.py"}, "cwd": str(repo)}
    assert run_hook(repo, envelope).returncode == 2


@pytest.mark.parametrize(
    "relative", ["docs/notes.md", ".claude/worktrees/lane/scripts/stage.py", "tests/test_x.py"]
)
def test_allows_paths_outside_the_launch_source(repo: Path, relative: str) -> None:
    in_flight(repo, os.getpid())
    assert run_hook(repo, edit(repo / relative)).returncode == 0


def test_allows_edits_when_no_row_is_in_flight_or_its_driver_is_dead(repo: Path) -> None:
    assert run_hook(repo, edit(repo / "scripts/stage.py")).returncode == 0
    in_flight(repo, DEAD_PID)
    assert run_hook(repo, edit(repo / "scripts/stage.py")).returncode == 0


def test_a_reused_pid_that_is_not_a_batch_driver_does_not_block(repo: Path) -> None:
    # A dead batch leaves in-flight.json behind; its pid may now belong to anything.
    in_flight(repo, os.getpid())
    result = run_hook(
        repo, edit(repo / "scripts/stage.py"), LIVE_BATCH_GUARD_DRIVER_MARK="drive_batch.py"
    )
    assert result.returncode == 0


def test_override_and_foreign_repo_pass(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    in_flight(repo, os.getpid())
    target = repo / "scripts/stage.py"
    assert run_hook(repo, edit(target), GENOMICS_LIVE_BATCH_EDIT_OK="1").returncode == 0
    elsewhere = tmp_path_factory.mktemp("other") / "scripts/stage.py"
    assert run_hook(repo, edit(elsewhere)).returncode == 0
