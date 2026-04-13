from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DOC = ROOT / "SKILL.md"
SKILL_MANIFEST = ROOT / "skill.json"
DISPATCH_REF = ROOT / "references" / "llmx-dispatch.md"
TEMPLATES_REF = ROOT / "references" / "synthesis-templates.md"
DOMAIN_POOLS_REF = ROOT / "references" / "domain-pools.md"


class BrainstormContractTest(unittest.TestCase):
    def test_docs_match_structured_artifact_contract(self) -> None:
        skill_text = SKILL_DOC.read_text()
        dispatch_text = DISPATCH_REF.read_text()
        templates_text = TEMPLATES_REF.read_text()
        manifest = json.loads(SKILL_MANIFEST.read_text())

        self.assertEqual(
            manifest["modes"]["default"]["artifacts"],
            ["synthesis.md", "matrix.json", "matrix.md", "coverage.json"],
        )
        self.assertIn("matrix.json", skill_text)
        self.assertIn("coverage.json", skill_text)
        self.assertIn("matrix.json", dispatch_text)
        self.assertIn("coverage.json", dispatch_text)
        self.assertIn("matrix.json", templates_text)
        self.assertIn("coverage.json", templates_text)

    def test_docs_do_not_teach_raw_llmx_chat_commands(self) -> None:
        combined = "\n".join(
            [
                SKILL_DOC.read_text(),
                DISPATCH_REF.read_text(),
                TEMPLATES_REF.read_text(),
            ]
        )

        self.assertNotIn("llmx chat", combined)
        self.assertNotIn("llmx chat -m", combined)

    def test_docs_preserve_divergent_boundary_and_domain_row_tracking(self) -> None:
        skill_text = SKILL_DOC.read_text()
        dispatch_text = DISPATCH_REF.read_text()
        domain_pools_text = DOMAIN_POOLS_REF.read_text()

        self.assertIn("/model-review", skill_text)
        self.assertIn("caller_evidence", dispatch_text)
        self.assertIn("speculative", dispatch_text)
        self.assertIn("domain_row", dispatch_text)
        self.assertIn("domain_row", domain_pools_text)


if __name__ == "__main__":
    unittest.main()
