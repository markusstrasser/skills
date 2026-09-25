#!/usr/bin/env python3
"""Blind-reader test: does a figure answer its questions better than the prose alone?

A fresh reader (Claude CLI in --safe-mode: no CLAUDE.md, hooks or skills) sees one
arm of each item -- an image or a text -- and answers pre-registered questions.
Answers are graded deterministically against values taken from the data, never
from the rendered figure. Token use is reported per arm.

Spec (JSON):
{
  "reader": "sonnet",                      # optional, any `claude --model` value
  "items": [{
    "id": "matrix",
    "arms": {"full":  {"image": "matrix.png"},
             "prose": {"text_file": "matrix.prose.txt"},
             "chart": {"image": "matrix.chart.png"}},
    "questions": [
      {"id": "q1", "q": "...", "kind": "number", "answer": 102, "tol": 2, "role": "claim"},
      {"id": "q2", "q": "...", "kind": "range",  "answer": [303, 325], "tol": 2},
      {"id": "q3", "q": "...", "kind": "choice", "options": ["a", "b"], "answer": "a"}
    ]
  }]
}
Paths are relative to the spec file. Arm names are free; `prose` and `full` feed
the verdict. Tag each question with a `role`: `claim` (the takeaway the figure asserts),
`lookup` (a specific value) or `shape` (a pattern, crossing or trend). A chart earns its
place when `full` beats `prose` on claims, or on lookups/shape the reader actually needs.

Usage: blind_read.py SPEC.json [--repeats N] [--workers N] [--out DIR]
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROMPT = """You are shown one piece of material and nothing else. Answer every question from that
material alone; do not use outside knowledge. If the material does not let you answer a question,
give null for it -- a null is better than a guess.

Answer formats: "number" -> a single number; "range" -> [low, high]; "choice" -> one of the listed
options, copied exactly. Numbers are plain (no units, no $ or %, no thousands separators).

{material}

Questions:
{questions}

