#!/usr/bin/env python3
"""Pangram AI-text detection — empirical slop check.

Calls Pangram Labs' V3 detector (a trained classifier) and reports an
AI-likelihood score. Complements de-slop's heuristic taxonomy: the taxonomy
explains *why* prose reads as AI; Pangram gives an empirical *score*.

Stdlib-only (urllib) — runs with bare `python3` from any project, no deps.

Usage:
    python3 pangram.py "text to check"            # inline text
    python3 pangram.py -f draft.md                # a file
    git diff | python3 pangram.py                  # stdin
    python3 pangram.py -f essay.md --split paragraph   # score each paragraph
    python3 pangram.py -f essay.md --json          # raw API JSON

Env: PANGRAM_API_KEY (auto-loaded from CWD/.env.local, CWD/.env, or ~/.env).

Cost: each chunk sent is one Pangram request (consumes account credits).
`--split` sends one request per chunk — mind the count on large inputs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://text.api.pangram.com/v3"


def _load_dotenv() -> None:
    """Load PANGRAM_API_KEY from .env files if not already in the shell env.

    Search order (shell env wins, stops at first file that defines the key):
    CWD/.env.local → CWD/.env → ~/.env.
    """
    if os.environ.get("PANGRAM_API_KEY"):
        return
    for env_file in (Path.cwd() / ".env.local", Path.cwd() / ".env", Path.home() / ".env"):
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.removeprefix("export ").strip()
            if key != "PANGRAM_API_KEY":
                continue
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault("PANGRAM_API_KEY", value)
            return


def detect(text: str, api_key: str, timeout: int = 60) -> dict:
    """POST text to Pangram /v3, return parsed response dict."""
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"text": text}).encode(),
        headers={"Content-Type": "application/json", "x-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise SystemExit("✗ 401 — PANGRAM_API_KEY missing/invalid or out of credits")
        if e.code == 400:
            raise SystemExit("✗ 400 — bad request (text empty or malformed?)")
        raise SystemExit(f"✗ Pangram HTTP {e.code}: {e.read().decode(errors='replace')[:200]}")
    except urllib.error.URLError as e:
        raise SystemExit(f"✗ network error reaching Pangram: {e.reason}")


def _read_input(args) -> str:
    if args.text:
        return args.text
    if args.file:
        return Path(args.file).read_text()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("✗ no input — pass text, -f FILE, or pipe via stdin")


def _chunks(text: str, mode: str) -> list[str]:
    if mode == "paragraph":
        return [c.strip() for c in text.split("\n\n") if c.strip()]
    if mode == "line":
        return [c.strip() for c in text.splitlines() if c.strip()]
    return [text]


def _marker(pred_short: str) -> str:
    return {"AI": "✗", "AI-Assisted": "!", "Mixed": "!", "Human": "✓"}.get(pred_short, "?")


def _print_doc(result: dict) -> None:
    print(f"{_marker(result['prediction_short'])} {result['headline']} "
          f"(AI {result['fraction_ai']:.0%} / assisted {result['fraction_ai_assisted']:.0%} "
          f"/ human {result['fraction_human']:.0%})")
    print(f"  {result['prediction']}")
    flagged = [w for w in result.get("windows", []) if w["ai_assistance_score"] >= 0.5]
    if flagged and len(result.get("windows", [])) > 1:
        print(f"\n  Flagged segments ({len(flagged)}/{len(result['windows'])}):")
        for w in flagged:
            snippet = w["text"].replace("\n", " ").strip()
            if len(snippet) > 80:
                snippet = snippet[:77] + "..."
            print(f"  {_marker_for_score(w['ai_assistance_score'])} [{w['start_index']}:{w['end_index']}] "
                  f"score={w['ai_assistance_score']:.2f} {w['confidence']:<6} — {snippet}")


def _marker_for_score(score: float) -> str:
    return "✗" if score >= 0.8 else "!"


def _print_split(chunks: list[str], results: list[dict]) -> None:
    n = len(chunks)
    ai_count = 0
    for i, (chunk, res) in enumerate(zip(chunks, results), 1):
        if res["prediction_short"] in ("AI", "AI-Assisted", "Mixed"):
            ai_count += 1
        snippet = chunk.replace("\n", " ").strip()
        if len(snippet) > 70:
            snippet = snippet[:67] + "..."
        print(f"  [{i}/{n}] {_marker(res['prediction_short'])} {res['prediction_short']:<12} "
              f"ai={res['fraction_ai']:.0%} — {snippet}")
    print(f"\n  {ai_count}/{n} chunks flagged AI / AI-assisted")


def main() -> None:
    p = argparse.ArgumentParser(description="Pangram AI-text detection (slop check).")
    p.add_argument("text", nargs="?", help="text to check (or use -f / stdin)")
    p.add_argument("-f", "--file", help="read text from a file")
    p.add_argument("--split", choices=["none", "paragraph", "line"], default="none",
                   help="check whole doc (default), or each paragraph/line separately")
    p.add_argument("--json", action="store_true", help="emit raw API JSON")
    p.add_argument("--fail-on-ai", action="store_true",
                   help="exit 2 if the verdict is AI / AI-Assisted / Mixed (for gating)")
    args = p.parse_args()

    _load_dotenv()
    api_key = os.environ.get("PANGRAM_API_KEY")
    if not api_key:
        raise SystemExit("✗ PANGRAM_API_KEY not set (add to ~/.env or export it)")

    text = _read_input(args)
    chunks = _chunks(text, args.split)
    results = [detect(c, api_key) for c in chunks]

    if args.json:
        print(json.dumps(results if args.split != "none" else results[0], indent=2))
    elif args.split != "none":
        _print_split(chunks, results)
    else:
        _print_doc(results[0])

    if args.fail_on_ai:
        verdicts = {r["prediction_short"] for r in results}
        if verdicts & {"AI", "AI-Assisted", "Mixed"}:
            sys.exit(2)


if __name__ == "__main__":
    main()
