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
    """Return path to the project's `docs/GOALS.md` (or root `GOALS.md`)."""
    for candidate in (project_dir / "docs" / "GOALS.md", project_dir / "GOALS.md"):
        if candidate.exists():
            return str(candidate)
    return None


def build_review_preamble_blocks(
    project_dir: Path, charter_anchor: bool = False
) -> tuple[list, bool]:
    """Assemble the review preamble.

    ``charter_anchor`` gates the project GOALS/governance block:
      - ``False`` (default) — **blind-adversarial** critique: the reviewer judges
        on its own priors, NOT against the project's stated conclusions. Correct
        default for design/diff critique (the blind-first-pass principle).
        Verbatim-charter injection measurably biases reviewers toward
        charter-compliance and against scoping-down (2026-06-15 biased-critique
        incident; the neutral re-run only de-biased once the charter was removed).
      - ``True`` — **compliance/governance** review: inject GOALS so the reviewer
        checks the work *against* the stated goals.

    ``DEVELOPMENT_CONTEXT`` is ALWAYS injected: it corrects a reviewer bias
    (assuming human dev costs → "over-engineered for the effort") without imposing
    the project's conclusions, so it is unbiasing in both modes.
    """
    goals_path = find_governance(project_dir)
    blocks = []
    if charter_anchor and goals_path:
        blocks.append(
            PreambleBlock(
                "PROJECT GOALS & GOVERNANCE (verbatim — compliance review against these)",
                Path(goals_path).read_text(),
            )
        )
    blocks.append(PreambleBlock("DEVELOPMENT CONTEXT", DEVELOPMENT_CONTEXT))
    return blocks, bool(charter_anchor and goals_path)
