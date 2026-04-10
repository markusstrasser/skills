from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from shared.context_packet import BudgetPolicy, ContextPacket, PacketSection, TextBlock
from shared.context_renderers import write_packet_artifact
from shared.file_specs import FileSpec, parse_file_spec, read_file_excerpt
from shared.git_context import parse_status_porcelain, truncate_diff_text


class ContextPacketTest(unittest.TestCase):
    def test_write_packet_artifact_emits_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            packet = ContextPacket(
                title="Packet",
                sections=[PacketSection("Section", [TextBlock("Block", "hello world")])],
                budget_policy=BudgetPolicy(metric="tokens", limit=100),
            )
            output_path = root / "packet.md"
            manifest_path = root / "packet.manifest.json"
            artifact = write_packet_artifact(
                packet,
                renderer="markdown",
                output_path=output_path,
                manifest_path=manifest_path,
                builder_name="test",
                builder_version="v1",
            )
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(artifact.content_hash, manifest["rendered_content_hash"])
            self.assertEqual(artifact.payload_hash, manifest["payload_hash"])
            self.assertEqual(manifest["budget_metric"], "tokens")
            self.assertEqual(manifest["normalization_version"], "v1")

    def test_parse_file_spec_handles_ranges(self) -> None:
        spec = parse_file_spec("foo.py:10-20")
        self.assertEqual(spec.path, Path("foo.py"))
        self.assertEqual(spec.start_line, 10)
        self.assertEqual(spec.end_line, 20)
        self.assertEqual(spec.range_spec, "10-20")

    def test_parse_status_porcelain_handles_rename_and_spaces(self) -> None:
        raw = b"R  old name.py\x00new name.py\x00?? extra file.py\x00"
        entries = parse_status_porcelain(raw)
        self.assertEqual(entries[0].old_path, "old name.py")
        self.assertEqual(entries[0].path, "new name.py")
        self.assertEqual(entries[1].path, "extra file.py")

    def test_read_file_excerpt_honors_max_chars(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "long.txt"
            path.write_text("A" * 200 + "\n" + "B" * 200)
            text, truncated, omission = read_file_excerpt(FileSpec(path=path), max_chars=80)
            self.assertTrue(truncated)
            self.assertIsNone(omission)
            self.assertLessEqual(len(text), 80)

    def test_truncate_diff_text_honors_max_chars(self) -> None:
        diff = "\n".join(
            [
                "diff --git a/a.py b/a.py",
                "--- a/a.py",
                "+++ b/a.py",
                "@@ -1 +1 @@",
                "-" + ("x" * 120),
                "+" + ("y" * 120),
            ]
        )
        text, truncated = truncate_diff_text(diff, 90)
        self.assertTrue(truncated)
        self.assertLessEqual(len(text), 90)


if __name__ == "__main__":
    unittest.main()
