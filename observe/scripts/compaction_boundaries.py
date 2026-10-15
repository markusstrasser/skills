#!/usr/bin/env python3
"""Deterministic compaction-boundary lane: does the session recover well after each compaction?

For every compact_boundary in recent Claude Code transcripts, measures:
  contract    summary carries the PreCompact contract (re-read section + lossy banner;
              skills/hooks/precompact-instructions.py, shipped 2026-10-15)
  carry12     share of the previous summary's 12-word shingles found in this one
              (low = each summary re-paraphrases the last, so details drift)
  refs        paths the next turn should re-open: compact_file_reference attachments
              (path only, no content) plus paths in the summary's re-read section
  reread      share of refs actually opened (Read/Grep/Bash naming the path) within the
              next WINDOW tool calls; CliffCompaction (arXiv 2609.26779 App. C.1) found
              paraphrased summaries suppress exactly this
  unread_err  Edit/Write errors "has not been read"/"modified since read" in that window

Split by contract vs no-contract so the hook's effect is a before/after read, not a guess.
Raw transcripts are read-only. Usage: compaction_boundaries.py [--days N] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from pathlib import Path

ROOT = Path.home() / ".claude" / "projects"
WINDOW = 50  # tool calls after the boundary that count as "the resume"
CONTRACT_MARK = "re-read before relying on details"
PATH_RE = re.compile(r"(?:~|\.{0,2})?/?(?:[\w.@-]+/)+[\w.@-]+\.\w{1,8}")
UNREAD_RE = re.compile(r"has not been read|modified since (?:it was )?read", re.I)


def shingles(text: str, n: int = 12) -> set[str]:
    w = text.split()
    return {" ".join(w[i : i + n]) for i in range(max(0, len(w) - n + 1))}


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return ""


def reread_section_paths(summary: str) -> set[str]:
    low = summary.lower()
    at = low.find(CONTRACT_MARK)
    if at < 0:
        return set()
    return set(PATH_RE.findall(summary[at : at + 3000]))


def touches(tool: dict, path: str) -> bool:
    inp = tool.get("input") or {}
    name = Path(path).name
    for key in ("file_path", "path", "notebook_path"):
        v = inp.get(key)
        if isinstance(v, str) and (v == path or v.endswith("/" + path.lstrip("./~")) or Path(v).name == name and "/" not in path):
            return True
    cmd = inp.get("command")
    return isinstance(cmd, str) and (path in cmd or (len(name) > 6 and name in cmd))


def boundaries(path: Path) -> list[dict]:
    out: list[dict] = []
    cur: dict | None = None
    prev_summary = ""
    tools_seen = 0
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return out
    for line in lines:
        if '"compact_boundary"' in line or '"isCompactSummary"' in line or cur is not None:
            try:
                d = json.loads(line)
            except ValueError:
                continue
        else:
            continue
        if d.get("subtype") == "compact_boundary":
            meta = d.get("compactMetadata") or {}
            cur = {"session": path.stem, "project": path.parent.name, "path": str(path), "ts": d.get("timestamp", ""),
                   "trigger": meta.get("trigger"), "pre": meta.get("preTokens"),
                   "summary": "", "refs": set(), "restored": set(), "opened": set(), "unread_err": 0}
            out.append(cur)
            tools_seen = 0
            continue
        if cur is None:
            continue
        if d.get("isCompactSummary"):
            cur["summary"] = text_of((d.get("message") or {}).get("content"))
            cur["carry12"] = (
                len(shingles(prev_summary) & shingles(cur["summary"])) / max(1, len(shingles(prev_summary)))
                if prev_summary else None
            )
            prev_summary = cur["summary"]
            cur["refs"] |= reread_section_paths(cur["summary"])
            continue
        att = d.get("attachment") or {}
        if att.get("type") == "compact_file_reference" and att.get("filename"):
            cur["refs"].add(att["filename"])
        elif att.get("type") == "file" and att.get("filename"):
            cur["restored"].add(att["filename"])
        content = (d.get("message") or {}).get("content")
        if not isinstance(content, list) or tools_seen >= WINDOW:
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                tools_seen += 1
                for ref in cur["refs"]:
                    if touches(block, ref):
                        cur["opened"].add(ref)
            elif block.get("type") == "tool_result" and block.get("is_error"):
                if UNREAD_RE.search(text_of(block.get("content"))):
                    cur["unread_err"] += 1
    return out


def finish(b: dict) -> dict:
    s = b.pop("summary")
    refs = b.pop("refs") - b["restored"]
    opened = b.pop("opened") & refs
    b.pop("restored")
    b.update(summary_chars=len(s), contract=CONTRACT_MARK in s.lower() and "lossy" in s[:400].lower(),
             refs=len(refs), reread=(len(opened) / len(refs)) if refs else None,
             unopened=sorted(refs - opened)[:10])
    return b


def summarize(rows: list[dict]) -> dict:
    def med(key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return round(statistics.median(vals), 3) if vals else None
    return {"n": len(rows), "carry12_med": med("carry12"), "reread_med": med("reread"),
            "refs_med": med("refs"), "summary_chars_med": med("summary_chars"),
            "unread_err": sum(r["unread_err"] for r in rows)}


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--days", type=float, default=14)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    cutoff = time.time() - args.days * 86400
    # main sessions plus subagents (<project>/<session>/subagents/*.jsonl compact too)
    files = [p for p in ROOT.rglob("*.jsonl") if p.stat().st_mtime >= cutoff]
    rows = [finish(b) for p in files for b in boundaries(p)]
    rows = [r for r in rows if r["ts"] >= time.strftime("%Y-%m-%d", time.gmtime(cutoff))]
    report = {"scanned": len(files), "boundaries": len(rows),
              "with_summary": sum(1 for r in rows if r["summary_chars"]),
              "contract": summarize([r for r in rows if r["contract"]]),
              "no_contract": summarize([r for r in rows if not r["contract"] and r["summary_chars"]])}
    if args.json:
        print(json.dumps({**report, "rows": rows}, default=list))
        return 0
    print(f"scanned {report['scanned']} transcripts · {report['boundaries']} boundaries "
          f"({report['with_summary']} with summary) · last {args.days:g}d")
    print(f"{'arm':<12}{'n':>6}{'carry12':>9}{'reread':>8}{'refs':>6}{'chars':>8}{'unread_err':>11}")
    for arm in ("contract", "no_contract"):
        r = report[arm]
        print(f"{arm:<12}{r['n']:>6}{r['carry12_med']!s:>9}{r['reread_med']!s:>8}"
              f"{r['refs_med']!s:>6}{r['summary_chars_med']!s:>8}{r['unread_err']:>11}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
