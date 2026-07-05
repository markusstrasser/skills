#!/usr/bin/env python3
"""Extract #f / #g feedback from user messages in Claude Code session transcripts.

The user drops `#f` (ground-truth feedback) or `#g` (global issue) inline during
sessions. The text after it carries the meaning — no predefined taxonomy.

Usage:
    uv run python3 scripts/extract_user_tags.py [--days N] [--project P] [--tag f|g] [--json]

Scans ~/.claude/projects/*/UUID.jsonl for user messages containing the tag.

Transcript format note (the 2026-07-05 silent-false-zero fix): Claude Code lines
are ``{"type":"user","message":{"role":"user","content":...}}`` — the text lives
INSIDE the ``message`` dict. The original ``msg.get("content", msg.get("message"))``
fallback returned that dict (neither str nor list), so every modern transcript
yielded text="" and the extractor reported 0 forever. ``_message_texts`` below is
the single format-aware reader; ``test_extract_user_tags.py`` pins it.
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import os

# Inlined from meta/scripts/common/paths.py and meta/scripts/config.py
_CLAUDE_DIR = Path(os.environ.get("CLAUDE_DIR", str(Path.home() / ".claude")))
PROJECTS_DIR = _CLAUDE_DIR / "projects"


def extract_project_name(dir_name: str) -> str:
    """Convert dir name like '-Users-alien-Projects-intel' to 'intel'."""
    parts = dir_name.split("-")
    for i, p in enumerate(parts):
        if p == "Projects" and i + 1 < len(parts):
            return "-".join(parts[i + 1:])
    return dir_name

def tag_re(tag: str) -> re.Pattern:
    """Word-boundary match for #<tag> (not #foo, #function, etc.)."""
    return re.compile(rf"(?:^|\s)#{re.escape(tag)}(?=\s|$|[.,;:!?)])", re.MULTILINE)


def _message_texts(msg: dict) -> list[str]:
    """Return the user-authored text blocks of one transcript line, any format.

    Handles both the flat legacy shape ({"role":"user","content":...}) and the
    Claude Code envelope ({"type":"user","message":{"role":"user","content":...}}).
    Content may be a plain string or a list of blocks; only text blocks count
    (tool_result blocks carry no user-authored feedback).
    """
    # Harness-injected user lines re-quote old tags and double-count them:
    # compaction summaries carry isCompactSummary, skill/command expansions
    # carry isMeta / <command-*> markup. Neither is user-authored feedback.
    if msg.get("isCompactSummary") or msg.get("isMeta"):
        return []

    inner = msg.get("message")
    if isinstance(inner, dict):
        role = inner.get("role", msg.get("type"))
        content = inner.get("content", "")
    else:
        role = msg.get("role", msg.get("type"))
        content = msg.get("content", "")

    if role != "user":
        return []
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
    return []


def scan_session(session_path: Path, pattern: re.Pattern, stats: dict | None = None) -> list[dict]:
    """Extract tagged messages from a session JSONL file.

    `stats` (optional) accumulates denominators: files/user_messages counts —
    a bare "0 found" is indistinguishable from a broken parser without them.
    """
    results = []
    if stats is not None:
        stats["files"] = stats.get("files", 0) + 1
    try:
        with open(session_path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                text = "\n".join(t for t in _message_texts(msg) if t)
                if text and stats is not None:
                    stats["user_messages"] = stats.get("user_messages", 0) + 1
                # Skill/command expansions quote tag docs verbatim — not feedback.
                if "<command-name>" in text or "Base directory for this skill" in text:
                    continue
                if text and pattern.search(text):
                    # Strip the tag itself, keep the rest as the feedback
                    feedback = pattern.sub(" ", text).strip()
                    results.append(
                        {
                            "session": session_path.stem,
                            "line": line_num,
                            "feedback": feedback[:500],
                        }
                    )
    except (OSError, UnicodeDecodeError):
        pass
    return results


def main():
    days = 7
    project_filter = None
    tag = "f"
    json_output = "--json" in sys.argv

    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    if "--project" in sys.argv:
        idx = sys.argv.index("--project")
        if idx + 1 < len(sys.argv):
            project_filter = sys.argv[idx + 1]

    if "--tag" in sys.argv:
        idx = sys.argv.index("--tag")
        if idx + 1 < len(sys.argv):
            tag = sys.argv[idx + 1].lstrip("#")

    pattern = tag_re(tag)
    stats: dict = {}
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_ts = cutoff.timestamp()

    all_feedback = []

    if not PROJECTS_DIR.exists():
        print("No projects directory found", file=sys.stderr)
        sys.exit(1)

    for proj_dir in PROJECTS_DIR.iterdir():
        if not proj_dir.is_dir():
            continue
        proj_name = extract_project_name(proj_dir.name)
        if project_filter and project_filter not in proj_name:
            continue

        for session_file in proj_dir.glob("*.jsonl"):
            if session_file.stat().st_mtime < cutoff_ts:
                continue

            results = scan_session(session_file, pattern, stats)
            for r in results:
                r["project"] = proj_name
                all_feedback.append(r)

    denom = (
        f"scanned {stats.get('files', 0)} files / "
        f"parsed {stats.get('user_messages', 0)} user messages"
    )

    if json_output:
        json.dump({"stats": stats, "entries": all_feedback}, sys.stdout, indent=2)
        return

    total = len(all_feedback)
    print(f"User feedback (#{tag}): {total} entries in last {days} days ({denom})\n")

    if not total:
        if not stats.get("user_messages"):
            print(f"WARNING: parsed 0 user messages — source/parser problem, not an absence of #{tag}.")
        else:
            print(f"No #{tag} feedback found yet.")
        return

    # Group by project
    by_project = defaultdict(list)
    for e in all_feedback:
        by_project[e["project"]].append(e)

    for proj in sorted(by_project):
        entries = by_project[proj]
        print(f"  {proj} ({len(entries)})")
        for e in entries:
            preview = e["feedback"][:120].replace("\n", " ")
            print(f"    {e['session'][:8]}:{e['line']} | {preview}")
        print()


if __name__ == "__main__":
    main()
