#!/usr/bin/env python3
"""stop-uncommitted-warn.sh never auto-commits inside a lane clone (2026-10-27).

bin/lane marks a clone checkout with .git/lane-checkout-base and reviews it as a diff from
that base. A Stop-hook [wip] commit inside the clone (genomics 8cdaf0f6, 2026-10-24) left the
lane's work outside the review patch. With the marker: no commit, one advisory naming the
file. Positive control: the same repo without the marker gets the [wip] commit.

Run: python3 <thisfile>
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_stop_uncommitted_quiet import CHECKS, check, git, make_repo, run_hook, settle  # noqa: E402


def main():
    sid = f"test-stop-lane-{os.getpid()}"
    ledger = Path(f"/tmp/session-touched-{sid}.txt")
    seen = [Path.home() / ".claude" / f"stop-{k}-seen-{sid}.txt" for k in ("own", "contested", "unattrib")]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp)
            base = git(repo, "rev-parse", "HEAD").strip()
            (repo / ".git" / "lane-checkout-base").write_text(base + "\n")
            ledger.write_text("a.md\n")
            (repo / "a.md").write_text("lane edit\n")
            settle(repo / "a.md")
            code, ctx = run_hook(repo, sid)
            head = git(repo, "rev-parse", "HEAD").strip()
            check("lane clone: no [wip] commit", head == base and code == 0)
            check("lane clone: advisory names the file", "a.md" in ctx and "lane checkout" in ctx)
            (repo / ".git" / "lane-checkout-base").unlink()
            for path in seen:
                path.unlink(missing_ok=True)
            run_hook(repo, sid)
            log = git(repo, "log", "-1", "--format=%s")
            check("positive control: without the marker the [wip] commit happens",
                  git(repo, "rev-parse", "HEAD").strip() != base and log.startswith("[wip]"))
    finally:
        ledger.unlink(missing_ok=True)
        for path in seen:
            path.unlink(missing_ok=True)
    failed = [label for label, ok in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
