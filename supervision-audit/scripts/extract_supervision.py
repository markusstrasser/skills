#!/usr/bin/env python3
"""Extract user supervision patterns from Claude Code session transcripts.

Classifies each user message as either:
  - NEW_AGENCY: genuine new direction, idea, decision (valuable human input)
  - CORRECTION: fixing agent mistake, redirecting, repeating known rules
  - BOILERPLATE: repeated instructions that should be defaults
  - RUBBER_STAMP: low-information approval ("ok fix", "do it")
  - RE_ORIENT: continuations, "where was I", resuming after context loss

Outputs structured JSON and a summary report for LLM synthesis.

Usage:
    python3 extract_supervision.py [--days N] [--project PROJECT] [--output FILE]

Examples:
    python3 extract_supervision.py                          # Today, all projects
    python3 extract_supervision.py --days 3 --project intel # Last 3 days, intel only
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


TRANSCRIPT_BASE = Path.home() / ".claude" / "projects"

# --- Pattern definitions ---

RUBBER_STAMP_EXACT = {
    "ok", "ok fix", "ok do it", "yes", "do it", "implement all",
    "alright do it", "yes do it", "implement", "go ahead", "go",
    "yes go ahead", "sure", "yep", "yep do it", "ok cool",
    "sounds good do it", "lgtm", "ship it", "ok fix it",
    "ok implement", "implement it", "yes fix", "ok go",
}

BOILERPLATE_PATTERNS = [
    (r"IFF everything works.*git commit", "commit-boilerplate"),
    (r"git commit your changes granuarly", "commit-boilerplate"),
    (r"Do not add.*claude.*collab", "commit-no-coauthor"),
    (r"Keep commit messages.*1-2 sentence", "commit-format"),
    (r"Update the docs.*readme.*Claude\.md", "update-docs-reminder"),
]

CORRECTION_PATTERNS = [
    (r"use uv\b", "env-uv-not-conda"),
    (r"not conda", "env-uv-not-conda"),
    (r"python3 not python\b", "env-python3"),
    (r"don't already (have|download)", "idempotency-check"),
    (r"we already (have|download)", "idempotency-check"),
    (r"make sure we don't already", "idempotency-check"),
    (r"are you sure.*include", "completeness-verify"),
    (r"did you include all", "completeness-verify"),
    (r"is that all", "completeness-verify"),
    (r"anything missing", "completeness-verify"),
    (r"fully in there", "completeness-verify"),
    (r"download it yourself", "capability-nudge"),
    (r"why not\?$", "capability-nudge"),
    (r"Continue from where", "context-resume"),
    (r"where (were|was) (we|I|you)", "context-resume"),
    (r"you (missed|forgot|skipped)", "agent-omission"),
    (r"that's not (what|right)", "agent-wrong"),
    (r"no[,.]+ (that's|I said|we)", "agent-wrong"),
    (r"I (said|told you|already)", "repeat-instruction"),
    (r"stop[.!]", "halt"),
]

REORIENT_PATTERNS = [
    (r"continued from a previous conversation", "context-exhaustion"),
    (r"ran out of context", "context-exhaustion"),
]

DEEPER_PATTERNS = [
    (r"go deeper", "depth-nudge"),
    (r"dig deeper", "depth-nudge"),
    (r"deeper audit", "depth-nudge"),
    (r"more thorough", "depth-nudge"),
]


def classify_message(text: str) -> tuple[str, str]:
    """Classify a user message. Returns (category, sub_pattern)."""
    clean = text.strip()
    lower = clean.lower()

    # Skip system messages / task notifications / skill expansions
    if clean.startswith("<task-notification") or clean.startswith("<local-command"):
        return ("SYSTEM", "system")
    if clean.startswith("<command-name>"):
        return ("SYSTEM", "slash-command")
    if clean.startswith("Base directory for this skill:"):
        return ("SYSTEM", "skill-expansion")
    if clean.startswith("Stop hook feedback:"):
        return ("SYSTEM", "hook-feedback")
    if "session is being continued from a previous conversation" in clean:
        return ("SYSTEM", "context-continuation")

    # Rubber stamps (exact match on short messages)
    if lower.rstrip(".!") in RUBBER_STAMP_EXACT and len(clean) < 50:
        return ("RUBBER_STAMP", "approval")

    # Re-orientation after context loss
    for pattern, name in REORIENT_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            return ("RE_ORIENT", name)

    # Boilerplate (repeated instructions)
    for pattern, name in BOILERPLATE_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            return ("BOILERPLATE", name)

    # Corrections — only match short-ish messages (long ones are likely plans/context)
    if len(clean) < 500:
        for pattern, name in CORRECTION_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE):
                return ("CORRECTION", name)

    # Depth nudges — borderline, could be new agency or correction
    for pattern, name in DEEPER_PATTERNS:
        if re.search(pattern, lower):
            return ("CORRECTION", name)

    # Default: genuine new agency
    return ("NEW_AGENCY", "direction")


def process_session(path: Path) -> dict:
    """Process a single JSONL session file."""
    session_id = path.stem
    messages = []
    start_time = None
    end_time = None

    # Skip agent/compact files
    if "agent-" in session_id or "compact" in session_id:
        return None

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            timestamp = obj.get("timestamp")
            if timestamp:
                if start_time is None:
                    start_time = timestamp
                end_time = timestamp

            if obj.get("type") == "user":
                content = obj.get("message", {}).get("content", "")
                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                    content = " ".join(parts)

                if not isinstance(content, str) or len(content) < 3:
                    continue

                category, sub = classify_message(content)
                messages.append({
                    "category": category,
                    "sub_pattern": sub,
                    "text": content[:500],
                    "length": len(content),
                })

    if not messages:
        return None

    return {
        "session_id": session_id[:12],
        "start_time": start_time,
        "end_time": end_time,
        "total_user_messages": len(messages),
        "messages": messages,
    }


def find_sessions(project: str | None, days: int) -> list[Path]:
    """Find session files within the time window."""
    cutoff = datetime.now().timestamp() - (days * 86400)
    results = []

    for d in TRANSCRIPT_BASE.iterdir():
        if not d.is_dir():
            continue
        if project and project.lower() not in d.name.lower():
            continue
        for f in d.glob("*.jsonl"):
            if f.stat().st_mtime >= cutoff:
                if "agent-" not in f.name and "compact" not in f.name:
                    results.append(f)

    return sorted(results, key=lambda p: p.stat().st_mtime, reverse=True)


def main():
    parser = argparse.ArgumentParser(description="Extract supervision patterns")
    parser.add_argument("--days", type=int, default=1, help="Days back (default: 1)")
    parser.add_argument("--project", help="Filter to project (intel, selve, meta, etc.)")
    parser.add_argument("--output", "-o", help="Output JSON file (default: stdout report)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of report")
    args = parser.parse_args()

    sessions = find_sessions(args.project, args.days)
    if not sessions:
        print(f"No sessions found (days={args.days}, project={args.project})", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sessions)} sessions...", file=sys.stderr)

    results = []
    for s in sessions:
        r = process_session(s)
        if r:
            results.append(r)

    # Aggregate stats
    totals = {"NEW_AGENCY": 0, "CORRECTION": 0, "BOILERPLATE": 0, "RUBBER_STAMP": 0, "RE_ORIENT": 0, "SYSTEM": 0}
    sub_counts = {}
    correction_examples = []
    boilerplate_examples = []

    for sess in results:
        for msg in sess["messages"]:
            cat = msg["category"]
            totals[cat] = totals.get(cat, 0) + 1
            sub = msg["sub_pattern"]
            sub_counts[sub] = sub_counts.get(sub, 0) + 1

            if cat == "CORRECTION" and len(correction_examples) < 20:
                proj = "?"
                correction_examples.append({
                    "session": sess["session_id"],
                    "pattern": sub,
                    "text": msg["text"][:200],
                })
            elif cat == "BOILERPLATE" and len(boilerplate_examples) < 10:
                boilerplate_examples.append({
                    "session": sess["session_id"],
                    "pattern": sub,
                    "text": msg["text"][:200],
                })

    total_msgs = sum(totals.values()) - totals.get("SYSTEM", 0)
    wasted = totals["CORRECTION"] + totals["BOILERPLATE"] + totals["RUBBER_STAMP"] + totals["RE_ORIENT"]

    output = {
        "period": f"last {args.days} day(s)",
        "project_filter": args.project or "all",
        "sessions_analyzed": len(results),
        "total_user_messages": total_msgs,
        "wasted_supervision": wasted,
        "wasted_pct": round(100 * wasted / total_msgs, 1) if total_msgs else 0,
        "breakdown": {k: v for k, v in totals.items() if k != "SYSTEM"},
        "sub_pattern_counts": dict(sorted(sub_counts.items(), key=lambda x: -x[1])),
        "correction_examples": correction_examples,
        "boilerplate_examples": boilerplate_examples,
    }

    if args.json or args.output:
        text = json.dumps(output, indent=2)
        if args.output:
            Path(args.output).write_text(text)
            print(f"Written to {args.output}", file=sys.stderr)
        else:
            print(text)
    else:
        # Human-readable report
        print(f"\n{'='*60}")
        print(f"SUPERVISION AUDIT — {output['period']}, {output['project_filter']}")
        print(f"{'='*60}")
        print(f"Sessions: {output['sessions_analyzed']}")
        print(f"User messages: {output['total_user_messages']}")
        print(f"Wasted supervision: {output['wasted_supervision']} ({output['wasted_pct']}%)")
        print()
        print("BREAKDOWN:")
        for cat, count in output["breakdown"].items():
            pct = round(100 * count / total_msgs, 1) if total_msgs else 0
            print(f"  {cat:20s}: {count:4d} ({pct}%)")
        print()
        print("SUB-PATTERNS (top 15):")
        for sub, count in list(output["sub_pattern_counts"].items())[:15]:
            if sub in ("direction", "system", "slash-command"):
                continue
            print(f"  {sub:30s}: {count}")
        print()
        if correction_examples:
            print("CORRECTION SAMPLES:")
            for ex in correction_examples[:8]:
                print(f"  [{ex['session'][:8]}] ({ex['pattern']}): {ex['text'][:120]}")
            print()


if __name__ == "__main__":
    main()
