#!/usr/bin/env python3
"""Regression tests for verify_citations.py — run: uv run --no-project python3 test_verify_citations.py

Network-dependent (resolvers are live APIs). A resolver that comes back
`unreachable` SKIPS that assertion rather than failing — we only fail on a
definitive MISCLASSIFICATION, never on a transient network problem.
"""
from __future__ import annotations

import sys

import verify_citations as vc

# (doi, expected_status, why) — the classes the blocking gate must get right.
DOI_CASES = [
    ("10.5281/zenodo.20738220", "resolved",
     "DataCite/Zenodo DOI Crossref does not index — must NOT be 'hallucinated' "
     "(June-Kim determinacy-audit false-positive, 2026-07-10)"),
    ("10.1007/s10515-026-00638-5", "resolved",
     "ordinary Crossref journal DOI — rich-metadata path stays intact"),
    ("10.9999/nonexistent.hallucinated.99999", "hallucinated",
     "unregistered DOI — the blocking gate must still fire"),
]


def main() -> int:
    failures, skipped = [], []
    for doi, expected, why in DOI_CASES:
        c = vc.resolve_doi(doi)
        if c.status == "unreachable":
            skipped.append(f"  ~ SKIP  {doi} (resolver unreachable: {c.note})")
            continue
        if c.status != expected:
            failures.append(f"  ✗ FAIL  {doi}: got {c.status!r}, want {expected!r} — {why}")
        else:
            print(f"  ✓ {c.status:12} {doi}")
    for line in skipped:
        print(line)
    if failures:
        print("\n".join(failures))
        print(f"\n{len(failures)} misclassification(s) — blocking-gate regression.")
        return 1
    print(f"\nPASS ({len(DOI_CASES) - len(skipped)} checked, {len(skipped)} skipped).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
