#!/usr/bin/env python3
"""Drift guard for the provenance-tag taxonomy SSOT (references/provenance-tags.md).

The bug this prevents: 5 enforcers each carried a divergent INLINE copy of the tag regex, so
two gates disagreed on what counts as "sourced". Now every presence-gate LOADS provenance_tags.re;
this test fails if (a) the canonical regex misbehaves, or (b) any enforcer stops referencing it
(i.e. someone re-inlines and re-opens the drift)."""
import importlib.util
import re
from pathlib import Path

# precommit-trigger: provenance_tags.re provenance_tags.json gen_provenance_re.py provenance-tags.md pretool-source-remind.sh postwrite-source-check-semantic.sh subagent-source-check-stop.sh subagent-epistemic-gate.sh pretool-research-provenance-warn.sh stop-research-gate.sh postwrite-knowledge-index.py test_provenance_tags.py
# ^ validate-changed-hooks.sh runs this test when any of these is staged (so re-inlining the
#   taxonomy can't land). Opt-in: a test with no trigger line is never run by the pre-commit gate.

HOOKS = Path(__file__).resolve().parent
CANON = (HOOKS / "provenance_tags.re").read_text(encoding="utf-8").strip()

# The presence-gate enforcers — every gate that decides "is there a provenance tag here" LOADS the
# SSOT. Includes the two research-file gates (they prepend CANON, then OR in research-specific
# citation forms: URLs, markdown links, colon/comma-qualified tags). DELIBERATELY EXCLUDED:
#   - source-check-validator.py — parses [SOURCE:] payload STRUCTURE (URL present etc.), not presence.
#   - postwrite-source-check.sh — tag list is only in comments; gating delegates to the validator.
#   - postwrite-source-check-semantic.sh's density-count subset — a narrower "substantive-citation
#     density" heuristic that intentionally omits hedge tags; not the presence taxonomy.
ENFORCERS = [
    HOOKS / "pretool-source-remind.sh",
    HOOKS / "postwrite-source-check-semantic.sh",
    HOOKS / "subagent-source-check-stop.sh",
    HOOKS / "subagent-epistemic-gate.sh",
    HOOKS / "pretool-research-provenance-warn.sh",
    HOOKS / "stop-research-gate.sh",
    Path.home() / "Projects" / "agent-infra" / "scripts" / "epistemic-lint.py",
    # postwrite-knowledge-index.py used to carry its OWN inline SOURCE_TAG_RE (the one true
    # outlier — it knew ESTIMATED/PROVISIONAL but not SOURCE/DATABASE/…). It now LOADS
    # provenance_tags.json; this entry asserts it can't re-inline and re-open the drift.
    Path.home() / "Projects" / "agent-infra" / "scripts" / "postwrite-knowledge-index.py",
]


def _selftest() -> None:
    rx = re.compile(CANON)  # also proves the canonical compiles in Python re, not just grep -E
    # 1. recognizes every tier (core + engine + genomics + graded); rejects non-tags
    for ok in ("a [SOURCE: u] b", "[DATABASE: gnomAD]", "[INFERENCE]", "[UNVERIFIED]", "[Exa]",
               "[S2]", "[PubMed]", "[arXiv]", "[ClinGen]", "[CPIC]", "[gnomAD]", "[OMIM]",
               "[B2: industry whitepaper]", "[A1]"):
        assert rx.search(ok), f"canonical should match {ok!r}"
    for no in ("plain unsourced claim", "[A7]", "[G1]", "[NOTATAG]"):
        assert not rx.search(no), f"canonical should NOT match {no!r}"
    # 2. every presence-gate enforcer LOADS the SSOT (so it can't silently drift an inline copy).
    #    The SSOT now has two faces: provenance_tags.json (structured, authoritative) and the
    #    generated provenance_tags.re (grep projection). A consumer loading EITHER is single-homed.
    for f in ENFORCERS:
        assert f.exists(), f"enforcer missing: {f}"
        body = f.read_text(encoding="utf-8")
        assert ("provenance_tags.re" in body) or ("provenance_tags.json" in body), \
            f"{f.name} must LOAD the provenance SSOT (.re or .json), not inline the tag list (drift risk)"
    # 3. provenance_tags.re is a GENERATED projection of provenance_tags.json — byte-for-byte.
    #    This is the gate that keeps the JSON authoritative and forbids hand-editing the .re.
    import json
    spec = json.loads((HOOKS / "provenance_tags.json").read_text(encoding="utf-8"))
    gen = importlib.util.spec_from_file_location("gen_provenance_re", HOOKS / "gen_provenance_re.py")
    genmod = importlib.util.module_from_spec(gen); gen.loader.exec_module(genmod)  # type: ignore[union-attr]
    regenerated = genmod.gen_re(spec)
    assert regenerated == CANON + "\n" or regenerated == (HOOKS / "provenance_tags.re").read_text(encoding="utf-8"), \
        "provenance_tags.re is NOT the byte-for-byte generation of provenance_tags.json — re-run gen_provenance_re.py --write"
    # 4. in_re=false heads (vocabulary-but-not-hook) must NOT leak into the global-hook .re.
    for h in spec["heads"]:
        if not h.get("in_re", True):
            assert h["head"] not in CANON, \
                f"head {h['head']!r} is in_re=false but appears in provenance_tags.re — widening the hook needs owner sign-off"
    print("  ✓ canonical matches core+engine+genomics+graded tags; rejects [A7]/[G1]/non-tags")
    print(f"  ✓ all {len(ENFORCERS)} presence-gate enforcers load the SSOT (no inline copies left)")
    print("  ✓ provenance_tags.re is the byte-for-byte generation of provenance_tags.json")
    print("  ✓ in_re=false heads stay out of the global-hook .re (no silent widening)")
    print("\n  provenance-taxonomy drift guard passed.")


def test_provenance_taxonomy_single_homed():  # pytest-discoverable entry (matches skills test_*.py convention)
    _selftest()


if __name__ == "__main__":
    print("[provenance_tags drift guard]")
    _selftest()
