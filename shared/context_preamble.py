from __future__ import annotations

from pathlib import Path

from shared.context_packet import PreambleBlock


DEVELOPMENT_CONTEXT = """# DEVELOPMENT CONTEXT
All code, plans, and features in this project are developed by AI agents, not human developers. Dev creation time is effectively zero. Therefore:
- NEVER recommend trading stability, composability, or robustness for dev time savings
- NEVER recommend simpler or hacky approaches because they are faster to implement
- Cost-benefit analysis should filter on maintenance burden, supervision cost, complexity budget, and blast radius — not creation effort
- Implementation effort is not a meaningful cost dimension here; only ongoing drag matters
"""


def find_governance(project_dir: Path) -> str | None:
    """Locate the project's merged goals + governance doc.

    The single-doc convention (2026-04-24) is `docs/GOALS.md`. Falls back
    to root `GOALS.md` for projects without a docs/ directory. Legacy
    constitution locations (`.claude/rules/constitution.md`, inline
    `## Constitution` section in CLAUDE.md, `<constitution>` XML tag) are
    no longer searched — projects with split governance should be merged
    via the `/goals` skill.
    """
    for candidate in (project_dir / "docs" / "GOALS.md", project_dir / "GOALS.md"):
        if candidate.exists():
            return str(candidate)
    return None


def build_review_preamble_blocks(project_dir: Path) -> tuple[list, bool]:
    goals_path = find_governance(project_dir)
    blocks = []
    if goals_path:
        blocks.append(
            PreambleBlock(
                "PROJECT GOALS & GOVERNANCE (verbatim — review against these, not your priors)",
                Path(goals_path).read_text(),
            )
        )
    blocks.append(PreambleBlock("DEVELOPMENT CONTEXT", DEVELOPMENT_CONTEXT))
    return blocks, bool(goals_path)
