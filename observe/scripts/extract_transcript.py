#!/usr/bin/env python3
"""Extract and compress Claude Code session transcripts for analysis.

Reads JSONL transcript files from ~/.claude/projects/, strips thinking blocks
and base64/binary content, outputs compressed markdown summaries suitable for
LLM analysis (~10-50KB per session instead of 5-50MB raw).

--full mode: Higher-fidelity extraction for session-analyst dispatch to Gemini.
Raises truncation limits, preserves tool call args for key tools, keeps tool
results for failures, and preserves user correction sequences verbatim.
Paper evidence: raw traces >> summaries (+15pp, Lee et al. 2026 arXiv:2603.28052).

Usage:
    python extract_transcript.py <project> [--sessions N] [--output FILE] [--full]

Examples:
    python extract_transcript.py intel                    # Last 5 sessions
    python extract_transcript.py selve --sessions 3       # Last 3 sessions
    python extract_transcript.py meta --full -o /tmp/out.md  # Full fidelity
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
    "genomics": "-Users-alien-Projects-genomics",
}

# Content patterns to strip
BASE64_PATTERN = re.compile(r"[A-Za-z0-9+/]{100,}={0,2}")

# Module-level fidelity flag (set by --full)
FULL_MODE = False

# Truncation limits by mode
def _user_limit():    return 8000 if FULL_MODE else 1000
def _asst_limit():    return 4000 if FULL_MODE else 800
def _tool_cmd_limit(): return 500 if FULL_MODE else 120
def _tool_arg_limit(): return 800 if FULL_MODE else 150


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
    """Summarize a tool_use block. In --full mode, preserves more args."""
    name = content_block.get("name", "unknown_tool")
    inp = content_block.get("input", {})

    if name in ("Read", "Glob", "Grep"):
        path = inp.get("file_path") or inp.get("path") or inp.get("pattern", "")
        extra = ""
        if FULL_MODE and name == "Grep":
            extra = f", pattern={inp.get('pattern', '')}"
        return f"`{name}({path}{extra})`"
    elif name in ("Write", "Edit"):
        path = inp.get("file_path", "")
        if FULL_MODE:
            # In full mode, include old/new strings for Edit (diagnostic for corrections)
            if name == "Edit":
                old = inp.get("old_string", "")[:200]
                new = inp.get("new_string", "")[:200]
                return f"`Edit({path})`\n  old: `{old}`\n  new: `{new}`"
            elif name == "Write":
                content = inp.get("content", "")
                preview = content[:300] if content else ""
                return f"`Write({path})` [{len(content)} chars]\n  preview: `{preview}`"
        return f"`{name}({path})`"
    elif name == "Bash":
        cmd = inp.get("command", "")
        limit = _tool_cmd_limit()
        if len(cmd) > limit:
            cmd = cmd[:limit] + "..."
        return f"`Bash: {cmd}`"
    elif name == "Agent":
        desc = inp.get("description", "")
        if FULL_MODE:
            prompt = inp.get("prompt", "")[:300]
            return f"`Agent({desc})`\n  prompt: `{prompt}`"
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
        limit = _tool_arg_limit()
        if len(summary) > limit:
            summary = summary[:limit] + "..."
        return f"`{name}({summary})`"


def extract_tool_result(obj: dict) -> str | None:
    """Extract tool result text from a user message containing tool_result blocks.
    In --full mode, preserves error results for diagnostic value."""
    if not FULL_MODE:
        return None
    content = obj.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return None
    results = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        is_error = block.get("is_error", False)
        result_content = block.get("content", "")
        if isinstance(result_content, list):
            texts = [b.get("text", "") for b in result_content if isinstance(b, dict) and b.get("type") == "text"]
            result_content = "\n".join(texts)
        if is_error and result_content:
            results.append(f"[TOOL ERROR] {truncate_large_content(result_content, 2000)}")
        elif result_content and len(result_content) > 50:
            # In full mode, keep substantial results (truncated)
            results.append(f"[TOOL RESULT] {truncate_large_content(result_content, 1000)}")
    return "\n".join(results) if results else None


def process_transcript(path: Path) -> dict:
    """Process a single JSONL transcript into structured data."""
    messages = []
    session_id = path.stem
    total_input_tokens = 0
    total_output_tokens = 0
    model = None
    start_time = None
    end_time = None
    last_role = None  # Track for correction detection

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
                ulimit = _user_limit()
                if isinstance(content, str):
                    text = truncate_large_content(content, ulimit)
                elif isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(truncate_large_content(block.get("text", ""), ulimit))
                        elif isinstance(block, dict) and block.get("type") == "tool_result":
                            parts.append("[tool_result]")
                    text = "\n".join(parts)
                else:
                    text = str(content)[:500]

                entry = {"role": "user", "text": text}

                # In full mode, flag likely corrections (user message after assistant tool use)
                if FULL_MODE and last_role == "assistant":
                    # Check if this looks like a correction (short, directive)
                    stripped = text.strip()
                    if stripped and len(stripped) < 500 and not stripped.startswith("<system-reminder>"):
                        entry["likely_correction"] = True

                # In full mode, extract tool error results
                tool_result = extract_tool_result(obj)
                if tool_result:
                    entry["tool_results"] = tool_result

                messages.append(entry)
                last_role = "user"

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
                            parts.append(truncate_large_content(text, _asst_limit()))
                    elif block.get("type") == "tool_use":
                        tools_used.append(extract_tool_summary(block))

                entry = {"role": "assistant", "text": "\n".join(parts)}
                if tools_used:
                    entry["tools"] = tools_used
                messages.append(entry)
                last_role = "assistant"

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
    if FULL_MODE:
        lines.append("Mode: FULL FIDELITY (--full)")
    lines.append("")

    # UUID manifest — anchoring block for downstream LLM analysis.
    # Gemini 3.1 Pro fabricates session IDs without this (2 confirmed incidents).
    # The "Source" column distinguishes Claude Code from Codex when both transcript
    # sources are concatenated into the same Gemini dispatch.
    lines.append("## VALID SESSION IDS (Claude Code) — Use ONLY these. Never fabricate IDs.")
    lines.append("| Prefix | Full UUID | Source |")
    lines.append("|--------|-----------|--------|")
    for sess in sessions:
        lines.append(f"| {sess['session_id'][:8]} | {sess['session_id']} | claude-code |")
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
            tool_results = msg.get("tool_results", "")
            is_correction = msg.get("likely_correction", False)

            prefix = f"**{role}"
            if is_correction:
                prefix += " [CORRECTION]"
            prefix += ":**"

            if text:
                lines.append(f"{prefix} {text}")
            if tools:
                lines.append(f"**TOOLS:** {' → '.join(tools)}")
            if tool_results:
                lines.append(tool_results)
            if text or tools:
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    global FULL_MODE
    parser = argparse.ArgumentParser(description="Extract Claude Code session transcripts")
    parser.add_argument("project", help="Project name (intel, selve, meta) or directory prefix")
    parser.add_argument("--sessions", "-n", type=int, default=5, help="Number of recent sessions (default: 5)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--full", action="store_true",
                        help="Full fidelity mode: higher truncation limits, preserve tool args and corrections")
    args = parser.parse_args()

    FULL_MODE = args.full

    transcripts = find_transcripts(args.project, args.sessions)
    if not transcripts:
        print(f"No transcripts found for '{args.project}'", file=sys.stderr)
        sys.exit(1)

    mode_label = " (FULL)" if FULL_MODE else ""
    print(f"Processing {len(transcripts)} transcripts for '{args.project}'{mode_label}...", file=sys.stderr)

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
