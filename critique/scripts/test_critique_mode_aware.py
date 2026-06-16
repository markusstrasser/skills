"""Regression tests for the provenance-pure + mode-aware critique engine.

Covers three coupled de-biasing fixes (2026-06-16):
  Fix 2  review_gate: dead-ref blocker is diff-coherence — block in `close` mode,
         WARN in `model`/`auto` (design docs legitimately name cross-repo/basename
         refs). Recurred 2026-06-15/16 as a false-block on design-doc critique.
  Fix 3  context_preamble: the GOALS charter ("review against these, not your
         priors") is OFF by default — blind-adversarial critique — and opt-in via
         --charter-anchor for compliance review. DEVELOPMENT_CONTEXT stays always.
  Fix A  model-review: a silently auto-loaded dispatch.json is trusted only if it
         was computed for THIS packet (content-hash / packet-path binding), so a
         stale manifest can't poison the run.

Run: PYTHONPATH=<skills-root> python3 critique/scripts/test_critique_mode_aware.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS_ROOT = HERE.parent.parent  # skills/
if str(SKILLS_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILLS_ROOT))


def _load(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, HERE / filename)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class CharterAnchorTest(unittest.TestCase):
    """Fix 3 — GOALS charter OFF by default (blind), opt-in for compliance."""

    def setUp(self) -> None:
        from shared.context_preamble import build_review_preamble_blocks

        self.build = build_review_preamble_blocks
        self._tmp = tempfile.TemporaryDirectory()
        self.proj = Path(self._tmp.name)
        (self.proj / "docs").mkdir()
        (self.proj / "docs" / "GOALS.md").write_text("# GOALS\nMaximize autonomy.\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_charter_off_by_default(self) -> None:
        blocks, anchored = self.build(self.proj)
        titles = [b.title for b in blocks]
        self.assertFalse(
            any("GOALS" in t for t in titles),
            "default must be blind-adversarial: no GOALS charter injected",
        )
        self.assertTrue(
            any("DEVELOPMENT CONTEXT" in t for t in titles),
            "DEVELOPMENT_CONTEXT (unbiasing) must always be present",
        )
        self.assertFalse(anchored)

    def test_charter_on_injects_goals(self) -> None:
        blocks, anchored = self.build(self.proj, charter_anchor=True)
        self.assertTrue(
            any("GOALS" in b.title for b in blocks),
            "compliance review must inject the GOALS charter",
        )
        self.assertTrue(anchored)

    def test_anti_prior_language_removed(self) -> None:
        blocks, _ = self.build(self.proj, charter_anchor=True)
        joined = " ".join(b.title for b in blocks)
        self.assertNotIn(
            "not your priors", joined,
            "the anti-prior clause must be gone even in compliance mode",
        )


class DeadRefModeGateTest(unittest.TestCase):
    """Fix 2 — dead refs block in close mode, warn (not block) in model mode."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        git(self.repo, "init")
        self.packet = self.repo / "packet.md"
        self.packet.write_text(
            "# Design\nThis flow lives in scripts/does_not_exist_xyz.py and "
            "references ~/Projects/other-repo/thing.py for the cross-repo bridge.\n"
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _triage(self, mode: str) -> dict:
        out = self.repo / f"dispatch-{mode}.json"
        env = {**os.environ, "PYTHONPATH": str(SKILLS_ROOT)}
        subprocess.run(
            [sys.executable, str(HERE / "review_gate.py"), "triage",
             "--repo", str(self.repo), "--packet", str(self.packet),
             "--mode", mode, "--dispatch-out", str(out)],
            check=False, capture_output=True, env=env,
        )
        return json.loads(out.read_text())

    def test_close_mode_blocks(self) -> None:
        d = self._triage("close")
        self.assertTrue(
            any("dead refs" in b for b in d["blockers"]),
            "close mode must BLOCK on dead refs (diff incoherence)",
        )

    def test_model_mode_warns_not_blocks(self) -> None:
        d = self._triage("model")
        self.assertFalse(
            any("dead refs" in b for b in d["blockers"]),
            "model mode (design doc) must NOT block on dead refs",
        )
        self.assertTrue(
            any("dead refs" in w for w in d["warnings"]),
            "model mode should surface dead refs as an informational warning",
        )


class ManifestProvenanceTest(unittest.TestCase):
    """Fix A — auto-loaded dispatch manifest trusted only if it matches the packet."""

    def setUp(self) -> None:
        self.mr = _load("model_review", "model-review.py")
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)
        self.packet = self.d / "p-context.md"
        self.packet.write_text("packet body")
        # the packet's sidecar manifest records its content hash
        (self.d / "p-context.manifest.json").write_text(
            json.dumps({"payload_hash": "HASH_CURRENT"})
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _manifest(self, body: dict) -> Path:
        m = self.d / "dispatch.json"
        m.write_text(json.dumps(body))
        return m

    def test_stale_hash_rejected(self) -> None:
        m = self._manifest({"review_hash": "HASH_STALE", "packet_path": str(self.packet)})
        self.assertFalse(
            self.mr._manifest_matches_packet(m, self.packet),
            "a manifest whose review_hash != current packet must NOT auto-load",
        )

    def test_matching_hash_trusted(self) -> None:
        m = self._manifest({"review_hash": "HASH_CURRENT", "packet_path": str(self.packet)})
        self.assertTrue(
            self.mr._manifest_matches_packet(m, self.packet),
            "a manifest computed for this packet must auto-load",
        )

    def test_path_fallback_when_no_hash(self) -> None:
        m = self._manifest({"packet_path": str(self.packet)})
        self.assertTrue(self.mr._manifest_matches_packet(m, self.packet))
        other = self._manifest({"packet_path": str(self.d / "different.md")})
        self.assertFalse(self.mr._manifest_matches_packet(other, self.packet))

    def test_no_binding_info_rejected(self) -> None:
        m = self._manifest({"preset": "standard"})
        self.assertFalse(self.mr._manifest_matches_packet(m, self.packet))


if __name__ == "__main__":
    unittest.main(verbosity=2)
