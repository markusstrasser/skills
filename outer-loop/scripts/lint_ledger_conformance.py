#!/usr/bin/env python3
"""lint_ledger_conformance.py — check a repo's ledger provides the fields the outer-loop reads.

A copied schema with no check recreates the drift the shared schema exists to fix (ADR
2026-06-13). This linter is the check. It runs in each repo's `just smoke`.

It does NOT force a repo to rename its columns. The repo's `LOOP.md` carries a
`ledger.field_map` (canonical → that repo's actual column); the linter resolves every REQUIRED
canonical field through the map and asserts the mapped column exists in the repo's ledger. So
hutter keeps `variant`/`s_bytes`/`predicted_ds` and still conforms (they map to
candidate/score/predicted_score).

Field tiers come from references/ledger-schema.sql:
  REQUIRED      — absent → FAIL (exit 1).
  REQUIRED-IF   — added to REQUIRED when the contract's regime reads them (clean → score+predicted_score;
                  clean-expensive → +proxy_score, ground_truth_score, budget_consumed).
  RECOMMENDED   — absent → WARN (advisory; measure-before-enforce). Never fails the build.

Ledger introspection supports .sql schema files (executed into :memory: — real SQL parsing, no
regex), live .db files (PRAGMA table_info), and .jsonl event logs (keys across a sample).

Usage:
  lint_ledger_conformance.py --contract path/to/LOOP.md
  lint_ledger_conformance.py --contract LOOP.md --schema-root .   # resolve ledger.path against this root

Needs pyyaml (the contract is YAML). Missing pyyaml is a FAIL, not a silent skip — a conformance
check that silently doesn't run is the exact silent-proxy failure this guards against.
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import NoReturn

CORE_REQUIRED = ["ts", "candidate", "verdict", "lineage_parent", "dead_end", "tags"]
CLEAN_REQUIRED = ["score", "predicted_score"]
EXPENSIVE_REQUIRED = ["proxy_score", "ground_truth_score", "budget_consumed"]
RECOMMENDED = [
    "reason", "gate_command", "gate_version", "artifact_hash", "data_snapshot",
    "env_version", "proposer_version", "skill_version", "quarantine_state", "rollback_pointer",
]


def _fail(msg: str) -> NoReturn:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_contract(path: Path) -> dict:
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        _fail("conformance linter needs pyyaml (the contract is YAML): `uv add pyyaml`. "
              "Refusing to silently skip the check.")
    text = path.read_text()
    # The contract is either YAML frontmatter (--- ... ---) or the first ```yaml fence.
    if text.lstrip().startswith("---"):
        body = text.lstrip()[3:]
        end = body.find("\n---")
        block = body[:end] if end >= 0 else body
    elif "```yaml" in text:
        start = text.index("```yaml") + len("```yaml")
        block = text[start:text.index("```", start)]
    else:
        _fail(f"{path}: no YAML frontmatter or ```yaml block found")
    data = yaml.safe_load(block)
    if not isinstance(data, dict):
        _fail(f"{path}: contract did not parse to a mapping")
    return data


def ledger_columns(schema_path: Path, table: str) -> set[str]:
    suffix = schema_path.suffix.lower()
    if not schema_path.exists():
        _fail(f"ledger path does not exist: {schema_path}")
    if suffix == ".sql":
        con = sqlite3.connect(":memory:")
        try:
            con.executescript(schema_path.read_text())
        except sqlite3.Error as e:
            _fail(f"could not load schema {schema_path}: {e}")
        cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
        if not cols:
            _fail(f"table {table!r} not found in {schema_path} (check ledger.table in the contract)")
        return cols
    if suffix == ".db":
        con = sqlite3.connect(str(schema_path))
        cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
        if not cols:
            _fail(f"table {table!r} not found in {schema_path}")
        return cols
    if suffix in (".jsonl", ".ndjson"):
        cols: set[str] = set()
        with schema_path.open() as f:
            for i, line in enumerate(f):
                if i >= 200:
                    break
                line = line.strip()
                if line:
                    cols |= set(json.loads(line).keys())
        if not cols:
            _fail(f"no records to introspect in {schema_path}")
        return cols
    _fail(f"unsupported ledger format {suffix!r} (want .sql/.db/.jsonl)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True, type=Path)
    ap.add_argument("--schema-root", type=Path, default=None,
                    help="resolve ledger.path against this dir (default: the contract's dir)")
    a = ap.parse_args()

    contract = load_contract(a.contract)
    regime = (contract.get("verifier") or {}).get("regime")
    ledger = contract.get("ledger") or {}
    raw_path = ledger.get("path")
    table = ledger.get("table", "ledger")
    field_map = ledger.get("field_map") or {}
    if not regime:
        _fail("contract missing verifier.regime")
    # Git-native ledgers (the research loop: git history + CYCLE.md + failed-experiments fingerprints)
    # have no SQL/jsonl table — SQL field conformance does not apply. Skip cleanly, don't hard-fail.
    if ledger.get("kind") == "git-native":
        print(f"✓ ledger conformance N/A: {a.contract.name} [{regime}] — git-native ledger "
              "(checked via git: CYCLE.md + failed-experiments, not SQL fields).")
        return 0
    if not raw_path:
        _fail("contract missing ledger.path (and ledger.kind is not 'git-native')")

    root = a.schema_root or a.contract.resolve().parent
    schema_path = (root / raw_path).resolve()
    columns = ledger_columns(schema_path, table)

    required = list(CORE_REQUIRED)
    if regime in ("clean-cheap", "clean-expensive"):
        required += CLEAN_REQUIRED
    if regime == "clean-expensive":
        required += EXPENSIVE_REQUIRED

    def resolved(canonical: str) -> str:
        return field_map.get(canonical, canonical)

    failures, warnings = [], []
    for canon in required:
        col = resolved(canon)
        if col not in columns:
            failures.append(f"REQUIRED {canon!r} → column {col!r} not in {table} ({schema_path.name})")
    for canon in RECOMMENDED:
        col = resolved(canon)
        if col not in columns:
            warnings.append(f"RECOMMENDED {canon!r} → column {col!r} absent")

    label = f"{a.contract.parent.name}/{a.contract.name} [{regime}]"
    for w in warnings:
        print(f"WARN  {label}: {w}")
    if failures:
        for fmsg in failures:
            print(f"FAIL  {label}: {fmsg}", file=sys.stderr)
        print(f"\n✗ ledger conformance FAILED: {len(failures)} required field(s) unmapped.",
              file=sys.stderr)
        return 1
    print(f"✓ ledger conformance OK: {label} — {len(required)} required field(s) present, "
          f"{len(warnings)} recommended absent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
