#!/usr/bin/env python3
"""item_analysis.py — psychometric item analysis over an eval response matrix.

Mechanizes eval-skill Phase 4.5 checks #1 (outliers-first) and #2 (gold validity):
instead of "the agent should list per-item scores and notice the outlier", it
computes per-item difficulty + discrimination over the (model x item) response
matrix and ranks the items you MUST trace-audit before any verdict.

WHY THIS EXISTS — recurrence (the self-improvement bar):
  - 2026-06-13 phenome KG-verifier: trusted the aggregate, committed a wrong verdict.
  - 2026-06-14 Composer: scored 0/33 on `diekstra` and was ranked "mid-pack" until a
    manual trace audit found the 0 was CORRECT (it dropped methodology claims the
    contaminated gold wrongly kept). Item analysis flags `diekstra` mechanically:
    it is the lowest-discrimination, highest-top-dispersion item in the set.

METHOD (classical test theory; IRT-lite). Converged from 7 candidates — full
2PL/3PL/4PL IRT, DIF, Mokken-H, Bayesian-IRT, leave-one-out influence, CTT
discrimination, top-model dispersion. At our N (5-15 models x 3-100 items) full
IRT is underpowered (SEs too large <20 models x <100 items — frontier-discrimination.md);
v1 ships the small-N-robust signals, with IRT as the upgrade path once an item bank
is calibrated (tinyBenchmarks 2402.14992 / LEGO-IRT 2510.04051):
  difficulty       = mean normalized score over models (->1 ceiling / ->0 floor = ~0 info)
  discrimination   = corrected item-total correlation (item score vs LEAVE-ONE-OUT ability)
                     r < 0  => mis-keyed / contaminated gold (4PL negative-discrim signature)
  top_dispersion   = stdev of scores among the top-half-ability models (high = the strong
                     models DISAGREE on this item = ambiguous gold or genuine capability split)
  top_in_bottom    = the single highest-ability model lands in the bottom half on this item

OUTPUT is a directed "inspect these items" list, NOT a verdict. At small N every
flag is a LEAD for a trace audit, never a conclusion. Scores are normalized per
`scale_max` so a 0-3 faithfulness scale and a 0-1 recall scale are comparable
(the throwaway probe's first bug: a 0-1 ceiling threshold applied to 0-3 data).

Input: long-format JSONL, one row per cell:
    {"model": "...", "item": "...", "score": <float>, "scale_max": <float, default 1.0>}
Built-in adapters for the extraction_bakeoff formats:
    --adapter phenome  judge_phenome_results.jsonl   (score = covered/gold_total, scale 1)
    --adapter intel    judge_intel_results.jsonl     (score = mean_faith, scale 3, judge-mean)

Usage:
    item_analysis.py matrix.jsonl
    item_analysis.py --adapter phenome judge_phenome_results.jsonl
    item_analysis.py --adapter phenome judge_phenome_results.jsonl --json   # machine-readable
Stdlib only. Exit 0 always (advisory tool); --strict exits 3 if any item is flagged.
"""
from __future__ import annotations
import argparse, json, sys
from statistics import mean, pstdev

MIN_MODELS_POWERED = 8   # below this: directional only, no IRT params
MIN_ITEMS_POWERED = 5


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def load_long(path):
    cells = {}
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        sm = float(r.get("scale_max", 1.0)) or 1.0
        cells[(r["model"], r["item"])] = float(r["score"]) / sm
    return cells


def load_phenome(path):
    cells = {}
    for line in open(path):
        r = json.loads(line)
        gt = float(r["gold_total"])
        cells[(r["model"], r["slug"])] = (float(r["covered"]) / gt) if gt else 0.0
    return cells


def load_intel(path):
    raw = {}
    for line in open(path):
        r = json.loads(line)
        raw.setdefault((r["model"], r["slug"]), []).append(float(r["mean_faith"]) / 3.0)
    return {k: mean(v) for k, v in raw.items()}


ADAPTERS = {"long": load_long, "phenome": load_phenome, "intel": load_intel}


