from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "review_gate.py"
SPEC = importlib.util.spec_from_file_location("review_gate", SCRIPT)
assert SPEC and SPEC.loader
rg = importlib.util.module_from_spec(SPEC)
sys.modules["review_gate"] = rg
SPEC.loader.exec_module(rg)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class ReviewGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "T")
        (self.repo / "real.py").write_text("def foo(): pass\n")
        git(self.repo, "add", "real.py")
        git(self.repo, "commit", "-m", "init")
        self.packet = self.repo / ".model-review" / "packet.md"
        self.packet.parent.mkdir(parents=True)
        self.packet.write_text("# Packet\nSee `real.py` for logic.\n")
        manifest = {
            "review_targets": {
                "diff_target": {"owner": "code-review"},
                "design_target": {"owner": "critique", "axes": "standard"},
            },
            "payload_hash": "abc",
        }
        self.packet.with_suffix(".manifest.json").write_text(json.dumps(manifest))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_triage_pass_closeout(self) -> None:
        out = self.repo / ".model-review" / "dispatch.json"
        class Args:
            repo = self.repo
            packet = self.packet
            manifest = None
            review_dir = None
            base = head = None
            mode = "close"
            dispatch_out = out
            json = False

        # close mode without verify file → blocker
        code = rg.cmd_triage(Args)
        self.assertEqual(code, 1)
        data = json.loads(out.read_text())
        self.assertEqual(data["artifact"], "closeout")
        self.assertTrue(data["layers"]["diff"]["run"])
        self.assertTrue(data["layers"]["design"]["run"])

    def test_triage_dispatch_policy_repo(self) -> None:
        out = self.repo / "dispatch.json"

        class Args:
            repo = self.repo
            packet = self.packet
            manifest = None
            review_dir = None
            base = head = None
            mode = "model"
            budget_seconds = None
            dispatch_out = out
            json = False

        rg.cmd_triage(Args)
        data = json.loads(out.read_text())
        policy = data["dispatch_policy"]
        self.assertEqual(policy["context_scope"], "repo")
        self.assertTrue(policy["premise_scout"])

    def test_triage_dispatch_policy_packet_no_refs(self) -> None:
        self.packet.write_text("# Clear req\nDo X.\n")
        out = self.repo / "dispatch.json"

        class Args:
            repo = self.repo
            packet = self.packet
            manifest = None
            review_dir = None
            base = head = None
            mode = "model"
            budget_seconds = 900  # must sit at/above the axis-profile floor (600s for standard)
            dispatch_out = out
            json = False

        rg.cmd_triage(Args)
        policy = json.loads(out.read_text())["dispatch_policy"]
        self.assertEqual(policy["context_scope"], "packet")
        self.assertFalse(policy["premise_scout"])
        self.assertEqual(policy["budget_seconds"], 900)

    def test_triage_budget_below_floor_is_config_error(self) -> None:
        # 480 < the 600s standard-axis profile timeout: the ad6ba340 incident shape.
        # Triage must refuse (exit 2) and must NOT emit dispatch.json.
        out = self.repo / ".model-review" / "dispatch.json"

        class Args:
            repo = self.repo
            packet = self.packet
            manifest = None
            review_dir = None
            base = head = None
            mode = "model"
            budget_seconds = 480
            dispatch_out = out
            json = False

        self.assertEqual(rg.cmd_triage(Args), 2)
        self.assertFalse(out.exists())

    def test_triage_budget_at_floor_passes(self) -> None:
        out = self.repo / ".model-review" / "dispatch.json"
        floor, _axis = rg.axis_budget_floor("standard")

        class Args:
            repo = self.repo
            packet = self.packet
            manifest = None
            review_dir = None
            base = head = None
            mode = "model"
            budget_seconds = floor
            dispatch_out = out
            json = False

        self.assertEqual(rg.cmd_triage(Args), 0)
        policy = json.loads(out.read_text())["dispatch_policy"]
        self.assertEqual(policy["budget_seconds"], floor)

    def test_triage_manifest_budget_below_floor_is_config_error(self) -> None:
        # design_target.budget_seconds from the packet manifest hits the same floor.
        manifest = {
            "review_targets": {
                "design_target": {"owner": "critique", "axes": "standard", "budget_seconds": 300},
            },
            "payload_hash": "abc-floor",
        }
        self.packet.with_suffix(".manifest.json").write_text(json.dumps(manifest))
        out = self.repo / ".model-review" / "dispatch.json"

        class Args:
            repo = self.repo
            packet = self.packet
            manifest = None
            review_dir = None
            base = head = None
            mode = "model"
            budget_seconds = None
            dispatch_out = out
            json = False

        self.assertEqual(rg.cmd_triage(Args), 2)
        self.assertFalse(out.exists())

    def test_triage_dead_ref_blocks(self) -> None:
        # Dead refs BLOCK in close mode (diff-coherence). For a pure design doc
        # (model/auto, no diff layer) they now WARN instead — see
        # test_critique_mode_aware.py::DeadRefModeGateTest.
        self.packet.write_text("# Packet\nSee `missing.py`.\n")
        out = self.repo / "dispatch.json"

        class Args:
            repo = self.repo
            packet = self.packet
            manifest = None
            review_dir = None
            base = head = None
            mode = "close"
            dispatch_out = out
            json = False

        self.assertEqual(rg.cmd_triage(Args), 1)
        data = json.loads(out.read_text())
        self.assertEqual(data["schema_version"], rg.DISPATCH_SCHEMA_VERSION)
        self.assertTrue(any("dead ref" in b for b in data["blockers"]))

    def test_scan_dead_refs_ignores_diff_headers_and_resolves_nested_basenames(self) -> None:
        nested = self.repo / "scripts" / "orchestrator" / "controller_reconcile.py"
        nested.parent.mkdir(parents=True)
        nested.write_text("# source\n")
        packet = "\n".join(
            (
                "diff --git a/scripts/orchestrator/controller_reconcile.py "
                "b/scripts/orchestrator/controller_reconcile.py",
                "--- a/scripts/orchestrator/controller_reconcile.py",
                "+++ b/scripts/orchestrator/controller_reconcile.py",
                "The helper is in controller_reconcile.py.",
            )
        )

        self.assertEqual(rg._scan_dead_refs(packet, self.repo), [])

    def test_triage_recommends_cross2_preset(self) -> None:
        manifest = {
            "review_targets": {
                "diff_target": {"owner": "code-review"},
                "design_target": {"owner": "critique"},
            },
            "payload_hash": "abc2",
        }
        self.packet.with_suffix(".manifest.json").write_text(json.dumps(manifest))
        out = self.repo / "dispatch.json"

        class Args:
            repo = self.repo
            packet = self.packet
            manifest = None
            review_dir = None
            base = head = None
            mode = "model"
            dispatch_out = out
            json = True

        self.assertEqual(rg.cmd_triage(Args), 0)
        data = json.loads(out.read_text())
        self.assertEqual(data["preset"], "cross2")
        self.assertEqual(data["layers"]["design"]["axes"], "cross2")

    def test_triage_governance_escalates_cross4(self) -> None:
        manifest = {
            "review_targets": {
                "design_target": {"owner": "critique"},
            },
            "payload_hash": "abc3",
        }
        self.packet.with_suffix(".manifest.json").write_text(json.dumps(manifest))
        self.packet.write_text("# Packet\nSchema migration touches constitution.\n")
        out = self.repo / "dispatch.json"

        class Args:
            repo = self.repo
            packet = self.packet
            manifest = None
            review_dir = None
            base = head = None
            mode = "model"
            dispatch_out = out
            json = True

        self.assertEqual(rg.cmd_triage(Args), 0)
        data = json.loads(out.read_text())
        self.assertEqual(data["preset"], "cross4")
        self.assertIn("governance_paths", data["preset_reasons"])

    def test_contradictory_anchors_escalate_cross4(self) -> None:
        rd = self.repo / ".model-review" / "contrad-review"
        rd.mkdir(parents=True)
        findings = {
            "findings": [
                {
                    "id": 1,
                    "title": "outbox pattern allows direct corpus writes",
                    "file": "gateway.py",
                    "source_axis": "arch",
                    "description": "missing enforcement is a bug",
                },
                {
                    "id": 2,
                    "title": "outbox pattern is correctly enforced",
                    "file": "gateway.py",
                    "source_axis": "correctness",
                    "description": "works fine no issue",
                },
            ]
        }
        (rd / "findings.json").write_text(json.dumps(findings))
        manifest = {
            "review_targets": {"design_target": {"owner": "critique"}},
            "payload_hash": "c1",
        }
        self.packet.with_suffix(".manifest.json").write_text(json.dumps(manifest))
        out = self.repo / "dispatch.json"

        class Args:
            repo = self.repo
            packet = self.packet
            manifest = None
            review_dir = rd
            base = head = None
            mode = "model"
            dispatch_out = out
            json = True

        self.assertEqual(rg.cmd_triage(Args), 0)
        data = json.loads(out.read_text())
        self.assertEqual(data["preset"], "cross4")
        self.assertIn("contradictory_anchors", data["preset_reasons"])

    def test_non_overlap_does_not_escalate(self) -> None:
        rd = self.repo / ".model-review" / "overlap-review"
        rd.mkdir(parents=True)
        findings = {
            "findings": [
                {
                    "id": 1,
                    "title": "missing unit tests for drain path",
                    "file": "gateway.py",
                    "source_axis": "arch",
                },
                {
                    "id": 2,
                    "title": "retry_count not incremented on failure",
                    "file": "gateway.py",
                    "source_axis": "correctness",
                },
            ]
        }
        (rd / "findings.json").write_text(json.dumps(findings))
        pairs = rg.detect_contradictory_anchors(findings["findings"])
        self.assertEqual(pairs, [])

    def test_generic_entity_tokens_no_false_contradiction(self) -> None:
        findings = [
            {
                "id": 1,
                "title": "client config missing validation checks",
                "file": "app.py",
                "source_axis": "arch",
                "description": "broken validation path",
            },
            {
                "id": 2,
                "title": "client config works correctly today",
                "file": "app.py",
                "source_axis": "correctness",
                "description": "no issue found",
            },
        ]
        self.assertEqual(rg.detect_contradictory_anchors(findings), [])

    def test_rank_writes_escalation_recommendation(self) -> None:
        rd = self.repo / ".model-review" / "esc"
        rd.mkdir(parents=True)
        (rd / "coverage.json").write_text(
            json.dumps({"dispatch": {"requested_axes": ["arch", "correctness"]}})
        )
        findings = {
            "findings": [
                {
                    "id": 1,
                    "title": "outbox pattern allows direct corpus writes",
                    "file": "gateway.py",
                    "source_axis": "arch",
                    "severity": "high",
                    "description": "bug missing enforcement",
                },
                {
                    "id": 2,
                    "title": "outbox pattern is correctly enforced",
                    "file": "gateway.py",
                    "source_axis": "correctness",
                    "severity": "high",
                    "description": "works fine no issue",
                },
            ]
        }
        (rd / "findings.json").write_text(json.dumps(findings))

        class Args:
            review_dir = rd
            top = 8
            json = False

        self.assertEqual(rg.cmd_rank(Args), 0)
        esc = json.loads((rd / "escalation-recommendation.json").read_text())
        self.assertEqual(esc["escalation_recommended"], "cross4")
        self.assertEqual(esc["current_preset"], "cross2")
        self.assertFalse(esc["escalation_executed"])

    def test_contradictions_subcommand(self) -> None:
        rd = self.repo / ".model-review" / "csub"
        rd.mkdir(parents=True)
        findings = {
            "findings": [
                {
                    "id": 1,
                    "title": "schema migration is broken and invalid",
                    "file": "m.sql",
                    "source_axis": "arch",
                },
                {
                    "id": 2,
                    "title": "schema migration is correct and safe",
                    "file": "m.sql",
                    "source_axis": "correctness",
                },
            ]
        }
        (rd / "findings.json").write_text(json.dumps(findings))

        class Args:
            review_dir = rd
            json = True

        self.assertEqual(rg.cmd_contradictions(Args), 0)
        data = json.loads((rd / "anchor-contradictions.json").read_text())
        self.assertEqual(data["contradictory_pairs"], 1)

    def test_rank_top_n(self) -> None:
        rd = self.repo / ".model-review" / "r1"
        rd.mkdir(parents=True)
        findings = {
            "findings": [
                {"id": 1, "title": "low noise", "severity": "low", "confidence": 0.5},
                {
                    "id": 2,
                    "title": "cross high",
                    "severity": "high",
                    "confidence": 0.9,
                    "cross_model": True,
                    "file": "real.py",
                },
            ]
        }
        (rd / "findings.json").write_text(json.dumps(findings))

        class Args:
            review_dir = rd
            top = 8
            json = False

        self.assertEqual(rg.cmd_rank(Args), 0)
        top = json.loads((rd / "orchestrator-top.json").read_text())
        self.assertEqual(top["findings"][0]["title"], "cross high")


if __name__ == "__main__":
    unittest.main()
