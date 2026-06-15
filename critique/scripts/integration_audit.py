#!/usr/bin/env python3
"""Post-review integration audit — deterministic gate for /critique close.

Checks whether git changes after model-review plausibly implement findings marked
HALLUCINATED in verified-disposition.md. Report-only by default; --strict exits 1.

Tier 1 only (no LLM). Consumes artifacts the review pipeline already writes.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.git_context import diff_ref, run_git  # noqa: E402

VERDICT_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*(CONFIRMED|CORRECTED|HALLUCINATED|INCONCLUSIVE)\s*\|\s*(.+?)\s*\|",
    re.I,
)
STOP = frozenset(
    "a an the and or but if in on at to for of is are was be with from as by it this that".split()
)
SIG_WORD = re.compile(r"[a-z0-9_]{4,}", re.I)


@dataclass
class FindingRecord:
    num: int
    verdict: str
    title: str
    file: str
    fix: str
    notes: str = ""


@dataclass
class AuditResult:
    review_dir: Path
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def exit_code(self, strict: bool) -> int:
        if self.failures:
            return 1
        if strict and self.warnings:
            return 1
        return 0


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def parse_verified_disposition(path: Path) -> dict[int, dict[str, str]]:
    if not path.is_file():
        return {}
    out: dict[int, dict[str, str]] = {}
    for line in path.read_text().splitlines():
        m = VERDICT_ROW.match(line.strip())
        if not m:
            continue
        num = int(m.group(1))
        out[num] = {
            "verdict": m.group(2).upper(),
            "claim": m.group(3).strip(),
            "notes": "",
        }
    return out


def load_findings(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        return data.get("findings", []) or []
    return data if isinstance(data, list) else []


def merge_records(review_dir: Path) -> list[FindingRecord]:
    vd = parse_verified_disposition(review_dir / "verified-disposition.md")
    findings = load_findings(review_dir / "findings.json")
    records: list[FindingRecord] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        num = int(f.get("id") or f.get("num") or 0)
        title = str(f.get("title") or f.get("claim") or "").strip()
        if not title and num in vd:
            title = vd[num]["claim"]
        verdict = vd.get(num, {}).get("verdict", "UNVERIFIED")
        records.append(
            FindingRecord(
                num=num,
                verdict=verdict,
                title=title,
                file=str(f.get("file") or "").strip(),
                fix=str(f.get("fix") or "").strip(),
                notes=vd.get(num, {}).get("notes", ""),
            )
        )
    # disposition rows without findings.json entries
    for num, row in vd.items():
        if any(r.num == num for r in records):
            continue
        records.append(
            FindingRecord(
                num=num,
                verdict=row["verdict"],
                title=row["claim"],
                file="",
                fix="",
                notes=row.get("notes", ""),
            )
        )
    return records


def _significant_phrases(text: str, min_words: int = 4) -> list[str]:
    words = [w.lower() for w in SIG_WORD.findall(text) if w.lower() not in STOP]
    phrases: list[str] = []
    for i in range(0, max(0, len(words) - min_words + 1)):
        chunk = words[i : i + min_words]
        if len(chunk) >= min_words:
            phrases.append(" ".join(chunk))
    return phrases


def _basename(path: str) -> str:
    return Path(path).name if path else ""


def collect_diff(repo: Path, base: str | None, head: str | None) -> tuple[str, set[str]]:
    ref = diff_ref(base, head)
    try:
        if ref:
            names = run_git(repo, ["diff", "--name-only", ref]).splitlines()
            text = run_git(repo, ["diff", ref])
        else:
            names = run_git(repo, ["diff", "--name-only", "HEAD"]).splitlines()
            names += run_git(repo, ["diff", "--name-only", "--cached"]).splitlines()
            text = run_git(repo, ["diff", "HEAD"]) + "\n" + run_git(repo, ["diff", "--cached"])
    except RuntimeError:
        names, text = [], ""
    files = {n.strip() for n in names if n.strip()}
    return text, files


def collect_commit_log(repo: Path, base: str | None, head: str | None) -> str:
    ref = diff_ref(base, head)
    try:
        if ref:
            return run_git(repo, ["log", "--format=%s%n%b", ref])
        return run_git(repo, ["log", "-5", "--format=%s%n%b"])
    except RuntimeError:
        return ""


def audit(
    review_dir: Path,
    repo: Path,
    *,
    base: str | None,
    head: str | None,
    plan_path: Path | None,
) -> AuditResult:
    result = AuditResult(review_dir=review_dir)
    if not review_dir.is_dir():
        result.failures.append(f"review dir not found: {review_dir}")
        return result

    vd_path = review_dir / "verified-disposition.md"
    fj_path = review_dir / "findings.json"
    if not vd_path.exists() and not fj_path.exists():
        result.warnings.append("no verified-disposition.md or findings.json — skip integration audit")
        return result
    if not vd_path.exists():
        result.warnings.append("verified-disposition.md missing — audit uses findings only (unverified)")

    records = merge_records(review_dir)
    hallucinated = [r for r in records if r.verdict == "HALLUCINATED"]
    if not hallucinated:
        return result

    diff_text, diff_files = collect_diff(repo, base, head)
    corpus = "\n".join([diff_text, collect_commit_log(repo, base, head)])
    if plan_path and plan_path.is_file():
        corpus += "\n" + plan_path.read_text()

    corpus_l = corpus.lower()
    confirmed_files = {
        _basename(r.file)
        for r in records
        if r.verdict in ("CONFIRMED", "CORRECTED") and r.file
    }

    for r in hallucinated:
        title_l = _norm(r.title)
        if title_l and title_l in corpus_l:
            result.failures.append(
                f"#{r.num} HALLUCINATED claim title appears in diff/commits/plan: {r.title[:80]}"
            )

        for phrase in _significant_phrases(r.fix):
            if phrase in corpus_l:
                result.failures.append(
                    f"#{r.num} HALLUCINATED fix phrasing in diff/commits/plan: …{phrase}…"
                )
                break

        bname = _basename(r.file)
        if bname and bname in {_basename(f) for f in diff_files} and bname not in confirmed_files:
            result.warnings.append(
                f"#{r.num} HALLUCINATED-only file touched in diff: {r.file or bname}"
            )

    return result


def render_report(result: AuditResult) -> str:
    lines = [f"Integration audit — {result.review_dir}"]
    if result.failures:
        lines.append(f"FAIL ({len(result.failures)})")
        lines.extend(f"  - {f}" for f in result.failures)
    else:
        lines.append("PASS — no HALLUCINATED finding integrated in diff/commits/plan")
    if result.warnings:
        lines.append(f"WARN ({len(result.warnings)})")
        lines.extend(f"  - {w}" for w in result.warnings)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Post-review integration audit (deterministic).")
    ap.add_argument("--review-dir", type=Path, required=True)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--base", default=None, help="git base for diff (e.g. session commit range)")
    ap.add_argument("--head", default=None)
    ap.add_argument("--plan", type=Path, default=None, help="plan file to scan for adopted claims")
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    result = audit(
        args.review_dir.resolve(),
        args.repo.resolve(),
        base=args.base,
        head=args.head,
        plan_path=args.plan,
    )
    report = render_report(result)
    if args.as_json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "failures": result.failures,
                    "warnings": result.warnings,
                    "review_dir": str(result.review_dir),
                },
                indent=2,
            )
        )
    else:
        print(report)
    return result.exit_code(args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
