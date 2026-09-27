"""operator-deck parses both operator lists in place and rotates the whole deck."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

DECK = Path(__file__).resolve().parents[1] / "bin/operator-deck"
ROOT = DECK.parents[1]


def run(*args: str, home: Path) -> str:
    env = {**os.environ, "OPERATOR_DECK_HOME": str(home)}
    return subprocess.run([sys.executable, str(DECK), *args], capture_output=True, text=True,
                          env=env, check=True).stdout


def bullets(path: Path, stop: tuple[str, ...]) -> int:
    n = 0
    for line in path.read_text().splitlines():
        if line.startswith(stop):
            break
        n += line.startswith("- **")
    return n


def test_selftest_passes(tmp_path: Path) -> None:
    assert run("--selftest", home=tmp_path).startswith("PASS")


def test_every_listed_step_is_in_the_deck(tmp_path: Path) -> None:
    # The deck is parsed from the two reference files; a bullet the parser skips would
    # silently drop out of every rotation.
    moves = bullets(ROOT / "research/references/follow-up-moves.md", ("## Domain packs", "## Habits"))
    frames = bullets(ROOT / "references/operator-frames.md", ("## Question forms",))
    listed = [ln for ln in run("list", home=tmp_path).splitlines() if ln.startswith("  ")]
    assert len(listed) == moves + frames


def test_draws_rotate_and_log(tmp_path: Path) -> None:
    first = run("next", "--project", "p", "--n", "2", home=tmp_path)
    ids = [ln.split("[", 1)[1].split("]", 1)[0] for ln in first.splitlines() if ln[:1].isdigit()]
    second = run("next", "--project", "p", "--n", "2", home=tmp_path)
    assert not any(f"[{i}]" in second for i in ids)
    run("log", ids[0], "--outcome", "applied", "--note", "done", "--project", "p", home=tmp_path)
    assert "1 applied" in run("status", "--project", "p", home=tmp_path)
