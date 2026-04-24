#!/usr/bin/env python3
"""Synchronize skill symlinks: Codex and Gemini mirror Claude Code.

Policy:
- Claude Code is the source of truth. Skills visible to Claude — at user level
  (~/.claude/skills/) and per-project (<proj>/.claude/skills/) — are mirrored
  into the Codex and Gemini discovery paths.
- Codex reads ~/.agents/skills/ (user) and <proj>/.agents/skills/ (project).
- Gemini reads ~/.gemini/skills/ (user). Per-project Gemini scoping not yet wired.
- The old full-tree ~/.agents/skills -> ~/Projects/skills symlink is replaced
  with a selective directory matching ~/.claude/skills/, because Codex enforces
  the same skill-description context budget as Claude.

Each entry in .claude/skills/ (whether a symlink into ~/Projects/skills/ or a
real per-project skill dir) becomes a symlink in the mirror dir pointing at
the same target.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
PROJECTS = HOME / "Projects"

CLAUDE_USER_DIR = HOME / ".claude" / "skills"
AGENTS_USER_DIR = HOME / ".agents" / "skills"
GEMINI_USER_DIR = HOME / ".gemini" / "skills"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _dirs_identical(a: Path, b: Path) -> bool:
    """True if a and b have the same tree (ignoring .DS_Store and pycache)."""
    def _walk(root: Path) -> set[tuple[str, int, bytes]]:
        out: set[tuple[str, int, bytes]] = set()
        for p in root.rglob("*"):
            if p.name == ".DS_Store" or "__pycache__" in p.parts:
                continue
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                out.add((rel, p.stat().st_size, p.read_bytes()))
        return out
    try:
        return _walk(a) == _walk(b)
    except OSError:
        return False


def _link_target_for(entry: Path) -> Path:
    """Resolve the canonical target a mirror symlink should point at."""
    if entry.is_symlink():
        raw = Path(os.readlink(entry))
        return raw if raw.is_absolute() else (entry.parent / raw).resolve()
    return entry.resolve()


def _replace_symlink(link: Path, target: Path, *, dry_run: bool) -> str:
    if link.is_symlink():
        try:
            current = Path(os.readlink(link))
            if not current.is_absolute():
                current = (link.parent / current).resolve()
            if current == target:
                return "ok"
        except OSError:
            pass
        if not dry_run:
            link.unlink()
    elif link.exists():
        # Duplicate real dir: replace with a symlink only if content matches source.
        if not link.is_dir():
            return "skip-nonsymlink-file"
        if not _dirs_identical(link, target):
            return "conflict-diverged"
        if dry_run:
            return "would-replace-dir"
        import shutil
        shutil.rmtree(link)
        link.symlink_to(target)
        return "replaced-dir-with-link"
    if not dry_run:
        link.symlink_to(target)
    return "linked"


def _mirror(source: Path, target: Path, label: str, *, dry_run: bool) -> list[str]:
    """Mirror source/ into target/ as symlinks pointing at each source entry's target."""
    messages: list[str] = []
    if not source.is_dir():
        return messages
    _ensure_dir(target)

    expected: dict[str, Path] = {}
    for entry in sorted(source.iterdir()):
        if entry.name.startswith("."):
            continue
        if not (entry.is_dir() or entry.is_symlink()):
            continue
        expected[entry.name] = _link_target_for(entry)

    for name, dest in expected.items():
        status = _replace_symlink(target / name, dest, dry_run=dry_run)
        messages.append(f"{label}/{name}: {status}")

    for link in sorted(target.iterdir()):
        if link.name.startswith(".") or link.name in expected:
            continue
        if not link.is_symlink():
            # Leave unexpected real dirs in place and warn — may be hand-curated.
            messages.append(f"{label}/{link.name}: skip-nonsymlink-stale")
            continue
        try:
            resolved = link.resolve()
        except OSError:
            resolved = None
        # Only prune symlinks that point into the skills repo or into .claude/skills
        claude_skills_parent = source
        prunable = resolved is not None and (
            ROOT in resolved.parents
            or resolved == ROOT
            or claude_skills_parent in resolved.parents
        )
        if prunable:
            if not dry_run:
                link.unlink()
            messages.append(f"{label}/{link.name}: removed-stale-link")

    return messages


def _sync_agents_user_root(*, dry_run: bool) -> list[str]:
    """Replace legacy ~/.agents/skills full-tree symlink with a selective dir."""
    messages: list[str] = []
    if AGENTS_USER_DIR.is_symlink():
        if not dry_run:
            AGENTS_USER_DIR.unlink()
        messages.append("agents/skills: removed-legacy-symlink")
    return messages


def _iter_projects() -> list[Path]:
    if not PROJECTS.is_dir():
        return []
    return sorted(p for p in PROJECTS.iterdir() if p.is_dir() and not p.name.startswith("."))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    messages: list[str] = []

    # User level: mirror ~/.claude/skills/ into ~/.agents/skills/ and ~/.gemini/skills/.
    messages.extend(_sync_agents_user_root(dry_run=args.dry_run))
    messages.extend(_mirror(CLAUDE_USER_DIR, AGENTS_USER_DIR, "agents", dry_run=args.dry_run))
    messages.extend(_mirror(CLAUDE_USER_DIR, GEMINI_USER_DIR, "gemini", dry_run=args.dry_run))

    # Per project: mirror <proj>/.claude/skills/ into <proj>/.agents/skills/.
    for proj in _iter_projects():
        claude_dir = proj / ".claude" / "skills"
        if not claude_dir.is_dir():
            continue
        agents_dir = proj / ".agents" / "skills"
        label = f"{proj.name}/.agents"
        messages.extend(_mirror(claude_dir, agents_dir, label, dry_run=args.dry_run))

    print("\n".join(messages) if messages else "nothing to do")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
