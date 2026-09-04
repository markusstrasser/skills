#!/usr/bin/env python3
# Gov-ID: hook:secret-path-read-guard
# goal: deterministic Read/Grep/Glob-side twin of the Bash secret-path gate
# verifier: skills/hooks/test_secret_path_guard.py
# blast_radius: shared
"""PreToolUse(Read|Grep|Glob) — refuse tool reads under the operator's secret stores.

Twin of the Bash dispatcher's `secret-path-guard`; both load the ONE protected-path definition
in `pretool_secret_path_guard.py`. Together they replace the settings.json `Read()` deny rules
that made the auto-mode permission classifier stop for a human on unresolvable paths
(2026-09-04). Fail-open on malformed input, like every PreToolUse hook here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pretool_secret_path_guard import offending_secret_path, reason  # noqa: E402

_PATH_KEYS = ("file_path", "path", "pattern", "notebook_path")


def main() -> int:
    try:
        envelope = json.load(sys.stdin)
    except Exception:
        return 0
    tool = str(envelope.get("tool_name") or "Read")
    tool_input = envelope.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    text = "\n".join(str(tool_input.get(key) or "") for key in _PATH_KEYS)
    token = offending_secret_path(text)
    if token is None:
        return 0
    sys.stderr.write(reason(token, tool) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
