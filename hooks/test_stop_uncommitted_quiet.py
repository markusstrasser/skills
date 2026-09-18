#!/usr/bin/env python3
"""Test stop-uncommitted-warn.sh quiet modes (2026-09-18).

Pins three behaviors added after immigration-research 2026-09-17/18 produced nine
[wip] checkpoints and eleven repeated contested-file lists in one session:
  1. `.claude/no-auto-checkpoint` in the repo: no commit, one advisory naming the
     files, and silence on the next Stop (once per file per session).
  2. Without the marker and with no live subagents, a settled own file is still
     auto-committed as [wip] (the original behavior is preserved).
  3. An unattributable `_cache/` file is never surfaced.

Run: python3 <thisfile>
"""
import json
import os
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
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def run_hook(repo, sid):
    r = subprocess.run([str(HOOK)], input=json.dumps({"cwd": str(repo), "session_id": sid}),
                       capture_output=True, text=True)
    ctx = ""
    if r.stdout.strip():
        try:
            ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
        except Exception:
            ctx = r.stdout
    return r.returncode, ctx


def make_repo(tmp):
    repo = Path(tmp) / "repo"
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


def main():
    sid = f"test-stop-{os.getpid()}"
    ledger = Path(f"/tmp/session-touched-{sid}.txt")
    seen = [Path.home() / ".claude" / f"stop-{k}-seen-{sid}.txt" for k in ("own", "contested", "unattrib")]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp)
            ledger.write_text("a.md\n")
            (repo / "a.md").write_text("edited\n")
            settle(repo / "a.md")
            cache = repo / "lane" / "_cache"
            cache.mkdir(parents=True)
            (cache / "cells.csv").write_text("x\n")
            settle(cache / "cells.csv")
            # 1. marker present: no commit, one advisory, then silence
            (repo / ".claude").mkdir()
            (repo / ".claude" / "no-auto-checkpoint").write_text("off\n")
            before = git(repo, "rev-list", "--count", "HEAD").strip()
            code, ctx = run_hook(repo, sid)
            after = git(repo, "rev-list", "--count", "HEAD").strip()
            check("marker: no [wip] commit", before == after and code == 0)
            check("marker: advisory names the file", "a.md" in ctx and "auto-checkpoint is off" in ctx)
            check("marker: _cache file never surfaced", "_cache" not in ctx)
            code, ctx2 = run_hook(repo, sid)
            check("marker: second Stop is silent", ctx2.strip() == "")
            # 2. marker removed, settled file: original auto-commit preserved
            (repo / ".claude" / "no-auto-checkpoint").unlink()
            code, ctx3 = run_hook(repo, sid)
            after2 = git(repo, "rev-list", "--count", "HEAD").strip()
            log = git(repo, "log", "-1", "--format=%s")
            check("no marker: [wip] auto-commit happens", int(after2) == int(before) + 1 and log.startswith("[wip]"))
            check("no marker: _cache file never surfaced", "_cache" not in ctx3)
    finally:
        ledger.unlink(missing_ok=True)
        for p in seen:
            p.unlink(missing_ok=True)
    failed = [l for l, ok in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
