"""Vendored skills stay byte-equal to their upstream pin (see sync_upstream_skills.py)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PINS = sorted(ROOT.glob("*/UPSTREAM.json"))


@pytest.mark.parametrize("pin_path", PINS, ids=lambda p: p.parent.name)
def test_vendored_files_match_pin(pin_path: Path) -> None:
    skill = pin_path.parent
    pin = json.loads(pin_path.read_text())
    assert {"repo", "path", "commit", "files"} <= pin.keys()
    assert pin["files"], "pin lists no files"
    for rel, digest in pin["files"].items():
        data = (skill / rel).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, (
            f"{skill.name}/{rel} differs from upstream {pin['commit'][:7]}: "
            "put local changes in a separate skill, or run "
            "scripts/sync_upstream_skills.py --update"
        )
    local = {
        p.relative_to(skill).as_posix()
        for p in skill.rglob("*")
        if p.is_file() and p.name not in {"UPSTREAM.json", ".DS_Store"}
        and "__pycache__" not in p.parts
    }
    assert local == set(pin["files"]), f"unpinned files in {skill.name}: {local - set(pin['files'])}"
