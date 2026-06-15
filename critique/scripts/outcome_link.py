#!/usr/bin/env python3
"""Link critique findings to post-review git commits — closes the learning loop.

Maps CONFIRMED/CORRECTED findings (from findings.json + verified-disposition.md)
to commits that touched the cited file after the review run.

Tiered evidence (do not Goodhart on file-touch alone):
  linked_file   — any commit touched the cited path (weak candidate)
  linked_anchor — commit subject overlaps finding anchor words (evidence-grade)

Usage:
  outcome_link.py --repo . --review-dir .model-review/foo-abc123
  outcome_link.py --repo . --review-dir .model-review/foo --since HEAD~20
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

_ia_spec = importlib.util.spec_from_file_location(
    "integration_audit", Path(__file__).parent / "integration_audit.py"
)
assert _ia_spec and _ia_spec.loader
ia = importlib.util.module_from_spec(_ia_spec)
sys.modules["integration_audit"] = ia
_ia_spec.loader.exec_module(ia)

merge_records = ia.merge_records

VERDICT_OK = frozenset({"CONFIRMED", "CORRECTED"})
SIG_WORD = re.compile(r"[a-z0-9_]{4,}", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "LC_ALL": "C"},
    )
    if r.returncode != 0:
        return ""
    return r.stdout.strip()


def _norm_rel(repo: Path, path: str) -> str:
    p = path.strip().lstrip("./").replace("\\", "/")
    if not p:
        return ""
    full = repo / p
    if full.is_file():
        return p
    try:
        return full.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return p


def default_since(repo: Path, review_dir: Path) -> str | None:
    """Best-effort post-review window: HEAD~30 if repo has history."""
    if _git(repo, "rev-parse", "--is-inside-work-tree") != "true":
        return None
    depth = _git(repo, "rev-list", "--count", "HEAD")
    try:
        n = int(depth)
    except ValueError:
        return None
    if n <= 1:
        return None
    return f"HEAD~{min(30, max(1, n - 1))}"


def commits_touching_file(repo: Path, rel: str, since: str | None, limit: int = 12) -> list[dict]:
    if not rel:
        return []
    args = ["log", f"-{limit}", "--format=%H%x09%h%x09%s%x09%ci", "--", rel]
    if since:
        args = ["log", since + "..HEAD", "--format=%H%x09%h%x09%s%x09%ci", "--", rel]
    out = _git(repo, *args)
    rows: list[dict] = []
    for line in out.splitlines():
        parts = line.split("\t", 3)
        if len(parts) < 4:
            continue
        rows.append(
            {
                "sha": parts[0],
                "short": parts[1],
                "subject": parts[2],
                "date": parts[3],
            }
        )
    return rows


def anchor_overlap(commit_subject: str, title: str, fix: str) -> float:
    words = {w.lower() for w in SIG_WORD.findall(f"{title} {fix}")}
    words -= {"this", "that", "with", "from", "should", "file", "code", "fix"}
    if not words:
        return 0.0
    subj = commit_subject.lower()
    hits = sum(1 for w in words if w in subj)
    return hits / len(words)


def link_findings(
    repo: Path,
    review_dir: Path,
    *,
    since: str | None = None,
    anchor_overlap_min: float = 0.15,
) -> dict:
    if since is None:
        since = default_since(repo, review_dir)
    records = merge_records(review_dir)
    links: list[dict] = []
    for rec in records:
        if rec.verdict not in VERDICT_OK:
            continue
        rel = _norm_rel(repo, rec.file)
        commits = commits_touching_file(repo, rel, since)
        matched = [
            c
            for c in commits
            if anchor_overlap(c["subject"], rec.title, rec.fix) >= anchor_overlap_min
        ]
        linked_file = bool(commits)
        linked_anchor = bool(matched)
        links.append(
            {
                "finding_id": rec.num,
                "verdict": rec.verdict,
                "title": rec.title,
                "file": rel or rec.file,
                "fix": rec.fix,
                "commits_touching_file": commits,
                "commits_anchor_overlap": matched,
                "linked_file": linked_file,
                "linked_anchor": linked_anchor,
                # Evidence-grade only — never use file-touch alone for learning metrics.
                "linked": linked_anchor,
            }
        )
    anchor_linked = sum(1 for x in links if x["linked_anchor"])
    file_only = sum(1 for x in links if x["linked_file"] and not x["linked_anchor"])
    unlinked = sum(1 for x in links if not x["linked_file"])
    return {
        "generated_at": _now(),
        "repo": str(repo.resolve()),
        "review_dir": str(review_dir.resolve()),
        "since": since,
        "finding_links": links,
        "summary": {
            "actionable_findings": len(links),
            "linked_anchor": anchor_linked,
            "linked_file_only": file_only,
            "unlinked": unlinked,
            "linked": anchor_linked,
        },
    }


def cmd_link(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    review_dir = args.review_dir.resolve()
    if not (review_dir / "findings.json").is_file():
        print(f"no findings.json in {review_dir}", file=sys.stderr)
        return 2
    payload = link_findings(repo, review_dir, since=args.since)
    out_path = review_dir / "outcome-link.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        s = payload["summary"]
        print(
            f"Outcome link: {s['linked_anchor']} anchor / {s['linked_file_only']} file-only / "
            f"{s['unlinked']} unlinked → {out_path}"
        )
        for row in payload["finding_links"]:
            if row["linked_anchor"]:
                mark = "✓"
            elif row["linked_file"]:
                mark = "~"
            else:
                mark = "?"
            n = len(row["commits_anchor_overlap"]) or len(row["commits_touching_file"])
            print(f"  {mark} #{row['finding_id']} [{row['verdict']}] {row['title'][:55]} ({n} commit(s))")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Link critique findings to post-review git commits.")
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--review-dir", type=Path, required=True)
    ap.add_argument("--since", default=None, help="Git rev for log range (e.g. HEAD~30 or <sha>)")
    ap.add_argument("--json", action="store_true")
    ap.set_defaults(func=cmd_link)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
