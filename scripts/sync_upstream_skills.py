#!/usr/bin/env python3
"""Keep vendored third-party skills equal to a pinned upstream commit.

A vendored skill is a directory holding an UPSTREAM.json:

    {"repo": "owner/name", "path": "dir/in/repo", "commit": "<sha>",
     "files": {"SKILL.md": "<sha256>", ...}}

The files beside it are verbatim copies of `path` at `commit`. Local edits
belong in a separate skill, never in the copy: test_upstream_skills.py fails
when a file's hash differs from its pin.

    sync_upstream_skills.py            # report skills whose upstream moved
    sync_upstream_skills.py --update   # pull upstream HEAD and repin
    sync_upstream_skills.py --update socratic-tutor

Exit codes: 0 in sync (or updated), 1 upstream moved (check mode),
2 upstream unreachable ([DEGRADED], nothing changed).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "UPSTREAM.json"


def vendored_dirs(names: list[str]) -> list[Path]:
    dirs = sorted(p.parent for p in ROOT.glob(f"*/{PIN}"))
    if names:
        dirs = [d for d in dirs if d.name in names]
        missing = set(names) - {d.name for d in dirs}
        if missing:
            raise SystemExit(f"not vendored: {', '.join(sorted(missing))}")
    return dirs


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "skills-upstream-sync"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def upstream_head(repo: str) -> str:
    return json.loads(fetch(f"https://api.github.com/repos/{repo}/commits/HEAD"))["sha"]


def upstream_files(repo: str, path: str, commit: str) -> dict[str, bytes]:
    tree = json.loads(
        fetch(f"https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1")
    )
    if tree.get("truncated"):
        raise RuntimeError(f"{repo}@{commit}: tree listing truncated")
    prefix = path.rstrip("/") + "/"
    rels = [
        e["path"][len(prefix):]
        for e in tree["tree"]
        if e["type"] == "blob" and e["path"].startswith(prefix)
    ]
    if not rels:
        raise RuntimeError(f"{repo}@{commit}: no files under {path}")
    return {
        rel: fetch(f"https://raw.githubusercontent.com/{repo}/{commit}/{prefix}{rel}")
        for rel in sorted(rels)
    }


def update(skill: Path, pin: dict, head: str) -> None:
    files = upstream_files(pin["repo"], pin["path"], head)
    for rel in pin["files"]:
        if rel not in files:
            (skill / rel).unlink(missing_ok=True)
    for rel, data in files.items():
        if rel == PIN:
            raise RuntimeError(f"upstream ships its own {PIN}; refusing to overwrite the pin")
        dest = skill / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    pin["commit"] = head
    pin["files"] = {rel: sha256(data) for rel, data in files.items()}
    (skill / PIN).write_text(json.dumps(pin, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("names", nargs="*", help="skill directories (default: all vendored)")
    parser.add_argument("--update", action="store_true", help="pull upstream HEAD and repin")
    args = parser.parse_args()

    moved = degraded = False
    for skill in vendored_dirs(args.names):
        pin = json.loads((skill / PIN).read_text())
        try:
            head = upstream_head(pin["repo"])
            if head == pin["commit"]:
                print(f"OK {skill.name} @ {head[:7]}")
                continue
            if args.update:
                update(skill, pin, head)
                print(f"UPDATED {skill.name} -> {head[:7]}; review `git diff -- {skill.name}`")
            else:
                moved = True
                print(f"MOVED {skill.name}: pinned {pin['commit'][:7]}, upstream {head[:7]}")
        except (urllib.error.URLError, TimeoutError, RuntimeError, KeyError) as exc:
            degraded = True
            print(f"[DEGRADED] {skill.name}: {exc}", file=sys.stderr)
    if degraded:
        return 2
    return 1 if moved else 0


if __name__ == "__main__":
    raise SystemExit(main())
