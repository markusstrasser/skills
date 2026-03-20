#!/usr/bin/env python3
"""Governance state logger — path-aware tool usage tracking.

PostToolUse hook. Maintains per-session state vector tracking what categories
of data have been accessed and what external actions have been taken.
Flag-only: logs to JSONL for retrospective path analysis, never blocks.

Motivation: Runtime Governance (arxiv:2603.16586) — our hooks are access-control
(degenerate case ignoring path history). This logger enables future path-dependent
policies by tracking the state an agent accumulates during a session.

AgentDrift (arxiv:2603.12564) — agents never question tool data reliability.
This logger measures tool-trust patterns: how many tools called, how many
cross-referenced, what data categories accessed.
"""

import json
import os
import time
from pathlib import Path

LOG_PATH = Path("~/.claude/governance-state.jsonl").expanduser()
STATE_DIR = Path("~/.claude/governance-sessions").expanduser()

# Tool categories for governance tracking
TOOL_CATEGORIES = {
    # Financial data — highest risk per AgentDrift
    "financial": [
        "mcp__yahoo", "mcp__alpha", "mcp__polygon", "mcp__fmp",
        "mcp__sec", "mcp__edgar",
    ],
    # Research/search — medium risk (hallucinated citations)
    "research": [
        "mcp__research__search_papers", "mcp__research__fetch_paper",
        "mcp__research__read_paper", "mcp__research__ask_papers",
        "mcp__research__verify_claim", "mcp__research__prepare_evidence",
        "mcp__scite__search_literature",
    ],
    "websearch": [
        "mcp__exa__web_search_exa", "mcp__exa__web_search_advanced_exa",
        "mcp__brave-search__brave_web_search", "mcp__brave-search__brave_news_search",
        "mcp__perplexity__perplexity_search", "mcp__perplexity__perplexity_ask",
        "mcp__perplexity__perplexity_reason", "mcp__perplexity__perplexity_research",
        "mcp__firecrawl__firecrawl_scrape", "mcp__firecrawl__firecrawl_search",
        "WebSearch", "WebFetch",
    ],
    # External actions — tracked for path-dependent policies
    "external": [
        "mcp__claude_ai_Gmail__gmail_create_draft",
        "mcp__claude_ai_Gmail__gmail_send",
    ],
    # Code execution
    "execution": ["Bash"],
    # File modification
    "write": ["Write", "Edit"],
    # Browser automation
    "browser": [
        "mcp__claude-in-chrome__navigate", "mcp__claude-in-chrome__form_input",
        "mcp__claude-in-chrome__javascript_tool",
    ],
}


def categorize_tool(tool_name: str) -> list[str]:
    """Return all matching categories for a tool."""
    cats = []
    for cat, tools in TOOL_CATEGORIES.items():
        if any(tool_name.startswith(t) for t in tools):
            cats.append(cat)
    if not cats:
        cats = ["other"]
    return cats


def get_session_id() -> str:
    """Read session ID from file or generate fallback."""
    sid_file = Path(".claude/current-session-id")
    if sid_file.exists():
        return sid_file.read_text().strip()[:8]
    return f"unknown-{int(time.time()) % 100000}"


def load_session_state(session_id: str) -> dict:
    """Load or initialize per-session governance state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = STATE_DIR / f"{session_id}.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "session_id": session_id,
        "started": time.time(),
        "step_count": 0,
        "categories_accessed": [],
        "tool_names": [],
        "data_sensitivity": 0,  # 0=none, 1=public, 2=internal, 3=sensitive
        "external_actions": 0,
        "write_actions": 0,
    }


def save_session_state(session_id: str, state: dict):
    """Persist session state."""
    state_file = STATE_DIR / f"{session_id}.json"
    state_file.write_text(json.dumps(state, indent=2))


def main():
    t0 = time.monotonic()

    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    if not tool_name:
        return

    session_id = get_session_id()
    state = load_session_state(session_id)

    # Update state vector
    categories = categorize_tool(tool_name)
    state["step_count"] += 1
    for cat in categories:
        if cat not in state["categories_accessed"]:
            state["categories_accessed"].append(cat)
    if tool_name not in state["tool_names"]:
        state["tool_names"].append(tool_name)

    # Track sensitivity level
    if "financial" in categories:
        state["data_sensitivity"] = max(state["data_sensitivity"], 3)
    elif "research" in categories or "websearch" in categories:
        state["data_sensitivity"] = max(state["data_sensitivity"], 1)

    # Track action types
    if "external" in categories:
        state["external_actions"] += 1
    if "write" in categories:
        state["write_actions"] += 1

    save_session_state(session_id, state)

    elapsed_ms = (time.monotonic() - t0) * 1000

    # Append event to global log
    event = {
        "ts": time.time(),
        "session_id": session_id,
        "tool": tool_name,
        "categories": categories,
        "elapsed_ms": round(elapsed_ms, 1),
        "state_snapshot": {
            "step": state["step_count"],
            "sensitivity": state["data_sensitivity"],
            "cats": state["categories_accessed"],
            "external": state["external_actions"],
        },
    }

    try:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass  # Fail open — never block on logging failure


if __name__ == "__main__":
    main()
