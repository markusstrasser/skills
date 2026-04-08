#!/usr/bin/env python3
"""Validate session IDs in Gemini output against the extraction manifest.

Reads input.md for the VALID SESSION IDS table, then checks gemini-output.md
for any 8-char hex patterns that aren't in the allowlist. Reports fabricated
IDs and optionally strips them from findings.

Usage:
    python validate_session_ids.py [--input FILE] [--output FILE] [--strip]

Defaults to session-analyst artifact paths.
"""

import argparse
import re
import sys
from pathlib import Path

ARTIFACT_DIR = Path.home() / "Projects/meta/artifacts/session-analyst"
HEX8_PATTERN = re.compile(r"\b([0-9a-f]{8})\b")
MANIFEST_ROW = re.compile(r"\|\s*([0-9a-f]{8})\s*\|")


def extract_manifest(input_text: str) -> set[str]:
    """Extract valid session ID prefixes from the VALID SESSION IDS table."""
    return set(MANIFEST_ROW.findall(input_text))


def extract_referenced_ids(gemini_text: str) -> set[str]:
    """Extract all 8-char hex strings from Gemini output."""
    return set(HEX8_PATTERN.findall(gemini_text))


def validate(input_path: Path, gemini_path: Path) -> dict:
    """Validate Gemini output IDs against manifest. Returns report dict."""
    input_text = input_path.read_text()
    gemini_text = gemini_path.read_text()

    valid_ids = extract_manifest(input_text)
    referenced_ids = extract_referenced_ids(gemini_text)

    # Only flag hex strings that appear near session-referencing context
    # (not random hex in code snippets, hashes, etc.)
    session_context = re.compile(
        r"(?:session|Session|SESSION|uuid|UUID)\s*[:=]?\s*\b([0-9a-f]{8})\b"
        r"|\*\*Session:\*\*\s*\b([0-9a-f]{8})\b"
    )
    contextual_ids = set()
    for m in session_context.finditer(gemini_text):
        contextual_ids.add(m.group(1) or m.group(2))

    fabricated = contextual_ids - valid_ids
    valid_refs = contextual_ids & valid_ids
    unreferenced = valid_ids - contextual_ids

    return {
        "valid_ids": sorted(valid_ids),
        "referenced_ids": sorted(contextual_ids),
        "fabricated": sorted(fabricated),
        "valid_refs": sorted(valid_refs),
        "unreferenced": sorted(unreferenced),
    }


def strip_fabricated(gemini_text: str, fabricated: set[str]) -> str:
    """Replace fabricated session IDs with [FABRICATED_ID]."""
    result = gemini_text
    for fid in fabricated:
        result = result.replace(fid, "[FABRICATED_ID]")
    return result


def main():
    parser = argparse.ArgumentParser(description="Validate session IDs in Gemini output")
    parser.add_argument("--input", "-i", type=Path, default=ARTIFACT_DIR / "input.md")
    parser.add_argument("--gemini", "-g", type=Path, default=ARTIFACT_DIR / "gemini-output.md")
    parser.add_argument("--strip", action="store_true", help="Replace fabricated IDs in output")
    parser.add_argument("--output", "-o", type=Path, help="Write stripped output to file")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"✗ Input not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if not args.gemini.exists():
        print(f"✗ Gemini output not found: {args.gemini}", file=sys.stderr)
        sys.exit(1)

    report = validate(args.input, args.gemini)

    print(f"  Manifest IDs: {len(report['valid_ids'])} {report['valid_ids']}")
    print(f"  Referenced:   {len(report['referenced_ids'])} {report['referenced_ids']}")

    if report["fabricated"]:
        print(f"  ✗ Fabricated: {len(report['fabricated'])} {report['fabricated']}")
    else:
        print(f"  ✓ No fabricated session IDs")

    if report["unreferenced"]:
        print(f"  ! Unreferenced sessions: {report['unreferenced']}")

    if args.strip and report["fabricated"]:
        gemini_text = args.gemini.read_text()
        cleaned = strip_fabricated(gemini_text, set(report["fabricated"]))
        out_path = args.output or args.gemini
        out_path.write_text(cleaned)
        print(f"  ✓ Stripped {len(report['fabricated'])} fabricated IDs → {out_path}")

    sys.exit(1 if report["fabricated"] else 0)


if __name__ == "__main__":
    main()
