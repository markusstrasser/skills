"""Regression tests for verify_citations.py — run: uv run --no-project python3 test_verify_citations.py

Includes deterministic advisory-response tests and live resolver checks.
A live resolver that comes back
`unreachable` SKIPS that assertion rather than failing — we only fail on a
definitive MISCLASSIFICATION, never on a transient network problem.
"""
from __future__ import annotations

import json
import sys
import unittest
from unittest.mock import patch

import verify_citations as vc

# (doi, expected_status, why) — the classes the blocking gate must get right.
DOI_CASES = [
    ("10.5281/zenodo.20738220", "resolved",
     ("DataCite/Zenodo DOI Crossref does not index — must NOT be 'hallucinated' "
      "(June-Kim determinacy-audit false-positive, 2026-07-10)")),
    ("10.1007/s10515-026-00638-5", "resolved",
     "ordinary Crossref journal DOI — rich-metadata path stays intact"),
    ("10.9999/nonexistent.hallucinated.99999", "hallucinated",
     "unregistered DOI — the blocking gate must still fire"),
]


class AdvisoryResponseTests(unittest.TestCase):
    """An advisory service failure must preserve principal DOI verification."""

    def test_invalid_crossref_responses_are_unreachable(self):
        for response in (b"<html>unavailable</html>", b"\xff", b"[]", b"{}",
                         b'{"message":null}', b'{"message":{"published":[1]}}'):
            with self.subTest(response=response), patch.object(vc, "_get", return_value=response):
                citation = vc.resolve(vc.Cite("doi", "10.1234/test"))
                self.assertEqual(citation.status, "unreachable")
                self.assertIn("Crossref response invalid", citation.note)
                self.assertFalse(vc.build_report([citation]).blocking)

    def test_invalid_dblp_responses_preserve_resolved_citation(self):
        crossref = json.dumps({"message": {
            "title": ["A real research preprint"], "type": "posted-content",
        }}).encode()
        invalid_responses = [
            b"<html>upstream unavailable</html>", b"", b"\xff", b"[]", b"{}",
            b'{"result":{"hits":{"hit":"unexpected"}}}',
            b'{"result":{"hits":{"hit":null}}}',
            b'{"result":{"hits":{"hit":{}}}}',
            b'{"result":{"hits":{"hit":[null]}}}',
        ]
        for response in invalid_responses:
            with self.subTest(response=response), patch.object(
                vc, "_get", side_effect=[crossref, response],
            ):
                citation = vc.resolve(vc.Cite("doi", "10.1234/test"))
                self.assertEqual(citation.status, "resolved")
                self.assertEqual(citation.upgrade, "")
                self.assertIn("[DEGRADED]", citation.note)
                self.assertIn("DBLP", citation.note)
                report = vc.build_report([citation])
                self.assertFalse(report.blocking)
                self.assertEqual(report.resolved, 1)
                self.assertIn("[DEGRADED]", vc.brief(report))
                self.assertIn("[DEGRADED]", report.cites[0]["note"])

    def test_dblp_transport_failure_is_visible(self):
        citation = vc.Cite("doi", "10.1234/test", status="resolved",
                           title="A real research preprint", arxiv_only=True,
                           note="existing provenance")
        with patch.object(vc, "resolve_doi", return_value=citation), patch.object(
            vc, "_get", side_effect=vc.Unreachable("HTTP 503"),
        ):
            result = vc.resolve(citation)
        self.assertEqual(result.status, "resolved")
        self.assertIn("existing provenance", result.note)
        self.assertIn("[DEGRADED]", result.note)
        self.assertIn("HTTP 503", result.note)

    def test_valid_dblp_responses_keep_matching_guard(self):
        title = "A real research preprint"
        cases = [
            ({"@total": "0"}, ""),
            ({"hit": [{"info": {"type": "Journal Articles", "venue": "Journal",
                                "title": title, "year": "2026"}}]}, "Journal (2026)"),
            ({"hit": [{"info": {"type": "Journal Articles", "venue": "Journal",
                                "title": "An unrelated publication"}}]}, ""),
        ]
        for hits, expected in cases:
            with self.subTest(hits=hits), patch.object(
                vc, "_get", return_value=json.dumps({"result": {"hits": hits}}).encode(),
            ):
                self.assertEqual(vc.dblp_upgrade(title), expected)


def main() -> int:
    result = unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(AdvisoryResponseTests)
    )
    if not result.wasSuccessful():
        return 1
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
