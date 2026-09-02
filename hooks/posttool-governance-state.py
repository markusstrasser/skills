#!/usr/bin/env python3
"""Live-session bridge to the relocated governance hook."""

from pathlib import Path
import runpy


TARGET = Path.home() / ".agents/skills/hooks/posttool-governance-state.py"
if not TARGET.is_file():
    raise SystemExit(f"canonical governance hook is missing: {TARGET}")

runpy.run_path(str(TARGET), run_name="__main__")
