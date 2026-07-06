#!/usr/bin/env python3
"""subagent-empty-research-shadow.py — SHADOW: researcher did N research calls, wrote 0 findings.

Backs steward-proposal 2026-06-21-researcher-pathological-empty-stop-gate.md. The proposal is
explicitly "do NOT ship blind" — a Stop gate that blocks a legitimate CORAL *partial* checkpoint
(some findings + honest [GAP]s) would FIGHT the design (iatrogenic). So this ships as SHADOW:
it LOGS would-fire, never blocks, so the promotion review can confirm 0 false-positives on REAL
researcher stops before any advisory/block promotion (measure-before-enforcing, constitution P3).

The separable pathological invariant (distinguishable from a legitimate partial):
  research_calls >= N   AND   the episode wrote essentially NOTHING (only a stub)
    - research_calls: transcript tool_use in {Read, Grep, Glob, WebFetch, WebSearch,
      mcp__research__*, mcp__exa__*, mcp__perplexity__*, mcp__brave-search__*}
    - "wrote nothing": total Write/Edit/MultiEdit content this episode is stub-sized
      (< STUB_MAX chars) AND carries no provenance tag. A researcher who APPENDED real findings
      (bulk content, or any [DATA]/[SOURCE]/[DATABASE]/[INFERENCE]/[UNVERIFIED] tag) -> PASS.
    - Rationale: the earlier "no provenance tag" signal alone fired on 76/485 real transcripts
      (coding subagents Read+Write with no tags) — total-written-chars is the signal that actually
      separates "still just the stub" from "wrote a lot". Measured 2026-07-06 before shipping: the
      revised predicate fires on 9/486 recent transcripts, ALL with write_calls==0 (genuinely wrote
      nothing). Deployed researcher-Stop-only (researcher.md), so the live population is researcher
      subagents, where "researched a lot, wrote 0 files" is exactly the pathological target.

Never blocks (exit 0, no stdout). Fail-open on any error. Reversibility: delete the file + the
one fire-and-forget call in subagent-source-check-stop.sh.

Promotion gate (do NOT auto-promote): dry-run ~/.claude/subagent-empty-research-shadow.jsonl over
>=2 weeks of real fires; confirm every would-fire is a true pathological-empty (0 FP) and legitimate
partials never appear; tune N; only THEN convert to advisory, and only later to block.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

SHADOW_LOG = os.path.expanduser("~/.claude/subagent-empty-research-shadow.jsonl")
N_RESEARCH_CALLS = 6  # threshold; tune during the promotion review
STUB_MAX = 400  # total Write/Edit content chars below which the episode wrote "only a stub"

_RESEARCH_PREFIXES = ("mcp__research__", "mcp__exa__", "mcp__perplexity__", "mcp__brave-search__")
_RESEARCH_NAMES = {"Read", "Grep", "Glob", "WebFetch", "WebSearch"}
_PROV_TAG = re.compile(r"\[(?:DATA|SOURCE|DATABASE|INFERENCE|UNVERIFIED)\b")


def _is_research(name: str) -> bool:
    return name in _RESEARCH_NAMES or any(name.startswith(p) for p in _RESEARCH_PREFIXES)


def _tool_uses(transcript_path: str):
    """Yield (tool_name, input_dict) for each assistant tool_use in the subagent transcript."""
    path = os.path.expanduser(transcript_path or "")
    if not path or not os.path.exists(path):
        return
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "assistant":
                continue
            content = obj.get("message", {}).get("content", "")
            if not isinstance(content, list):
                continue
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    yield c.get("name", ""), (c.get("input") or {})


def evaluate(transcript_path: str, n_threshold: int = N_RESEARCH_CALLS) -> dict:
    research_calls = 0
    tagged_writes = 0
    write_calls = 0
    write_chars = 0
    for name, inp in _tool_uses(transcript_path):
        if _is_research(name):
            research_calls += 1
        elif name in ("Write", "Edit", "MultiEdit"):
            write_calls += 1
            blob = " ".join(
                str(inp.get(k, "")) for k in ("content", "new_string", "new_str")
            )
            write_chars += len(blob)
            if _PROV_TAG.search(blob):
                tagged_writes += 1
    # Pathological-empty = researched a lot AND wrote only a stub (few chars, no provenance tag).
    # Any bulk content OR any provenance tag == real findings appended -> PASS (CORAL-correct).
    would_fire = (
        research_calls >= n_threshold and write_chars < STUB_MAX and tagged_writes == 0
    )
    return {
        "research_calls": research_calls,
        "write_calls": write_calls,
        "write_chars": write_chars,
        "tagged_writes": tagged_writes,
        "would_fire": would_fire,
    }


def main() -> int:
    try:
        inp = json.load(sys.stdin)
    except Exception:
        return 0  # fail open
    try:
        rec = evaluate(inp.get("transcript_path", ""))
        # Log only the would-fire cases (bounded) so the promotion review reads clean.
        if rec["would_fire"]:
            rec["ts"] = datetime.now(timezone.utc).isoformat()
            rec["session_id"] = inp.get("session_id")
            os.makedirs(os.path.dirname(SHADOW_LOG), exist_ok=True)
            with open(SHADOW_LOG, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
    except Exception:
        pass
    return 0  # SHADOW: never act.


if __name__ == "__main__":
    sys.exit(main())
