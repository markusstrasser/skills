#!/usr/bin/env python3
"""Tests for item_analysis.py — lock the diekstra-class invariant (a mis-keyed item
where the best models score worst MUST surface as INSPECT-GOLD, ranked first) and
the scale-normalization fix (the throwaway probe's bug: 0-1 threshold on 0-3 data).

Self-contained (synthetic matrices) — no cross-repo fixture dependency. Run:
    uv run python3 test_item_analysis.py      (or: pytest)
"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import item_analysis as ia  # type: ignore[import-not-found]  # noqa: E402  (dynamic sys.path)


def _matrix(cells):
    """cells: {(model,item): (score, scale_max)} -> long-format dict for analyze()."""
    return {k: (v[0] / v[1]) for k, v in cells.items()}


def test_miskeyed_item_flagged_inspect_gold_and_ranked_first():
    # 4 models. Item 'bad' is mis-keyed: the two HIGH-ability models score 0, the two
    # LOW-ability models score 1 -> strong negative discrimination (the diekstra shape).
    cells = {}
    for m, base in [("strong_a", 1.0), ("strong_b", 0.9), ("weak_a", 0.2), ("weak_b", 0.1)]:
        cells[(m, "good1")] = (base, 1.0)
        cells[(m, "good2")] = (base, 1.0)
    cells[("strong_a", "bad")] = (0.0, 1.0)
    cells[("strong_b", "bad")] = (0.0, 1.0)
    cells[("weak_a", "bad")] = (1.0, 1.0)
    cells[("weak_b", "bad")] = (1.0, 1.0)
    res = ia.analyze(_matrix(cells))
    flagged = {r["item"]: r for r in res["item_stats"] if r["flag"]}
    assert "bad" in flagged, f"mis-keyed item not flagged: {res['item_stats']}"
    assert flagged["bad"]["flag"] == "INSPECT-GOLD", flagged["bad"]
    assert res["item_stats"][0]["item"] == "bad", "mis-keyed item must rank first to inspect"
    assert res["item_stats"][0]["discrimination"] < 0


def test_ceiling_and_floor_flagged():
    cells = {}
    for m in ("a", "b", "c"):
        cells[(m, "ceil")] = (1.0, 1.0)   # everyone perfect -> ceiling
        cells[(m, "floor")] = (0.0, 1.0)  # everyone zero -> floor
        cells[(m, "mid")] = (0.5, 1.0)
    res = ia.analyze(_matrix(cells))
    flags = {r["item"]: r["flag"] for r in res["item_stats"]}
    assert flags["ceil"] == "CEILING", flags
    assert flags["floor"] == "FLOOR", flags


def test_scale_normalization_no_false_ceiling():
    # 0-3 faithfulness scale, mid values (~1.5/3 = 0.5). With scale_max=3 these must
    # normalize to ~0.5 difficulty (NO ceiling). This is the probe's bug, locked out.
    cells = {}
    for m, v in [("a", 1.5), ("b", 1.6), ("c", 1.4)]:
        cells[(m, "i1")] = (v, 3.0)
        cells[(m, "i2")] = (v + 0.1, 3.0)
        cells[(m, "i3")] = (v - 0.1, 3.0)
    res = ia.analyze(_matrix(cells))
    for r in res["item_stats"]:
        assert r["flag"] != "CEILING", f"false ceiling on 0-3 scale: {r}"
        assert r["difficulty"] < 0.7, f"difficulty not normalized: {r}"


def test_underpowered_flag():
    cells = {(m, f"i{j}"): (0.5, 1.0) for m in ("a", "b", "c") for j in range(3)}
    res = ia.analyze(_matrix(cells))
    assert res["powered"] is False  # 3 models x 3 items < floor


def test_good_item_not_flagged():
    # positive discrimination, mid difficulty -> clean item, no flag.
    cells = {}
    for m, base in [("strong", 0.9), ("mid", 0.6), ("weak", 0.2)]:
        cells[(m, "g1")] = (base, 1.0)
        cells[(m, "g2")] = (base, 1.0)
        cells[(m, "probe")] = (base, 1.0)  # tracks ability -> positive discrimination
    res = ia.analyze(_matrix(cells))
    probe = next(r for r in res["item_stats"] if r["item"] == "probe")
    assert probe["flag"] == "", probe
    assert probe["discrimination"] > 0


def test_long_adapter_roundtrip_and_cli():
    # >=3 models required to compute item-total discrimination (can't correlate 2 points).
    rows = []
    for m, base in [("strong", 1.0), ("mid", 0.6), ("weak", 0.1)]:
        rows.append({"model": m, "item": "ok", "score": base, "scale_max": 1.0})
        rows.append({"model": m, "item": "ok2", "score": base, "scale_max": 1.0})
    # mis-keyed 'bad': best models score worst.
    rows.append({"model": "strong", "item": "bad", "score": 0.0, "scale_max": 1.0})
    rows.append({"model": "mid", "item": "bad", "score": 0.0, "scale_max": 1.0})
    rows.append({"model": "weak", "item": "bad", "score": 1.0, "scale_max": 1.0})
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
        path = f.name
    try:
        out = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "item_analysis.py"), path, "--json"],
            capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        res = json.loads(out.stdout)
        assert "bad" in res["flagged"]
    finally:
        os.unlink(path)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"  FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
