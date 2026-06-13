#!/usr/bin/env python3
"""Drift guard for the provenance-tag taxonomy SSOT (references/provenance-tags.md).

The bug this prevents: 5 enforcers each carried a divergent INLINE copy of the tag regex, so
two gates disagreed on what counts as "sourced". Now every presence-gate LOADS provenance_tags.re;
this test fails if (a) the canonical regex misbehaves, or (b) any enforcer stops referencing it
(i.e. someone re-inlines and re-opens the drift)."""
import re
from pathlib import Path

# precommit-trigger: provenance_tags.re provenance-tags.md pretool-source-remind.sh postwrite-source-check-semantic.sh subagent-source-check-stop.sh subagent-epistemic-gate.sh test_provenance_tags.py
# ^ validate-changed-hooks.sh runs this test when any of these is staged (so re-inlining the
#   taxonomy can't land). Opt-in: a test with no trigger line is never run by the pre-commit gate.

HOOKS = Path(__file__).resolve().parent
CANON = (HOOKS / "provenance_tags.re").read_text(encoding="utf-8").strip()

# The presence-gate enforcers (NOT source-check-validator.py — it parses [SOURCE:] payloads,
# a different concern — nor postwrite's line-33 strong-citation density subset).
ENFORCERS = [
    HOOKS / "pretool-source-remind.sh",
    HOOKS / "postwrite-source-check-semantic.sh",
    HOOKS / "subagent-source-check-stop.sh",
    HOOKS / "subagent-epistemic-gate.sh",
    Path.home() / "Projects" / "agent-infra" / "scripts" / "epistemic-lint.py",
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
    # 2. every presence-gate enforcer LOADS the SSOT (so it can't silently drift an inline copy)
    for f in ENFORCERS:
        assert f.exists(), f"enforcer missing: {f}"
        assert "provenance_tags.re" in f.read_text(encoding="utf-8"), \
            f"{f.name} must LOAD provenance_tags.re, not inline the tag list (drift risk)"
    print("  ✓ canonical matches core+engine+genomics+graded tags; rejects [A7]/[G1]/non-tags")
    print(f"  ✓ all {len(ENFORCERS)} presence-gate enforcers load the SSOT (no inline copies left)")
    print("\n  provenance-taxonomy drift guard passed.")


def test_provenance_taxonomy_single_homed():  # pytest-discoverable entry (matches skills test_*.py convention)
    _selftest()


if __name__ == "__main__":
    print("[provenance_tags drift guard]")
    _selftest()
