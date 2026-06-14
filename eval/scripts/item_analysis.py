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
  discrimination   = corrected item-total correlation (item score vs LEAVE-ONE-OUT ability),
                     computed by ITERATIVE PURIFICATION: a mis-keyed item contaminates the
                     ability criterion at tiny N and would flip CLEAN items negative too, so
                     each round we flag the most-negative item, remove it from the basis, and
                     recompute the remaining items' r against the de-contaminated basis. A
                     surviving r < 0 => mis-keyed / contaminated gold (4PL negative-discrim).
  top_dispersion   = stdev of scores among the top-half-ability models (high = the strong
                     models DISAGREE on this item = ambiguous gold or capability split)
  top_in_bottom    = the single highest-ability model lands in the bottom half on this item

OUTPUT is a directed "inspect these items" list, NOT a verdict. At small N every
flag is a LEAD for a trace audit, never a conclusion (the contract: flags are always
leads; `powered` only governs whether you may make a QUANTITATIVE claim from them).
Scores are normalized per `scale_max` so a 0-3 faithfulness scale and a 0-1 recall
scale are comparable (the throwaway probe's first bug: a 0-1 ceiling threshold on
0-3 data). A non-positive scale_max / gold_total is bad data — fail loud, don't coerce.

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
CEILING = 0.9            # difficulty above this => ~0 information
FLOOR = 0.1             # difficulty below this => ~0 information / all-fail
LOW_DISCRIM = 0.15      # positive-but-weak discrimination
DISPERSION = 0.25       # heuristic: top-half stdev above this = high-ability disagreement


def pearson(xs, ys):
    n = len(xs)
    if n < 3:            # cannot correlate < 3 points
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:   # degenerate variance -> undefined, not a misleading 0
        return None
    return num / (dx * dy)


def _norm(score, scale_max):
    sm = float(scale_max)
    if sm <= 0:          # non-positive scale is bad data — fail loud (don't /1.0 or flip sign)
        raise ValueError(f"scale_max must be > 0, got {sm}")
    return float(score) / sm


def load_long(path):
    cells = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            cells[(r["model"], r["item"])] = _norm(r["score"], r.get("scale_max", 1.0))
    return cells


def load_phenome(path):
    cells = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            gt = float(r["gold_total"])
            if gt <= 0:      # a non-positive gold total is bad data, not difficulty 0.0
                raise ValueError(f"gold_total must be > 0 for {r.get('slug')}, got {gt}")
            cells[(r["model"], r["slug"])] = float(r["covered"]) / gt
    return cells


def load_intel(path):
    raw = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            raw.setdefault((r["model"], r["slug"]), []).append(_norm(r["mean_faith"], 3.0))
    return {k: mean(v) for k, v in raw.items()}


ADAPTERS = {"long": load_long, "phenome": load_phenome, "intel": load_intel}


def _corrected_r(cells, models, it, basis):
    """Corrected item-total r: item score vs each model's mean over the BASIS items
    (excluding `it` itself, and excluding ragged models with no basis cell — never
    substitute the contaminated global ability)."""
    if len(basis) < 2:           # need >=2 items so the leave-one-out basis is non-empty
        return None
    xs, ys = [], []
    for m in models:
        if (m, it) not in cells:
            continue
        others = [cells[(m, o)] for o in basis if o != it and (m, o) in cells]
        if not others:           # ragged model — exclude from the correlation (fixes H1/L1)
            continue
        xs.append(cells[(m, it)])
        ys.append(mean(others))
    return pearson(xs, ys)


