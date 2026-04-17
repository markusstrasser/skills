#!/usr/bin/env python3
"""POST a prompt to Quiver Arrow, write SVG(s) to disk."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://api.quiver.ai/v1/svgs/generations"


def _ok(msg: str) -> None:
    print(f"  \u2713 {msg}")


def _fail(msg: str) -> None:
    print(f"  \u2717 {msg}", file=sys.stderr)


def main() -> int:
    p = argparse.ArgumentParser(description="Generate SVG via Quiver Arrow API")
    p.add_argument("prompt", help="Text description of the desired SVG")
    p.add_argument("-o", "--output", default=None,
                   help="Output path (default: illustration-<ts>.svg). With --n>1, suffix _<i>.svg is appended.")
    p.add_argument("-m", "--model", default="arrow-1.1",
                   choices=["arrow-1.1", "arrow-1.1-max"],
                   help="Model. Use arrow-1.1-max for higher quality / detailed assets.")
    p.add_argument("-i", "--instructions", default=None,
                   help="Optional refinement instructions (style, palette, constraints).")
    p.add_argument("-n", "--n", type=int, default=1, help="Number of generations.")
    args = p.parse_args()

    key = os.environ.get("QUIVERAI_API_KEY")
    if not key:
        _fail("QUIVERAI_API_KEY not set. Get one at app.quiver.ai \u2192 API keys, then export it.")
        return 2

    body: dict = {"model": args.model, "prompt": args.prompt, "n": args.n}
    if args.instructions:
        body["instructions"] = args.instructions

    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        _fail(f"HTTP {e.code}: {detail[:500]}")
        return 1
    except urllib.error.URLError as e:
        _fail(f"Network error: {e.reason}")
        return 1

    items = payload.get("data") or []
    if not items:
        _fail(f"No SVG in response: {json.dumps(payload)[:500]}")
        return 1

    base = args.output or f"illustration-{int(time.time())}.svg"
    base_path = Path(base)
    written: list[Path] = []
    for idx, item in enumerate(items):
        svg = item.get("svg")
        if not svg or not svg.lstrip().startswith(("<svg", "<?xml")):
            _fail(f"Item {idx}: response did not contain SVG markup")
            return 1
        if len(items) == 1:
            out = base_path
        else:
            out = base_path.with_name(f"{base_path.stem}_{idx}{base_path.suffix or '.svg'}")
        out.write_text(svg)
        written.append(out)
        _ok(f"wrote {out} ({len(svg)} bytes)")

    if "credits" in payload:
        _ok(f"credits charged: {payload['credits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
