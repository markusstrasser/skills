"""Key contract for /critique findings.json, shared by every reader.

CLI extraction transports cannot enforce the finding schema, so models name the keys
themselves. From 2026-07 most findings carried ``file_path``/``proposed_fix``; every
reader looked up ``file``/``fix`` and found nothing (disposition "File: N/A", no verify
anchors, review_gate ranking without file credit). model-review.py maps the aliases at
extraction; integration_audit.load_findings (also used by review_gate and outcome_link)
maps them for findings.json files saved before that.
"""

from __future__ import annotations

FINDING_KEY_ALIASES = {"file_path": "file", "proposed_fix": "fix"}


def normalize_finding_keys(finding: dict) -> dict:
    """Rename observed alias keys to the schema keys in place; return the finding."""
    for alias, key in FINDING_KEY_ALIASES.items():
        if alias in finding and not finding.get(key):
            finding[key] = finding.pop(alias)
    return finding
