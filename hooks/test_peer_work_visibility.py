#!/usr/bin/env python3
"""Test peer-work-visibility.py: shows peer dirty paths + peer commit topics, excludes my sid."""
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "peer-work-visibility.py"


def _git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, check=True)


def _commit(cwd, msg, sid):
    body = f"{msg}\n\nSession-ID: {sid}\n"
    subprocess.run(
        ["git", "-C", str(cwd), "commit", "-q", "--allow-empty", "-F", "-"],
        input=body, text=True, capture_output=True, check=True,
    )


def _repo():
    d = Path(tempfile.mkdtemp())
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@t")
    _git(d, "config", "user.name", "t")
    (d / "seed.txt").write_text("x")
    _git(d, "add", "seed.txt")
    _commit(d, "seed", "MINE-9999")  # seeded as mine so a clean same-sid repo is silent
    return d


def run(cwd, sid=""):
    p = subprocess.run(
        ["python3", str(HOOK), str(cwd), sid], capture_output=True, text=True, timeout=8
    )
    assert p.returncode == 0, p.stderr
    return p.stdout


def test_peer_commit_shown_mine_excluded():
    d = _repo()
    _commit(d, "peer did a thing", "PEER-1111")
    _commit(d, "i did a thing", "MINE-9999")
    out = run(d, "MINE-9999")
    assert "peer did a thing" in out
    assert "i did a thing" not in out


def test_dirty_paths_shown():
    d = _repo()
    (d / "seed.txt").write_text("modified by peer")
    out = run(d, "MINE-9999")
    assert "uncommitted paths" in out
    assert "seed.txt" in out


def test_silent_when_no_peer_work():
    d = _repo()
    # only my own commit, clean tree
    _commit(d, "just mine", "MINE-9999")
    out = run(d, "MINE-9999")
    assert out.strip() == ""


def test_fail_open_bad_cwd():
    p = subprocess.run(
        ["python3", str(HOOK), "/nonexistent/xyz", "sid"], capture_output=True, text=True, timeout=8
    )
    assert p.returncode == 0
    assert p.stdout.strip() == ""


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: test_peer_work_visibility")
