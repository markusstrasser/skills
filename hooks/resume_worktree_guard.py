"""Warn when SendMessage resumes a subagent whose isolated worktree the harness removed.

The Agent tool deletes an isolated worktree when its agent ends with no tracked change, even when the
agent was killed (a session limit, say). Its meta.json then records `worktreeCleanlyRemoved`. A
SendMessage resumes the agent with its context but no checkout, and it improvises: on 2026-10-25 the
genomics gencode-p2 agent worked in a `git archive` export with no git HEAD, so no test ran.
The fix is to name a replacement managed worktree in the message, or dispatch fresh.
"""

import json
from pathlib import Path


def removed_worktree_note(tool_input: dict, transcript_path: str) -> str:
    """Advisory note for a SendMessage to an agent whose worktree is gone, or "" when clean."""
    target = str(tool_input.get("to") or "").strip()
    if not target or not transcript_path:
        return ""
    subagents = Path(transcript_path).with_suffix("") / "subagents"
    if not subagents.is_dir():
        return ""
    for meta_path in subagents.glob("agent-*.meta.json"):
        agent_id = meta_path.name.removeprefix("agent-").removesuffix(".meta.json")
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue
        if target not in (meta.get("name"), agent_id):
            continue
        if str(meta.get("worktreeCleanlyRemoved")).lower() != "true":
            return ""
        if "/.claude/worktrees/" in str(tool_input.get("message") or ""):
            return ""
        return (
            f"SendMessage resumes '{target}', whose isolated worktree the harness removed "
            "(worktreeCleanlyRemoved in its meta.json). The agent will run with no git checkout. "
            "Create a managed worktree first (git worktree add <repo>/.claude/worktrees/<name> <base>) "
            "and name its path in the message, or dispatch a fresh agent."
        )
    return ""
