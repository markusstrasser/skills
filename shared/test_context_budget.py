from __future__ import annotations

import unittest

from shared.context_budget import enforce_budget
from shared.context_packet import BudgetPolicy, ContextPacket, DiffBlock, PacketSection, TextBlock


class ContextBudgetTest(unittest.TestCase):
    def test_enforce_budget_truncates_before_dropping(self) -> None:
        packet = ContextPacket(
            title="Packet",
            sections=[
                PacketSection(
                    "Section",
                    [
                        TextBlock("keep", "A" * 300, priority=500, drop_if_needed=False),
                        TextBlock("shrink", "B" * 2400, priority=10, drop_if_needed=True, min_chars=300),
                    ],
                )
            ],
            budget_policy=BudgetPolicy(metric="tokens", limit=420),
        )

        outcome = enforce_budget(packet, renderer="markdown")

        self.assertTrue(outcome.truncated_blocks)
        self.assertEqual(outcome.truncated_blocks[0]["block_title"], "shrink")
        if outcome.dropped_blocks:
            self.assertEqual(outcome.dropped_blocks[0]["block_title"], "shrink")
        self.assertLessEqual(outcome.estimated_usage, 420)

    def test_enforce_budget_drops_low_priority_blocks_first(self) -> None:
        packet = ContextPacket(
            title="Packet",
            sections=[
                PacketSection(
                    "Section",
                    [
                        TextBlock("keep", "A" * 300, priority=500, drop_if_needed=False),
                        TextBlock("drop-first", "B" * 300, priority=10, drop_if_needed=True),
                        TextBlock("drop-second", "C" * 300, priority=20, drop_if_needed=True),
                    ],
                )
            ],
            budget_policy=BudgetPolicy(metric="tokens", limit=120),
        )

        outcome = enforce_budget(packet, renderer="markdown")

        surviving_titles = [block.title for section in outcome.packet.sections for block in section.blocks]
        self.assertEqual(surviving_titles, ["keep", "drop-second"])
        self.assertEqual([entry["block_title"] for entry in outcome.dropped_blocks], ["drop-first"])
        self.assertLessEqual(outcome.estimated_usage, 120)

    def test_enforce_budget_preserves_non_droppable_diff(self) -> None:
        packet = ContextPacket(
            title="Packet",
            sections=[
                PacketSection(
                    "Git",
                    [
                        DiffBlock("diff", "D" * 800, priority=300, drop_if_needed=False),
                        TextBlock("excerpt", "E" * 400, priority=10, drop_if_needed=True),
                    ],
                )
            ],
            budget_policy=BudgetPolicy(metric="tokens", limit=250),
        )

        outcome = enforce_budget(packet, renderer="markdown")

        surviving_titles = [block.title for section in outcome.packet.sections for block in section.blocks]
        self.assertIn("diff", surviving_titles)
        self.assertNotIn("excerpt", surviving_titles)


if __name__ == "__main__":
    unittest.main()
