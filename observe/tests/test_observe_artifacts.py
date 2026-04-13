from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import observe_artifacts  # noqa: E402
import session_shape  # noqa: E402


class ObserveArtifactsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_env = dict(os.environ)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._old_env)

    def test_project_root_defaults_from_artifact_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_root = Path(tmp_dir) / "meta" / "artifacts" / "observe"
            os.environ.pop(observe_artifacts.OBSERVE_PROJECT_ROOT_ENV, None)
            os.environ[observe_artifacts.OBSERVE_ARTIFACT_ROOT_ENV] = str(artifact_root)

            self.assertEqual(observe_artifacts.project_root(), artifact_root.parents[1])
            self.assertEqual(observe_artifacts.artifact_root(), artifact_root)

    def test_project_root_prefers_explicit_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / "workspace"
            os.environ[observe_artifacts.OBSERVE_PROJECT_ROOT_ENV] = str(project_root)
            os.environ.pop(observe_artifacts.OBSERVE_ARTIFACT_ROOT_ENV, None)

            self.assertEqual(observe_artifacts.project_root(), project_root)
            self.assertEqual(observe_artifacts.artifact_root(), project_root / "artifacts" / "observe")

    def test_project_root_defaults_to_canonical_agent_infra_without_env(self) -> None:
        os.environ.pop(observe_artifacts.OBSERVE_PROJECT_ROOT_ENV, None)
        os.environ.pop(observe_artifacts.OBSERVE_ARTIFACT_ROOT_ENV, None)

        self.assertEqual(
            observe_artifacts.project_root(),
            Path.home() / "Projects" / "agent-infra",
        )

    def test_artifact_constants_cover_manifest_and_digest(self) -> None:
        self.assertEqual(observe_artifacts.MANIFEST_JSON, "manifest.json")
        self.assertEqual(observe_artifacts.DIGEST_MD, "digest.md")
        self.assertEqual(observe_artifacts.DISPATCH_META_JSON, "dispatch.meta.json")

    def test_session_shape_candidate_records_reference_signal_ids(self) -> None:
        shape = session_shape.SessionShape(
            uuid="abcdef12abcdef12abcdef12abcdef12",
            project="meta",
            start_ts="2026-04-10T12:00:00+00:00",
            first_message="help me debug a path issue",
            duration_min=12.5,
            cost_usd=1.23,
            features={"tool_intensity": 9.0},
            anomaly_score=3.5,
            anomaly_reasons=["tool_intensity=9.00 (high, z=2.1)"],
        )

        signal_record = session_shape.build_signal_record(shape, threshold=2.0)
        candidate_record = session_shape.build_candidate_record(shape, threshold=2.0)

        self.assertEqual(signal_record["schema"], "observe.signal.v1")
        self.assertEqual(candidate_record["schema"], "observe.candidate.v1")
        self.assertEqual(signal_record["signal_id"], candidate_record["source_signal_ids"][0])
        self.assertTrue(candidate_record["candidate_id"].startswith("candidate_"))
        self.assertTrue(candidate_record["checkable"])
        self.assertEqual(candidate_record["state"], "candidate")
        self.assertFalse(candidate_record["promoted"])
        self.assertEqual(candidate_record["session_id"], shape.uuid)
        self.assertEqual(candidate_record["project"], "meta")

        encoded = json.dumps(candidate_record)
        self.assertIn("session_shape_anomaly", encoded)

    def test_session_shape_wrapper_does_not_export_imported_modules(self) -> None:
        self.assertFalse(hasattr(session_shape, "json"))
        self.assertFalse(hasattr(session_shape, "sqlite3"))

    def test_active_observe_docs_use_agent_infra_root(self) -> None:
        observe_root = Path(__file__).resolve().parents[1]
        combined = "\n".join(
            [
                (observe_root / "SKILL.md").read_text(),
                (observe_root / "references" / "artifact-contract.md").read_text(),
                (observe_root / "references" / "transcript-extraction.md").read_text(),
                (observe_root / "references" / "findings-staging.md").read_text(),
            ]
        )

        self.assertNotIn("Projects/meta", combined)
        self.assertIn("Projects/agent-infra", combined)
        self.assertIn("manifest.json", combined)
        self.assertIn("digest.md", combined)


if __name__ == "__main__":
    unittest.main()
