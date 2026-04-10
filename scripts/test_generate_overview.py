from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import json

import scripts.generate_overview as generate_overview


class GenerateOverviewTest(unittest.TestCase):
    def test_build_overview_packet_creates_payload_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude").mkdir()
            (root / ".claude" / "overview.conf").write_text(
                "\n".join(
                    [
                        "OVERVIEW_TYPES=source",
                        "OVERVIEW_PROMPT_DIR=.claude/prompts",
                        "OVERVIEW_OUTPUT_DIR=.claude/overviews",
                        "OVERVIEW_SOURCE_DIRS=src/",
                    ]
                )
            )
            (root / ".claude" / "prompts").mkdir(parents=True)
            (root / ".claude" / "prompts" / "source.md").write_text("Summarize the source.")
            (root / "src").mkdir()
            config = generate_overview.read_overview_config(root)

            def fake_repomix(**kwargs):
                kwargs["output_path"].write_text("CODEBASE")

            with patch.object(generate_overview, "capture_repomix_to_file", fake_repomix):
                payload = generate_overview.build_overview_packet(
                    root,
                    config,
                    "source",
                    profile_name="fast_extract",
                    output_dir=root / ".claude" / "overviews",
                )

            self.assertTrue(payload.payload_path.exists())
            self.assertTrue(payload.manifest_path.exists())
            text = payload.payload_path.read_text()
            self.assertIn("<instructions>", text)
            self.assertIn("<codebase>", text)
            self.assertIn("Write the requested codebase overview in markdown.", text)
            manifest = json.loads(payload.manifest_path.read_text())
            self.assertIn(str(root / ".claude" / "prompts" / "source.md"), manifest["source_paths"])
            self.assertIn(str(root / ".claude" / "overviews" / ".overview-source-codebase.txt"), manifest["source_paths"])

    def test_live_and_batch_payloads_share_payload_hash(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude").mkdir()
            (root / ".claude" / "overview.conf").write_text(
                "\n".join(
                    [
                        "OVERVIEW_TYPES=source",
                        "OVERVIEW_PROMPT_DIR=.claude/prompts",
                        "OVERVIEW_OUTPUT_DIR=.claude/overviews",
                        "OVERVIEW_SOURCE_DIRS=src/",
                    ]
                )
            )
            (root / ".claude" / "prompts").mkdir(parents=True)
            (root / ".claude" / "prompts" / "source.md").write_text("Summarize the source.")
            (root / "src").mkdir()
            config = generate_overview.read_overview_config(root)

            def fake_repomix(**kwargs):
                kwargs["output_path"].write_text("CODEBASE")

            with patch.object(generate_overview, "capture_repomix_to_file", fake_repomix):
                live_payload = generate_overview.build_overview_packet(
                    root,
                    config,
                    "source",
                    profile_name="fast_extract",
                    output_dir=root / ".claude" / "overviews",
                )
                batch_payload = generate_overview.build_overview_packet(
                    root,
                    config,
                    "source",
                    profile_name="fast_extract",
                    output_dir=root / ".batch" / "source",
                )

            live_manifest = json.loads(live_payload.manifest_path.read_text())
            batch_manifest = json.loads(batch_payload.manifest_path.read_text())
            self.assertEqual(live_manifest["payload_hash"], batch_manifest["payload_hash"])


if __name__ == "__main__":
    unittest.main()
