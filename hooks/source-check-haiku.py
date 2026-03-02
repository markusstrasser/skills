#!/usr/bin/env python3
"""Semantic source citation check via Haiku.

Reads file content from stdin, calls Haiku to rate source coverage.
Outputs JSON with additionalContext if issues found.
"""
import json
import os
import sys
import urllib.request

PROMPT = """Rate this research file's overall source coverage on a 3-point scale.

A sourced claim has a bracket citation like [PubMed], [arXiv], [SOURCE: url], [A1]-[F6], [DATA], [INFERENCE], [ClinGen], [CPIC], [gnomAD], etc. Inline author attributions ("per Smith et al.", "Jaiswal 2017") also count.

Be generous. Skip: headers, instructions, task descriptions, common knowledge, variant IDs (like m.3243A>G, rs numbers), project-internal references, working-doc language. Plans and execution docs have looser standards than final research memos.

Respond with ONE line:
- GOOD — if most key claims have some attribution
- SPARSE — if several important quantitative or novel claims lack any attribution
- NONE — if the file has zero source attribution despite making empirical claims

If SPARSE or NONE, add up to 3 examples of the most important gaps (one line each, terse).

File content:
"""


def main():
    content = sys.stdin.read().strip()
    if not content:
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return

    fname = sys.argv[1] if len(sys.argv) > 1 else "unknown"

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 256,
        "messages": [{"role": "user", "content": PROMPT + content}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            text = result["content"][0]["text"].strip()
    except Exception:
        return

    # Only output if SPARSE or NONE
    first_line = text.split("\n")[0].upper()
    if "SPARSE" in first_line or "NONE" in first_line:
        msg = f"[source-check] {fname}: {text}"
        print(json.dumps({"additionalContext": msg}))


if __name__ == "__main__":
    main()