def analyze(cells):
    models = sorted({m for m, _ in cells})
    items = sorted({i for _, i in cells})
    ability = {}
    for m in models:
        vals = [cells[(m, it)] for it in items if (m, it) in cells]
        ability[m] = mean(vals) if vals else 0.0
    n_items = len(items)

    rows = []
    for it in items:
        present = [m for m in models if (m, it) in cells]
        item_scores, loo = [], {}
        for m in present:
            others = [cells[(m, o)] for o in items if o != it and (m, o) in cells]
            loo[m] = mean(others) if others else ability[m]
            item_scores.append(cells[(m, it)])
        difficulty = mean(item_scores) if item_scores else float("nan")
        r = pearson(item_scores, [loo[m] for m in present])
        # robust small-N signals
        ranked_by_ability = sorted(present, key=lambda m: loo[m], reverse=True)
        top_half = ranked_by_ability[: max(1, len(ranked_by_ability) // 2)]
        top_disp = pstdev([cells[(m, it)] for m in top_half]) if len(top_half) > 1 else 0.0
        top_model = ranked_by_ability[0]
        item_sorted = sorted(present, key=lambda m: cells[(m, it)])
        top_in_bottom = top_model in item_sorted[: max(1, len(item_sorted) // 2)]

        flag, reason = "", ""
        if r is not None and r < 0:
            flag, reason = "INSPECT-GOLD", f"negative discrimination (r={r:+.2f}): best models score worst — mis-keyed/contaminated gold?"
        elif difficulty > 0.9:
            flag, reason = "CEILING", f"difficulty {difficulty:.2f} — ~0 information, prune or replace"
        elif difficulty < 0.1:
            flag, reason = "FLOOR", f"difficulty {difficulty:.2f} — ~0 information or all-fail (check task/gold)"
        elif r is not None and r < 0.15:
            flag, reason = "LOW-DISCRIM", f"discrimination r={r:+.2f} (<0.15) — separates models weakly"
        elif top_disp > 0.25:
            flag, reason = "TOP-DISPERSION", f"high-ability models disagree (top stdev {top_disp:.2f}) — ambiguous gold or capability split"
        # anomaly score for ranking the inspect list (higher = inspect sooner)
        anom = (-(r) if r is not None else 0.0) + top_disp + (0.5 if top_in_bottom else 0.0)
        rows.append({
            "item": it, "difficulty": round(difficulty, 3),
            "discrimination": (round(r, 3) if r is not None else None),
            "top_dispersion": round(top_disp, 3), "top_in_bottom": top_in_bottom,
            "n_models": len(present), "flag": flag, "reason": reason,
            "anomaly": round(anom, 3),
        })
    rows.sort(key=lambda x: x["anomaly"], reverse=True)
    return {
        "n_models": len(models), "n_items": n_items,
        "powered": len(models) >= MIN_MODELS_POWERED and n_items >= MIN_ITEMS_POWERED,
        "models": models, "items": items,
        "ability": {m: round(a, 3) for m, a in sorted(ability.items(), key=lambda x: -x[1])},
        "matrix": {f"{m}|{it}": round(cells[(m, it)], 3) for (m, it) in cells},
        "item_stats": rows,
        "flagged": [r["item"] for r in rows if r["flag"]],
    }


def render(res):
    out = []
    pw = "POWERED" if res["powered"] else "DIRECTIONAL (underpowered)"
    out.append(f"item analysis — {res['n_models']} models x {res['n_items']} items — {pw}")
    if not res["powered"]:
        out.append(f"  N below powered floor ({MIN_MODELS_POWERED} models x {MIN_ITEMS_POWERED} items): "
                   "flags are LEADS for trace audit, NOT verdicts. No IRT params fit at this N.")
    out.append("\n  model ability (mean normalized score, descending):")
    for m, a in res["ability"].items():
        out.append(f"    {a:.2f}  {m}")
    out.append("\n  item            difficulty  discrim   top_disp  flag")
    out.append("  " + "-" * 62)
    for r in res["item_stats"]:
        d = f"{r['discrimination']:+.2f}" if r["discrimination"] is not None else " n/a"
        out.append(f"  {r['item'][:14].ljust(14)}  {r['difficulty']:9.2f}  {d.center(7)}  {r['top_dispersion']:7.2f}   {r['flag']}")
    flagged = [r for r in res["item_stats"] if r["flag"]]
    if flagged:
        out.append("\n  >> INSPECT (trace-audit before any verdict), most-anomalous first:")
        for r in flagged:
            out.append(f"     [{r['flag']}] {r['item']} — {r['reason']}")
    else:
        out.append("\n  >> no items flagged. (Still read >=1 trace/arm — absence of a flag is not validity.)")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Psychometric item analysis over an eval response matrix.")
    ap.add_argument("path")
    ap.add_argument("--adapter", choices=list(ADAPTERS), default="long")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--strict", action="store_true", help="exit 3 if any item is flagged")
    a = ap.parse_args()
    cells = ADAPTERS[a.adapter](a.path)
    if not cells:
        print("no cells parsed", file=sys.stderr); return 0
    res = analyze(cells)
    print(json.dumps(res, indent=2) if a.json else render(res))
    return 3 if (a.strict and res["flagged"]) else 0


if __name__ == "__main__":
    sys.exit(main())
