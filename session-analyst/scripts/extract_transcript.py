#!/usr/bin/env python3
"""Extract and compress Claude Code session transcripts for analysis.

Reads JSONL transcript files from ~/.claude/projects/, strips thinking blocks
and base64/binary content, outputs compressed markdown summaries suitable for
LLM analysis (~10-50KB per session instead of 5-50MB raw).

Usage:
    python extract_transcript.py <project> [--sessions N] [--output FILE]

Examples:
    python extract_transcript.py intel                    # Last 5 sessions
    python extract_transcript.py selve --sessions 3       # Last 3 sessions
    python extract_transcript.py meta --output /tmp/out.md
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


TRANSCRIPT_BASE = Path.home() / ".claude" / "projects"

# Map project short names to directory prefixes
PROJECT_MAP = {
    "intel": "-Users-alien-Projects-intel",
    "selve": "-Users-alien-Projects-selve",
    "meta": "-Users-alien-Projects-meta",
}

# Content patterns to strip
BASE64_PATTERN = re.compile(r"[A-Za-z0-9+/]{100,}={0,2}")
LONG_JSON_PATTERN = re.compile(r"\{[^}]{2000,}\}")


def find_transcripts(project: str, limit: int = 5) -> list[Path]:
    """Find the N most recent transcript files for a project."""
    dir_name = PROJECT_MAP.get(project)
    if not dir_name:
        # Try direct directory name
        dir_name = project

    project_dir = TRANSCRIPT_BASE / dir_name
    if not project_dir.exists():
        # Try fuzzy match
        for d in TRANSCRIPT_BASE.iterdir():
            if d.is_dir() and project.lower() in d.name.lower():
                project_dir = d
                break
        else:
            print(f"Error: No transcript directory found for '{project}'", file=sys.stderr)
            print(f"Available: {[d.name for d in TRANSCRIPT_BASE.iterdir() if d.is_dir()]}", file=sys.stderr)
            sys.exit(1)

    jsonl_files = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)

    # Filter to session directories (exclude files that are just IDs)
    # Actually they're all flat JSONL files
    return jsonl_files[:limit]


def strip_thinking(content_blocks: list) -> list:
    """Remove thinking blocks from content."""
    return [b for b in content_blocks if not (isinstance(b, dict) and b.get("type") == "thinking")]


def truncate_large_content(text: str, max_chars: int = 500) -> str:
    """Truncate text that's too long, likely base64 or verbose output."""
    if len(text) <= max_chars:
        return text
    # Strip base64 blobs
    text = BASE64_PATTERN.sub("[BASE64_CONTENT_STRIPPED]", text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [truncated, {len(text)} chars total]"


def extract_tool_summary(content_block: dict) -> str:
    """Summarize a tool_use block concisely."""
    name = content_block.get("name", "unknown_tool")
    inp = content_block.get("input", {})

    if name in ("Read", "Glob", "Grep"):
        path = inp.get("file_path") or inp.get("path") or inp.get("pattern", "")
        return f"`{name}({path})`"
    elif name in ("Write", "Edit"):
        path = inp.get("file_path", "")
        return f"`{name}({path})`"
    elif name == "Bash":
        cmd = inp.get("command", "")
        if len(cmd) > 120:
            cmd = cmd[:120] + "..."
        return f"`Bash: {cmd}`"
    elif name == "Agent":
        desc = inp.get("description", "")
        return f"`Agent({desc})`"
    elif name == "WebSearch":
        query = inp.get("query", "")
        return f"`WebSearch({query})`"
    elif name == "WebFetch":
        url = inp.get("url", "")
        return f"`WebFetch({url[:80]})`"
    else:
        # MCP tools, etc
        summary = json.dumps(inp, default=str)
        if len(summary) > 150:
            summary = summary[:150] + "..."
        return f"`{name}({summary})`"


def process_transcript(path: Path) -> dict:
    """Process a single JSONL transcript into structured data."""
    messages = []
    session_id = path.stem
    total_input_tokens = 0
    total_output_tokens = 0
    model = None
    start_time = None
    end_time = None

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")
            timestamp = obj.get("timestamp")

            if timestamp:
                if start_time is None:
                    start_time = timestamp
                end_time = timestamp

            if msg_type == "user":
                content = obj.get("message", {}).get("content", "")
                if isinstance(content, str):
                    text = truncate_large_content(content, 1000)
                elif isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(truncate_large_content(block.get("text", ""), 1000))
                        elif isinstance(block, dict) and block.get("type") == "tool_result":
                            parts.append("[tool_result]")
                    text = "\n".join(parts)
                else:
                    text = str(content)[:500]

                messages.append({"role": "user", "text": text})

            elif msg_type == "assistant":
                msg = obj.get("message", {})
                content = msg.get("content", [])
                usage = msg.get("usage", {})

                if not model:
                    model = msg.get("model")

                total_input_tokens += usage.get("input_tokens", 0)
                total_input_tokens += usage.get("cache_read_input_tokens", 0)
                total_input_tokens += usage.get("cache_creation_input_tokens", 0)
                total_output_tokens += usage.get("output_tokens", 0)

                # Process content blocks (strip thinking)
                filtered = strip_thinking(content) if isinstance(content, list) else []
                parts = []
                tools_used = []

                for block in filtered:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        if text.strip():
                            parts.append(truncate_large_content(text, 800))
                    elif block.get("type") == "tool_use":
                        tools_used.append(extract_tool_summary(block))

                entry = {"role": "assistant", "text": "\n".join(parts)}
                if tools_used:
                    entry["tools"] = tools_used
                messages.append(entry)

    return {
        "session_id": session_id,
        "model": model,
        "start_time": start_time,
        "end_time": end_time,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "message_count": len(messages),
        "messages": messages,
    }


def format_markdown(sessions: list[dict], project: str) -> str:
    """Format processed sessions as compressed markdown for LLM analysis."""
    lines = []
    lines.append(f"# Session Transcripts: {project}")
    lines.append(f"Extracted: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"Sessions: {len(sessions)}")
    lines.append("")

    # UUID manifest — anchoring block for downstream LLM analysis.
    # Gemini 3.1 Pro fabricates session IDs without this (2 confirmed incidents).
    lines.append("## VALID SESSION IDS — Use ONLY these. Never fabricate IDs.")
    lines.append("| Prefix | Full UUID |")
    lines.append("|--------|-----------|")
    for sess in sessions:
        lines.append(f"| {sess['session_id'][:8]} | {sess['session_id']} |")
    lines.append("")

    for sess in sessions:
        lines.append(f"## Session {sess['session_id'][:8]}...")
        lines.append(f"- Model: {sess['model']}")
        lines.append(f"- Time: {sess.get('start_time', '?')} → {sess.get('end_time', '?')}")
        lines.append(f"- Tokens: {sess['total_input_tokens']:,} in / {sess['total_output_tokens']:,} out")
        lines.append(f"- Messages: {sess['message_count']}")
        lines.append("")

        for msg in sess["messages"]:
            role = msg["role"].upper()
            text = msg.get("text", "").strip()
            tools = msg.get("tools", [])

            if text:
                lines.append(f"**{role}:** {text}")
            if tools:
                lines.append(f"**TOOLS:** {' → '.join(tools)}")
            if text or tools:
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Extract Claude Code session transcripts")
    parser.add_argument("project", help="Project name (intel, selve, meta) or directory prefix")
    parser.add_argument("--sessions", "-n", type=int, default=5, help="Number of recent sessions (default: 5)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    args = parser.parse_args()

    transcripts = find_transcripts(args.project, args.sessions)
    if not transcripts:
        print(f"No transcripts found for '{args.project}'", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(transcripts)} transcripts for '{args.project}'...", file=sys.stderr)

    sessions = []
    for t in transcripts:
        size_mb = t.stat().st_size / (1024 * 1024)
        print(f"  {t.name[:12]}... ({size_mb:.1f} MB)", file=sys.stderr)
        sessions.append(process_transcript(t))

    markdown = format_markdown(sessions, args.project)

    if args.output:
        Path(args.output).write_text(markdown)
        print(f"Written to {args.output} ({len(markdown):,} chars)", file=sys.stderr)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
