from __future__ import annotations

import re
from pathlib import Path

from shared.context_packet import PreambleBlock


DEVELOPMENT_CONTEXT = """# DEVELOPMENT CONTEXT
All code, plans, and features in this project are developed by AI agents, not human developers. Dev creation time is effectively zero. Therefore:
- NEVER recommend trading stability, composability, or robustness for dev time savings
- NEVER recommend simpler or hacky approaches because they are faster to implement
- Cost-benefit analysis should filter on maintenance burden, supervision cost, complexity budget, and blast radius — not creation effort
- Implementation effort is not a meaningful cost dimension here; only ongoing drag matters
"""


def find_constitution(project_dir: Path) -> tuple[str, str | None]:
    constitution = ""
    goals_path = None

    rules_constitution = project_dir / ".claude" / "rules" / "constitution.md"
    if rules_constitution.exists():
        constitution = rules_constitution.read_text().strip()

    if not constitution:
        claude_md = project_dir / "CLAUDE.md"
        if claude_md.exists():
            text = claude_md.read_text()
            tag_match = re.search(r"<constitution>(.*?)</constitution>", text, re.DOTALL)
            if tag_match:
                constitution = tag_match.group(1).strip()
            elif "## Constitution" in text:
                start = text.index("## Constitution")
                rest = text[start:]
                end = re.search(r"\n## (?!Constitution)", rest)
                constitution = rest[: end.start()].strip() if end else rest.strip()

    for candidate in (project_dir / "GOALS.md", project_dir / "docs" / "GOALS.md"):
        if candidate.exists():
            goals_path = str(candidate)
            break
    return constitution, goals_path


def build_review_preamble_blocks(project_dir: Path) -> tuple[list, bool]:
    constitution, goals_path = find_constitution(project_dir)
    blocks = []
    if constitution:
        blocks.append(
            PreambleBlock(
                "PROJECT CONSTITUTION (verbatim — review against these, not your priors)",
                constitution,
            )
        )
    if goals_path:
        blocks.append(PreambleBlock("PROJECT GOALS", Path(goals_path).read_text()))
    blocks.append(PreambleBlock("DEVELOPMENT CONTEXT", DEVELOPMENT_CONTEXT))
    return blocks, bool(constitution)

