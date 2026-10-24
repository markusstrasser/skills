"""Regressions for bin/lane-archive: which files a lane owns, failures that must neither orphan a copy nor drop a
file, and restores that never replace an entry. tests/test_lane.sh covers the lane commands around it."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ARCHIVE = Path(os.environ.get("LANE_ARCHIVE_UNDER_TEST") or Path(__file__).resolve().parents[1] / "bin/lane-archive")
DAY = 86400


@pytest.fixture
def lab(tmp_path: Path):
    home, ssd, fake_bin = tmp_path / "lanes", tmp_path / "ssd", tmp_path / "bin"
    for path in (home, ssd, fake_bin):
        path.mkdir()
    env = {**os.environ, "LANE_ARCHIVE_VOLUME": str(ssd), "LANE_ARCHIVE_REQUIRE_MOUNT": "0", "DISK_FLOOR_GIB": "0",
           "PATH": f"{fake_bin}:{os.environ['PATH']}"}
    return Path(os.path.realpath(home)), ssd, fake_bin, env


def age(paths, days):
    stamp = time.time() - days * DAY
    for path in paths:
        for root, dirs, files in os.walk(path):
            for name in dirs + files:
                os.utime(os.path.join(root, name), (stamp, stamp), follow_symlinks=False)
        os.utime(path, (stamp, stamp), follow_symlinks=False)


def write(home, files):
    for relative, text in files.items():
        (home / relative).parent.mkdir(parents=True, exist_ok=True)
        (home / relative).write_text(text, encoding="utf-8")


def lane(home, name, files=None, days=20):
    """A lane that finished <days> ago, with no checkout and no live process."""
    files = {f"{name}.json": json.dumps({"name": name, "pid": 999999, "checkout": "none"}),
             f"{name}.done": "EXIT=0\n", **(files or {})}
    write(home, files)
    age({home / relative.split("/", 1)[0] for relative in files}, days)


def archive(home, env, *args):
    return subprocess.run([sys.executable, str(ARCHIVE), "--home", str(home), *args], env=env,
                          capture_output=True, text=True, check=False)


def archived(ssd):
    return sorted(path.name for path in ssd.glob("lane-archive/*/*")) + sorted(
        path.name for path in ssd.glob("lane-archive/*/.*"))


def test_a_lane_takes_only_the_files_its_tools_write(lab):
    home, ssd, _, env = lab
    lane(home, "a", {"a.log": "log\n", "a.stalled-1.log": "stall\n", "a.harvest/1/lane.patch": "patch\n",
                     "a.review.md": "review\n"})
    # Left by a reaped lane a.b, and a note made by hand: neither is a's.
    extra = {"a.b.stalled-1.log": "b stall\n", "a.b.harvest/1/lane.patch": "b patch\n", "a.note4.done": "EXIT=0\n"}
    write(home, extra)
    age([home / "a.b.stalled-1.log", home / "a.b.harvest", home / "a.note4.done"], 20)
    result = archive(home, env, "--apply")
    assert result.returncode == 0, result.stdout + result.stderr
    for entry in ("a.b.harvest", "a.b.stalled-1.log", "a.note4.done"):
        assert f"NO-LANE  {entry}\n" in result.stdout, result.stdout
    final = Path(archive(home, env, "--where", "a").stdout.strip())
    entries = json.loads((final / "MANIFEST.json").read_text(encoding="utf-8"))["entries"]
    assert sorted(entries) == ["a.done", "a.harvest", "a.harvest/1", "a.harvest/1/lane.patch", "a.json", "a.log",
                               "a.review.md", "a.stalled-1.log"]
    assert all((home / relative).is_file() for relative in extra)
    assert not (home / "a.json").exists() and not (home / "a.harvest").exists()


def test_lanes_that_could_own_one_file_are_both_skipped(lab):
    home, ssd, _, env = lab
    # x.review.done is lane x's review marker and lane x.review's own marker.
    lane(home, "x")
    lane(home, "x.review")
    result = archive(home, env, "--apply")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SKIP     x  x.review.done could be another lane's file as well" in result.stdout, result.stdout
    assert "SKIP     x.review  x.review.done could be another lane's file as well" in result.stdout, result.stdout
    assert archived(ssd) == [] and (home / "x.json").exists() and (home / "x.review.json").exists()


def test_an_index_that_cannot_be_written_leaves_no_copy(lab):
    home, ssd, _, env = lab
    lane(home, "d", {"d.log": "log\n"})
    index = home / ".archived.tsv"
    index.write_text("", encoding="utf-8")
    index.chmod(0o400)
    for _ in range(2):
        result = archive(home, env, "--apply")
        assert result.returncode == 1 and "FAILED   d  " in result.stdout, result.stdout + result.stderr
    assert archived(ssd) == []
    assert (home / "d.json").is_file() and (home / "d.log").read_text(encoding="utf-8") == "log\n"


def test_a_crashed_lsof_moves_nothing(lab):
    home, ssd, fake_bin, env = lab
    lane(home, "e", {"e.log": "log\n"})
    lsof = fake_bin / "lsof"
    # Part of a listing, then a crash: the list is incomplete, not "nothing open".
    lsof.write_text("#!/bin/sh\necho p1\necho n/unrelated\nkill -SEGV $$\n", encoding="utf-8")
    lsof.chmod(0o755)
    result = archive(home, env, "--apply")
    assert result.returncode == 75, result.stdout + result.stderr
    assert "[DEGRADED] lane-archive: lsof failed or gave no answer" in result.stdout, result.stdout
    assert archived(ssd) == [] and (home / "e.log").is_file()


def test_the_sweep_spares_a_partial_whose_pass_is_alive(lab):
    home, ssd, _, env = lab
    lane(home, "f", {"f.log": "log\n"})
    month = ssd / "lane-archive" / "2026-01"
    live, dead = month / f".g.partial-{os.getpid()}", month / ".h.partial-999999"
    for path in (live, dead):
        path.mkdir(parents=True)
    result = archive(home, env, "--apply")
    assert result.returncode == 0, result.stdout + result.stderr
    assert live.is_dir() and not dead.exists()


def test_the_bounded_pass_leaves_a_lane_over_its_bound(lab):
    home, ssd, _, env = lab
    lane(home, "big", {"big.harvest/blob": ""})
    with open(home / "big.harvest/blob", "r+b") as handle:
        handle.truncate((1 << 30) + 1)  # sparse: no blocks are written
    age([home / "big.harvest"], 20)
    lane(home, "small", {"small.log": "log\n"})
    result = archive(home, env, "--apply", "--bounded")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ARCHIVED small -> " in result.stdout and "ARCHIVED big" not in result.stdout, result.stdout
    assert (home / "big.json").is_file() and not (home / "small.json").exists()


def test_a_removal_that_stops_is_partial_and_unarchive_completes_it(lab):
    home, ssd, _, env = lab
    lane(home, "p", {"p.log": "log\n", "p.harvest/1/lane.patch": "patch\n"})
    locked = home / "p.harvest/1"
    locked.chmod(0o555)
    age([home / "p.harvest"], 20)
    try:
        result = archive(home, env, "--apply")
        assert result.returncode == 1, result.stdout + result.stderr
        assert "PARTIAL  p: " in result.stdout and "p.harvest/1/lane.patch (Permission denied)" in result.stdout
        assert not (home / "p.json").exists() and (home / "p.harvest/1/lane.patch").is_file()
        restored = archive(home, env, "--unarchive", "p")
        assert restored.returncode == 0, restored.stdout + restored.stderr
        assert (home / "p.json").is_file() and (home / "p.log").read_text(encoding="utf-8") == "log\n"
        assert archived(ssd) == []
    finally:
        locked.chmod(0o755)


def test_unarchive_refuses_a_difference_and_keeps_matching_leftovers(lab):
    home, ssd, _, env = lab
    lane(home, "c", {"c.log": "log\n", "c.harvest/1/lane.patch": "patch\n"})
    assert archive(home, env, "--apply").returncode == 0
    final = Path(archive(home, env, "--where", "c").stdout.strip())
    # Part of the lane with the same bytes, as a stopped restore leaves it, and one file with other bytes.
    write(home, {"c.harvest/1/lane.patch": "patch\n", "c.log": "a new run\n"})
    refused = archive(home, env, "--unarchive", "c")
    assert refused.returncode == 2 and "c.log" in refused.stderr, refused.stdout + refused.stderr
    assert (home / "c.log").read_text(encoding="utf-8") == "a new run\n" and final.is_dir()
    (home / "c.log").unlink()
    restored = archive(home, env, "--unarchive", "c")
    assert restored.returncode == 0, restored.stdout + restored.stderr
    assert "already in place" in restored.stdout, restored.stdout
    assert (home / "c.log").read_text(encoding="utf-8") == "log\n" and (home / "c.json").is_file()
    assert not final.exists() and archive(home, env, "--where", "c").returncode == 1


def test_unarchive_under_the_disk_floor_restores_nothing(lab):
    home, _, _, env = lab
    lane(home, "u", {"u.log": "log\n"})
    assert archive(home, env, "--apply").returncode == 0
    result = archive(home, {**env, "DISK_FLOOR_GIB": "100000000"}, "--unarchive", "u")
    assert result.returncode == 75 and "[DEGRADED] lane-archive: DISK LOW: " in result.stdout, result.stdout
    assert not (home / "u.json").exists() and not (home / "u.log").exists()