def analyze(cells):
    models = sorted({m for m, _ in cells})
    items = sorted({i for _, i in cells})
    ability = {}
    for m in models:
        vals = [cells[(m, it)] for it in items if (m, it) in cells]
        ability[m] = mean(vals) if vals else 0.0

    # Iterative purification (fixes C1): flag the most-negative item, drop it from the
    # basis, recompute the rest against the de-contaminated basis. Converges when no
    # remaining item has r < 0. Clean items' r is then measured against a clean basis.
    disc, inspect_gold, remaining = {}, {}, list(items)
    while True:
        round_r = {it: _corrected_r(cells, models, it, remaining) for it in remaining}
        negs = {it: r for it, r in round_r.items() if r is not None and r < 0}
        if not negs:
            disc.update(round_r)
            break
        worst = min(negs, key=lambda it: negs[it])
        disc[worst] = inspect_gold[worst] = negs[worst]
        remaining.remove(worst)
        if len(remaining) < 2:   # can't compute LOO below 2 items
            disc.update({it: None for it in remaining})
            break

    rows = []
    for it in items:
        present = [m for m in models if (m, it) in cells]
        difficulty = mean(cells[(m, it)] for m in present)
        r = disc.get(it)
        ranked = sorted(present, key=lambda m: ability[m], reverse=True)
        top_half = ranked[: max(1, len(ranked) // 2)]
        top_disp = pstdev([cells[(m, it)] for m in top_half]) if len(top_half) > 1 else 0.0
        top_model = ranked[0]
        item_sorted = sorted(present, key=lambda m: cells[(m, it)])
        top_in_bottom = top_model in item_sorted[: max(1, len(item_sorted) // 2)]

        flag, reason = "", ""
        if it in inspect_gold:
            flag = "INSPECT-GOLD"
            reason = (f"negative discrimination (r={r:+.2f}) after purifying the bank — "
                      "best models score worst => mis-keyed/contaminated gold?")
        elif difficulty > CEILING:
            flag, reason = "CEILING", f"difficulty {difficulty:.2f} — ~0 information, prune or replace"
        elif difficulty < FLOOR:
            flag, reason = "FLOOR", f"difficulty {difficulty:.2f} — ~0 information or all-fail (check task/gold)"
        elif r is not None and r < LOW_DISCRIM:
            flag, reason = "LOW-DISCRIM", f"discrimination r={r:+.2f} (<{LOW_DISCRIM}) — separates models weakly"
        elif top_disp > DISPERSION:
            flag, reason = "TOP-DISPERSION", f"high-ability models disagree (top stdev {top_disp:.2f}) — ambiguous gold or capability split"
        # note co-occurring secondary signals so they aren't masked by the if/elif (L2)
        if flag == "INSPECT-GOLD":
            extra = []
            if difficulty > CEILING:
                extra.append("also ceiling")
            elif difficulty < FLOOR:
                extra.append("also floor")
            if top_disp > DISPERSION:
                extra.append(f"top-dispersion {top_disp:.2f}")
            if extra:
                reason += " [" + "; ".join(extra) + "]"
        rows.append({
            "item": it, "difficulty": round(difficulty, 3),
            "discrimination": (round(r, 3) if r is not None else None),
            "top_dispersion": round(top_disp, 3), "top_in_bottom": top_in_bottom,
            "n_models": len(present), "flag": flag, "reason": reason,
        })

    # Rank: INSPECT-GOLD (a genuine sign flip) dominates, ordered by most-negative r; then
    # all items by dispersion + a top-in-bottom nudge. A clean high-dispersion item can no
    # longer outrank a weakly-mis-keyed one (fixes M1).
    def sort_key(x):
        is_ig = x["flag"] == "INSPECT-GOLD"
        neg = -(x["discrimination"]) if (is_ig and x["discrimination"] is not None) else 0.0
        return (1 if is_ig else 0, neg, x["top_dispersion"] + (0.5 if x["top_in_bottom"] else 0.0))
    rows.sort(key=sort_key, reverse=True)
    return {
        "n_models": len(models), "n_items": len(items),
        "powered": len(models) >= MIN_MODELS_POWERED and len(items) >= MIN_ITEMS_POWERED,
        "models": models, "items": items,
        "ability": {m: round(a, 3) for m, a in sorted(ability.items(), key=lambda x: -x[1])},
        "matrix": {f"{m}|{it}": round(cells[(m, it)], 3) for (m, it) in cells},
        "item_stats": rows,
        "flagged": [r["item"] for r in rows if r["flag"]],
        "inspect_gold": [it for it in inspect_gold],
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
