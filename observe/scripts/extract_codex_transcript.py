#!/usr/bin/env python3
"""Extract and compress Codex CLI session transcripts for analysis.

Reads session data from ~/.codex/state_5.sqlite (thread metadata) and JSONL
rollout files (conversation content). Outputs compressed markdown summaries
matching the format of extract_transcript.py for Claude Code sessions.

Usage:
    python3 extract_codex_transcript.py <project> [--sessions N] [--output FILE]

Examples:
    python3 extract_codex_transcript.py research                # Last 5 sessions
    python3 extract_codex_transcript.py selve --sessions 3      # Last 3 sessions
    python3 extract_codex_transcript.py intel --output /tmp/codex.md
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

CODEX_DB = Path.home() / ".codex" / "state_5.sqlite"
BASE64_PATTERN = re.compile(r"[A-Za-z0-9+/]{100,}={0,2}")


def find_sessions(project: str, limit: int = 5) -> list[dict]:
    """Find the N most recent Codex sessions for a project via SQLite."""
    if not CODEX_DB.exists():
        print(f"Error: Codex database not found at {CODEX_DB}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(f"file:{CODEX_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    # Try exact match on cwd ending, then fuzzy
    rows = con.execute(
        "SELECT * FROM threads WHERE cwd LIKE ? ORDER BY updated_at DESC LIMIT ?",
        (f"%/{project}", limit),
    ).fetchall()

    if not rows:
        # Fuzzy: any cwd containing the project name
        rows = con.execute(
            "SELECT * FROM threads WHERE cwd LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (f"%{project}%", limit),
        ).fetchall()

    if not rows:
        # Show available projects
        cwds = con.execute(
            "SELECT DISTINCT cwd FROM threads ORDER BY cwd"
        ).fetchall()
        print(f"Error: No sessions found for '{project}'", file=sys.stderr)
        print(f"Available cwds: {[r['cwd'] for r in cwds]}", file=sys.stderr)
        con.close()
        sys.exit(1)

    result = [dict(r) for r in rows]
    con.close()
    return result


def truncate(text: str, max_chars: int = 500) -> str:
    """Truncate text, stripping base64 blobs."""
    if len(text) <= max_chars:
        return text
    text = BASE64_PATTERN.sub("[BASE64_STRIPPED]", text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [truncated, {len(text)} chars total]"


def extract_tool_summary(item: dict) -> str:
    """Summarize a function_call item concisely."""
    name = item.get("name", "unknown")
    raw_args = item.get("arguments", "{}")
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except (json.JSONDecodeError, TypeError):
        args = {}

    if name == "exec_command":
        cmd = args.get("cmd", "")
        if len(cmd) > 120:
            cmd = cmd[:120] + "..."
        return f"`Bash: {cmd}`"
    elif name == "apply_patch":
        # Extract file path from patch content
        patch = args.get("patch", "")
        match = re.search(r"--- (.+)", patch)
        path = match.group(1) if match else "?"
        return f"`Edit({path})`"
    elif name in ("read_file", "view_image"):
        path = args.get("file_path", args.get("path", "?"))
        return f"`Read({path})`"
    elif name == "write_stdin":
        sid = args.get("session_id", "?")
        return f"`write_stdin(session={sid})`"
    elif name == "update_plan":
        expl = args.get("explanation", "")[:80]
        return f"`update_plan({expl})`"
    elif name.startswith("mcp__"):
        summary = json.dumps(args, default=str)
        if len(summary) > 150:
            summary = summary[:150] + "..."
        return f"`{name}({summary})`"
    else:
        summary = json.dumps(args, default=str)
        if len(summary) > 150:
            summary = summary[:150] + "..."
        return f"`{name}({summary})`"


def extract_text_blocks(content: list, max_chars: int = 800) -> str:
    """Extract text from input_text/output_text content blocks."""
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type", "")
        if btype in ("input_text", "output_text"):
            text = block.get("text", "")
            if text.strip():
                parts.append(truncate(text.strip(), max_chars))
    return "\n".join(parts)


def process_rollout(thread: dict) -> dict:
    """Process a single Codex rollout JSONL into structured data."""
    rollout_path = Path(thread["rollout_path"])
    session_id = thread["id"]
    messages = []
    total_input_tokens = 0
    total_output_tokens = 0
    model = None
    start_time = None
    end_time = None

    if not rollout_path.exists():
        return {
            "session_id": session_id,
            "model": thread.get("model_provider", "?"),
            "title": thread.get("title", ""),
            "git_branch": thread.get("git_branch"),
            "git_sha": thread.get("git_sha"),
            "start_time": None,
            "end_time": None,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "message_count": 0,
            "messages": [],
        }

    with open(rollout_path) as f:
        # Accumulate tool calls between assistant messages
        pending_tools = []

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
            payload = obj.get("payload", {})

            if timestamp:
                if start_time is None:
                    start_time = timestamp
                end_time = timestamp

            if msg_type == "turn_context":
                if not model:
                    model = payload.get("model")

            elif msg_type == "event_msg":
                etype = payload.get("type", "")
                if etype == "token_count":
                    # total_token_usage is cumulative — take the last one
                    info = payload.get("info", {})
                    usage = info.get("total_token_usage", info)
                    total_input_tokens = usage.get("input_tokens", total_input_tokens)
                    total_output_tokens = usage.get("output_tokens", total_output_tokens)

            elif msg_type == "response_item":
                item = payload.get("item", payload)
                itype = item.get("type", "")
                role = item.get("role", "")

                if itype == "message":
                    content = item.get("content", [])
                    if not isinstance(content, list):
                        continue

                    if role == "developer":
                        # System prompt — skip
                        continue
                    elif role == "user":
                        text = extract_text_blocks(content, 1000)
                        # Skip AGENTS.md / environment context injections
                        if text and (
                            text.startswith("# AGENTS.md")
                            or text.startswith("<environment_context>")
                        ):
                            continue
                        if text:
                            # Flush any pending tools before user message
                            if pending_tools:
                                messages.append({
                                    "role": "assistant",
                                    "text": "",
                                    "tools": pending_tools,
                                })
                                pending_tools = []
                            messages.append({"role": "user", "text": text})
                    elif role == "assistant":
                        text = extract_text_blocks(content, 800)
                        if text or pending_tools:
                            entry = {"role": "assistant", "text": text}
                            if pending_tools:
                                entry["tools"] = pending_tools
                                pending_tools = []
                            messages.append(entry)

                elif itype == "function_call":
                    pending_tools.append(extract_tool_summary(item))

                elif itype == "function_call_output":
                    # Skip verbose tool output
                    pass

                elif itype == "reasoning":
                    # Opaque reasoning — skip
                    pass

        # Flush remaining tools
        if pending_tools:
            messages.append({
                "role": "assistant",
                "text": "",
                "tools": pending_tools,
            })

    return {
        "session_id": session_id,
        "model": model or thread.get("model_provider", "?"),
        "provider": thread.get("model_provider", "?"),
        "title": thread.get("title", ""),
        "git_branch": thread.get("git_branch"),
        "git_sha": thread.get("git_sha"),
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
    lines.append(f"# Session Transcripts: {project} (Codex)")
    lines.append(
        f"Extracted: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    lines.append(f"Sessions: {len(sessions)}")
    lines.append("")

    for sess in sessions:
        lines.append(f"## Session {sess['session_id'][:8]}...")
        model_str = sess["model"] or "?"
        provider = sess.get("provider", "")
        if provider and provider != model_str:
            model_str = f"{model_str} (via {provider})"
        lines.append(f"- Model: {model_str}")
        lines.append(
            f"- Time: {sess.get('start_time', '?')} → {sess.get('end_time', '?')}"
        )
        lines.append(
            f"- Tokens: {sess['total_input_tokens']:,} in / {sess['total_output_tokens']:,} out"
        )
        lines.append(f"- Messages: {sess['message_count']}")
        if sess.get("title"):
            title = sess["title"]
            if len(title) > 120:
                title = title[:120] + "..."
            lines.append(f"- Title: {title}")
        if sess.get("git_branch"):
            sha = (sess.get("git_sha") or "")[:8]
            lines.append(f"- Git: {sess['git_branch']}@{sha}")
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
    parser = argparse.ArgumentParser(
        description="Extract Codex CLI session transcripts"
    )
    parser.add_argument(
        "project",
        help="Project name (matches cwd) or path fragment",
    )
    parser.add_argument(
        "--sessions",
        "-n",
        type=int,
        default=5,
        help="Number of recent sessions (default: 5)",
    )
    parser.add_argument(
        "--output", "-o", help="Output file (default: stdout)"
    )
    args = parser.parse_args()

    threads = find_sessions(args.project, args.sessions)
    print(
        f"Processing {len(threads)} Codex sessions for '{args.project}'...",
        file=sys.stderr,
    )

    sessions = []
    for t in threads:
        rollout = Path(t["rollout_path"])
        size_kb = rollout.stat().st_size / 1024 if rollout.exists() else 0
        print(
            f"  {t['id'][:12]}... ({size_kb:.0f} KB) {t.get('title', '')[:60]}",
            file=sys.stderr,
        )
        sessions.append(process_rollout(t))

    markdown = format_markdown(sessions, args.project)

    if args.output:
        Path(args.output).write_text(markdown)
        print(
            f"Written to {args.output} ({len(markdown):,} chars)",
            file=sys.stderr,
        )
    else:
        print(markdown)


if __name__ == "__main__":
    main()
