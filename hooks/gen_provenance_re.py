#!/usr/bin/env python3
"""Generate provenance_tags.re from the structured SSOT provenance_tags.json.

The .re is a grep-friendly PROJECTION of the JSON vocab — committed as a file so
bash hooks can `cat` it with zero python dependency. This generator is the only
writer of that projection; test_provenance_tags.py asserts
    gen_re(load_json()) == provenance_tags.re   (byte-for-byte)
so the JSON is authoritative and the .re can never drift from it.

Heads with "in_re": false are part of the vocabulary but DELIBERATELY excluded
from the .re (the global-hook matching surface) until an owner widens the hook.

Usage:
  gen_provenance_re.py            # print the generated .re to stdout
  gen_provenance_re.py --write    # rewrite provenance_tags.re in place
  gen_provenance_re.py --check    # exit 1 if the on-disk .re differs (CI gate)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JSON_PATH = HERE / "provenance_tags.json"
RE_PATH = HERE / "provenance_tags.re"


def _esc(head: str) -> str:
    """Escape the literal brackets the way the canonical .re does: \\[ \\]."""
    return head  # heads are bare words; only the brackets are escaped, added below


def gen_re(spec: dict) -> str:
    """Build the exact regex string (with trailing newline) from the JSON spec."""
    alts: list[str] = []
    for h in spec["heads"]:
        if not h.get("in_re", True):
            continue
        head = _esc(h["head"])
        payload = h["payload"]
        if payload == "required":
            # open bracket + head + colon, no close bracket — matches "[SOURCE: ...]"
            alts.append(rf"\[{head}:")
        elif payload == "bare":
            alts.append(rf"\[{head}\]")
        else:  # pragma: no cover - guard against an unknown payload rule
            raise ValueError(f"unknown payload rule {payload!r} for head {head!r}")
    # grade tags: [A-F][1-6] with an optional :reason, brackets escaped
    g = spec["grade_tags"]
    if g.get("in_re", True):
        alts.append(rf"\[{g['pattern']}(:[^]]+)?\]")
    # engine + genomics: bare bracketed names
    for name in spec.get("engine", []) + spec.get("genomics", []):
        alts.append(rf"\[{name}\]")
    return "|".join(alts) + "\n"


def load_json() -> dict:
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def main() -> int:
    spec = load_json()
    generated = gen_re(spec)
    if "--write" in sys.argv:
        RE_PATH.write_text(generated, encoding="utf-8")
        print(f"wrote {RE_PATH} ({len(generated.encode())} bytes)", file=sys.stderr)
        return 0
    if "--check" in sys.argv:
        on_disk = RE_PATH.read_text(encoding="utf-8")
        if on_disk != generated:
            print("DRIFT: provenance_tags.re does not match gen from json", file=sys.stderr)
            return 1
        print("ok: provenance_tags.re matches json", file=sys.stderr)
        return 0
    sys.stdout.write(generated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
