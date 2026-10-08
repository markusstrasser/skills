#!/usr/bin/env python3
"""Test stop-uncommitted-warn.sh never checkpoints mid-commit work (2026-10-08).

genomics 2026-10-08: a landing tool (land_lane) had staged a lane commit on main and
was running its pre-commit hooks when the parent session's Stop fired. The hook's
subagent check read only `<slug>/<session_id>/tasks`, but after a context continuation
the harness wrote task outputs under a different session dir, so the hook saw no live
subagents and ran `git commit --only` on one of the staged files. That commit failed
only by luck; success would have split the landing commit into a [wip] checkpoint.

Pins:
  1. Staged content at hook start: no auto-commit, HEAD unchanged, path still staged.
  2. A recent task output under ANOTHER session dir for the same checkout: no auto-commit.
  3. Positive control: neither condition, a settled own file IS auto-committed, so the
     two guards above are not passing merely because the hook never commits.

Run: python3 <thisfile>
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOOK = Path(__file__).parent / "stop-uncommitted-warn.sh"
CHECKS = []


def check(label, ok):
    CHECKS.append((label, ok))
    print(f"  {'✓' if ok else '✗'} {label}")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout


def run_hook(repo, sid):
    subprocess.run([str(HOOK)], input=json.dumps({"cwd": str(repo), "session_id": sid}),
                   capture_output=True, text=True)


def make_repo(tmp, name):
    repo = Path(tmp) / name
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / "a.md").write_text("base\n")
    git(repo, "add", "a.md")
    git(repo, "commit", "-q", "-m", "init")
    return repo


def settle(path):
    old = time.time() - 1000
    os.utime(path, (old, old))


def head(repo):
    return git(repo, "rev-parse", "HEAD").strip()


def slug_dir(repo):
    return Path("/private/tmp") / f"claude-{os.getuid()}" / os.path.abspath(str(repo)).replace("/", "-")


def main():
    sid = f"test-staged-{os.getpid()}"
    ledger = Path(f"/tmp/session-touched-{sid}.txt")
    seen = [Path.home() / ".claude" / f"stop-{kind}-seen-{sid}.txt"
            for kind in ("own", "contested", "unattrib")]
    made_slugs = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            # 1. staged content at hook start
            repo = make_repo(tmp, "staged")
            (repo / "b.py").write_text("landed = 1\n")
            git(repo, "add", "b.py")
            settle(repo / "b.py")
            ledger.write_text("b.py\n")
            before = head(repo)
            run_hook(repo, sid)
            check("staged path: HEAD unchanged", head(repo) == before)
            check("staged path: still staged", "b.py" in git(repo, "diff", "--cached", "--name-only"))

            # 2. recent task output under another session dir for this checkout
            repo2 = make_repo(tmp, "peer_tasks")
            (repo2 / "a.md").write_text("edited\n")
            settle(repo2 / "a.md")
            ledger.write_text("a.md\n")
            other_tasks = slug_dir(repo2) / "other-session" / "tasks"
            other_tasks.mkdir(parents=True, exist_ok=True)
            made_slugs.append(slug_dir(repo2))
            (other_tasks / "agent.output").write_text("running\n")
            before = head(repo2)
            run_hook(repo2, sid)
            check("other-session task output: HEAD unchanged", head(repo2) == before)

            # 3. positive control: no staged paths, no task outputs -> checkpoint happens
            repo3 = make_repo(tmp, "control")
            (repo3 / "a.md").write_text("edited\n")
            settle(repo3 / "a.md")
            ledger.write_text("a.md\n")
            before = head(repo3)
            run_hook(repo3, sid)
            check("control: settled own file auto-committed", head(repo3) != before)
    finally:
        ledger.unlink(missing_ok=True)
        for path in seen:
            path.unlink(missing_ok=True)
        for slug in made_slugs:
            shutil.rmtree(slug, ignore_errors=True)
    failed = [label for label, ok in CHECKS if not ok]
    print(f"{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