Reply with only a JSON object mapping question id to answer, e.g. {{"q1": 12, "q2": [3, 5]}}."""


def fmt_questions(qs: list[dict]) -> str:
    lines = []
    for q in qs:
        extra = f" Options: {q['options']}." if q["kind"] == "choice" else ""
        lines.append(f"- {q['id']} ({q['kind']}): {q['q']}{extra}")
    return "\n".join(lines)


def parse_answers(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _num(x) -> float | None:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).replace(",", "").replace("$", "").replace("%", "").strip())
    except ValueError:
        return None


def grade(q: dict, a) -> str:
    """Return 'ok', 'wrong' or 'null'."""
    if a is None:
        return "null"
    tol = q.get("tol", 0)
    if q["kind"] == "number":
        v = _num(a)
        return "ok" if v is not None and abs(v - q["answer"]) <= tol else "wrong"
    if q["kind"] == "range":
        if not isinstance(a, (list, tuple)) or len(a) != 2:
            return "wrong"
        vals = [_num(x) for x in a]
        if None in vals:
            return "wrong"
        lo, hi = sorted(v for v in vals if v is not None)
        return "ok" if abs(lo - q["answer"][0]) <= tol and abs(hi - q["answer"][1]) <= tol else "wrong"
    if q["kind"] == "choice":
        return "ok" if str(a).strip().lower() == str(q["answer"]).strip().lower() else "wrong"
    raise ValueError(f"unknown kind {q['kind']!r}")


def run_reader(arm: dict, qs: list[dict], base: Path, model: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="blind-read-") as td:
        if "image" in arm:
            src = base / arm["image"]
            if not src.is_file():
                raise FileNotFoundError(src)
            shutil.copy(src, Path(td) / f"material{src.suffix}")
            material = f"The material is the image ./material{src.suffix}. Read it with the Read tool."
            tools = ["--allowedTools", "Read"]
        else:
            text = arm.get("text") or (base / arm["text_file"]).read_text()
            material = f"The material is this text:\n<material>\n{text.strip()}\n</material>"
            tools = ["--tools", ""]
        prompt = PROMPT.format(material=material, questions=fmt_questions(qs))
        # Prompt goes on stdin: --allowedTools/--tools are variadic and swallow a positional prompt.
        cmd = ["claude", "--safe-mode", "-p", "--model", model, "--output-format", "json",
               "--max-turns", "4", *tools]
        t0 = time.time()
        p = subprocess.run(cmd, cwd=td, capture_output=True, text=True, input=prompt, timeout=300)
        wall = time.time() - t0
    if p.returncode != 0:
        return {"error": f"rc={p.returncode}: {p.stderr.strip()[-300:]}", "wall_s": wall}
    d = json.loads(p.stdout)
    u = d.get("usage") or {}
    return {
        "raw": d.get("result"),
        "is_error": d.get("is_error"),
        "in_tok": sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")),
        "out_tok": u.get("output_tokens"),
        "reason_tok": (u.get("output_tokens_details") or {}).get("thinking_tokens"),
        "cost_usd": d.get("total_cost_usd"),
        "wall_s": round(wall, 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("spec", type=Path)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, help="default: <spec dir>/blind-read-out")
    ap.add_argument("--from-results", action="store_true",
                    help="regrade <out>/results.jsonl against the spec without calling the reader")
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text())
    base = args.spec.resolve().parent
    model = spec.get("reader", "sonnet")
    out = args.out or base / "blind-read-out"
    out.mkdir(parents=True, exist_ok=True)

    if args.from_results:
        rows = [json.loads(line) for line in (out / "results.jsonl").read_text().splitlines() if line]
        qmap = {it["id"]: it["questions"] for it in spec["items"]}
        for row in rows:
            if row.get("answers") is not None:
                row["grades"] = {q["id"]: grade(q, row["answers"].get(q["id"])) for q in qmap[row["item"]]}
        repeats = 1 + max((r["rep"] for r in rows), default=0)
        summary = render_summary(spec, rows, model, repeats)
        (out / "summary.md").write_text(summary)
        print(summary)
        return 0

    jobs = [(it, name, arm, r) for it in spec["items"] for name, arm in it["arms"].items()
            for r in range(args.repeats)]
    rows: list[dict] = []
    with cf.ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(run_reader, arm, it["questions"], base, model): (it, name, r)
                for it, name, arm, r in jobs}
        for f in cf.as_completed(futs):
            it, name, r = futs[f]
            res = f.result()
            answers = parse_answers(res.get("raw", "")) if "error" not in res else None
            grades = {q["id"]: ("error" if answers is None else grade(q, answers.get(q["id"])))
                      for q in it["questions"]}
            row = {"item": it["id"], "arm": name, "rep": r, "answers": answers, "grades": grades, **res}
            rows.append(row)
            print(f"{it['id']:<14} {name:<8} rep{r} " + " ".join(f"{k}:{v}" for k, v in grades.items()),
                  file=sys.stderr)

    (out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    failed = [r for r in rows if "error" in r or r["answers"] is None]
    summary = render_summary(spec, rows, model, args.repeats)
    (out / "summary.md").write_text(summary)
    print(summary)
    if failed:
        print(f"[DEGRADED] {len(failed)} reader call(s) failed or returned no JSON; see results.jsonl",
              file=sys.stderr)
        return 1
    return 0


def role_acc(it: dict, rows: list[dict], arm: str, role: str) -> float | None:
    qids = {q["id"] for q in it["questions"] if q.get("role", "untagged") == role}
    g = [v for r in rows if r["item"] == it["id"] and r["arm"] == arm for k, v in r["grades"].items() if k in qids]
    return g.count("ok") / len(g) if g else None


def verdict(it: dict, rows: list[dict]) -> str:
    """Per-role comparison of the full section against its prose. Advisory: whether the reader
    needs the lookups/shape the chart carries is the author's call, not the script's."""
    if not {"full", "prose"} <= set(it["arms"]):
        return f"- **{it['id']}**: needs `full` and `prose` arms for a verdict"
    parts, carries = [], {}
    for role in ("claim", "lookup", "shape", "untagged"):
        f, p = role_acc(it, rows, "full", role), role_acc(it, rows, "prose", role)
        if f is None or p is None:
            continue
        carries[role] = f - p > 0.15
        parts.append(f"{role}: full {f:.0%} / prose {p:.0%}")
    if carries.get("claim"):
        v = "the chart carries the takeaway itself; keep it"
    elif any(carries.get(r) for r in ("lookup", "shape", "untagged")):
        v = "prose carries the takeaway; keep the chart only if readers need the lookups/shape it adds"
    else:
        v = "prose answers everything asked; a sentence will do"
    chart = role_acc(it, rows, "chart", "claim")
    tail = f" (chart alone on claims: {chart:.0%})" if chart is not None else ""
    return f"- **{it['id']}**: {'; '.join(parts)} -> {v}{tail}"


def render_summary(spec: dict, rows: list[dict], model: str, repeats: int) -> str:
    lines = [f"# Blind-read results (reader: {model}, repeats: {repeats})", "",
             "| item | arm | correct | null | wrong | in_tok | out_tok | reason_tok | wall_s |",
             "|---|---|---|---|---|---|---|---|---|"]
    verdicts = []
    for it in spec["items"]:
        acc = {}
        errored = any(v == "error" for r in rows if r["item"] == it["id"] for v in r["grades"].values())
        for name in it["arms"]:
            rs = [r for r in rows if r["item"] == it["id"] and r["arm"] == name]
            g = [v for r in rs for v in r["grades"].values()]
            n = len(g) or 1
            acc[name] = g.count("ok") / n

            def avg(k):
                vals = [float(v) for r in rs if (v := r.get(k)) is not None]
                return round(sum(vals) / len(vals)) if vals else "-"
            lines.append(f"| {it['id']} | {name} | {g.count('ok')}/{len(g)} | {g.count('null')} | "
                         f"{g.count('wrong') + g.count('error')} | {avg('in_tok')} | {avg('out_tok')} | "
                         f"{avg('reason_tok')} | {avg('wall_s')} |")
        if errored:
            verdicts.append(f"- **{it['id']}**: [DEGRADED] reader errors; no verdict")
            continue
        verdicts.append(verdict(it, rows))
    per_q = ["", "## Per question (share correct by arm)", ""]
    for it in spec["items"]:
        for q in it["questions"]:
            cells = []
            for name in it["arms"]:
                g = [r["grades"][q["id"]] for r in rows if r["item"] == it["id"] and r["arm"] == name]
                cells.append(f"{name} {g.count('ok')}/{len(g)}")
            per_q.append(f"- {it['id']}.{q['id']} ({q['q'][:70]}): " + ", ".join(cells))
    return "\n".join(lines + ["", "## Verdicts (advisory)", ""] + verdicts + per_q) + "\n"


if __name__ == "__main__":
    sys.exit(main())
