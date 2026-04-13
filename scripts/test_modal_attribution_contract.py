from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODAL_SKILL = ROOT / "modal" / "SKILL.md"
MODAL_ATTRIBUTION = ROOT / "modal" / "references" / "attribution.md"
MODAL_RESOURCES = ROOT / "modal" / "references" / "resources.md"


class ModalAttributionContractTest(unittest.TestCase):
    def test_modal_docs_explain_question_source_status_spend(self) -> None:
        skill_text = MODAL_SKILL.read_text()
        attribution_text = MODAL_ATTRIBUTION.read_text()
        resources_text = MODAL_RESOURCES.read_text()

        self.assertIn("operational question", skill_text)
        self.assertIn("truth surface", skill_text)
        self.assertIn("billing question", skill_text)
        self.assertIn("synthetic status", skill_text)
        self.assertIn("Question -> Source -> Status -> Spend", attribution_text)
        self.assertIn("status and spend", resources_text)
        self.assertIn("question_id", attribution_text)
        self.assertIn("run_id", attribution_text)
        self.assertIn("stage", attribution_text)


if __name__ == "__main__":
    unittest.main()
