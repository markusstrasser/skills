#!/usr/bin/env python3
"""pretool-inventory-dispatch.py — advisory inventory-before-dispatch check.

PreToolUse:Agent hook. Implements the state-externalization principle
(decisions/2026-06-07-state-externalization-lens.md, arXiv:2606.02373): the
HARNESS supplies the "what's already been done on this topic" bookkeeping so the
dispatching policy makes only the semantic keep/skip/narrow decision — instead of
being *told via instruction* to "inventory before dispatch", which failed twice
as a pure instruction (~9M tokens of subagents rediscovering completed work, per
the global subagent_usage rule). This is the prune_chunks pattern: policy judges,
harness supplies the state.

Contract (Claude Code 2.1.x, see lint_hook_input_contract.py):
  - input arrives on stdin as the full envelope; tool fields under `.tool_input`;
    `cwd` is top-level.
  - Advisory ONLY: emits hookSpecificOutput.additionalContext, never blocks.
  - Fails OPEN: any error -> exit 0 with no output.

v1 signal: git log subjects in cwd (recent commits == "completed work"; this repo
family auto-commits per task, so finished work is in the log). agentlogs FTS is a
DEFERRED v2 enrichment — a single term matched 34k events in the 11GB index, so it
needs query-scoping (recent-run + task-message scope) before it's low-noise enough
for a synchronous pre-dispatch hook. Measure v1 first (Constitution Principle 3).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Generic scaffolding/verb tokens that carry no topic signal. Deliberately does
# NOT include domain nouns (harness, corpus, attestation, externalize, inventory,
# dispatch, ...) — those ARE the topic and must survive to match commits.
STOP = {
    "research", "researcher", "investigate", "explore", "exploration", "survey",
    "agent", "agents", "subagent", "subagents", "dispatch",  # 'dispatch' generic here
    "session", "sessions", "claude", "codex", "gemini", "opus", "sonnet",
    "files", "file", "code", "codebase", "tests", "test", "data", "update",
    "updates", "should", "could", "would", "about", "there", "their", "which",
    "where", "while", "these", "those", "before", "after", "across", "using",
    "into", "from", "with", "that", "this", "what", "when", "then", "than",
    "find", "finding", "search", "searching", "look", "looking", "check",
    "review", "reviewing", "write", "writing", "wrote", "report", "reports",
    "memo", "memos", "paper", "papers", "result", "results", "thing", "things",
    "finding", "findings", "settings", "marker", "markers", "maintenance",
    "make", "build", "wire", "wired", "scope", "scoped", "task", "tasks",
    "please", "needs", "need", "want", "given", "above", "below", "current",
    "recent", "recently", "everything", "anything", "something",
    # Generic-but-long nouns that are pervasive in an agent-infra repo and so
    # carry no discriminating topic signal (they match half the commit log).
    "architecture", "architectural", "infrastructure", "implementation",
    "documentation", "framework", "frameworks", "mechanism", "mechanisms",
    "approach", "approaches", "system", "systems", "analysis", "analyze",
    "validate", "validation", "structure", "structures", "generic", "general",
    "design", "designs", "pattern", "patterns", "feature", "features",
    "improve", "improvement", "improvements", "change", "changes",
}


def _emit(ctx: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": ctx,
        }
    }))


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        return
    env = json.loads(raw)
    ti = env.get("tool_input", {}) or {}
    desc = ti.get("description") or ""
    prompt = ti.get("prompt") or ""
    stype = ti.get("subagent_type") or ""
    cwd = env.get("cwd") or "."

    # --- Gate to the rediscovery failure class: research/exploration dispatches.
    # Worktree (implementation continuation) is EXPECTED to overlap recent commits -> skip.
    if "worktree" in raw:
        return
    text = f"{desc}\n{prompt[:1000]}"
    research_intent = bool(re.search(
        r"\b(research|investigat|explor|survey|audit|literature|find (all|every|out)|"
        r"search for|look (through|into)|what(?:'s| is) known|prior art|"
        r"state of the art|discover|map out|scan (the |all ))\b",
        text, re.I,
    ))
    eligible_types = {"researcher", "Explore"}
    if stype in eligible_types:
        pass  # always eligible
    elif research_intent:
        pass  # any type with explicit research intent
    else:
        return

    # --- Distinctive topic keywords from the dispatch text.
    seen: set[str] = set()
    kw: list[str] = []
    for t in re.findall(r"[a-z][a-z0-9_-]{4,}", text.lower()):
        if t in STOP or t in seen:
            continue
        seen.add(t)
        kw.append(t)
    kw = sorted(kw, key=len, reverse=True)[:8]  # longer == more distinctive
    if not kw:
        return

    # --- git log subjects in cwd (recent commits == completed work).
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "log", "--no-merges", "-200", "--since=21.days",
             "--format=%h%x09%s"],
            capture_output=True, text=True, timeout=2.5,
        ).stdout
    except Exception:
        return

    matches: list[tuple[str, str, list[str]]] = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        h, subj = line.split("\t", 1)
        sl = subj.lower()
        # A distinctive (>=6 char) keyword whole-word hit, OR >=2 shorter hits.
        strong = [k for k in kw if len(k) >= 6 and re.search(rf"\b{re.escape(k)}\b", sl)]
        any_hits = [k for k in kw if re.search(rf"\b{re.escape(k)}\b", sl)]
        if strong or len(any_hits) >= 2:
            matches.append((h, subj.strip(), strong or any_hits))
        if len(matches) >= 6:
            break
    if not matches:
        return

    matched_kw = sorted({k for _, _, ks in matches for k in ks})
    commit_lines = "\n".join(f"  {h}  {subj}" for h, subj, _ in matches)
    ctx = (
        "INVENTORY-BEFORE-DISPATCH (harness-supplied, advisory): this is a "
        f"research/exploration dispatch and {len(matches)} recent commit(s) in this "
        f"repo overlap its topic [{', '.join(matched_kw)}]:\n{commit_lines}\n"
        "Confirm the subagent isn't re-deriving finished work before spawning — narrow "
        "its scope to the gap, point it at these commits, or skip. "
        "(decisions/2026-06-07-state-externalization-lens.md)"
    )

    # Best-effort trigger log for ROI measurement (Constitution Principle 3).
    try:
        subprocess.run(
            [str(Path.home() / "Projects/skills/hooks/hook-trigger-log.sh"),
             "inventory-dispatch", "warn",
             f"kw={','.join(matched_kw)} n={len(matches)}"],
            timeout=1.0, capture_output=True,
        )
    except Exception:
        pass

    _emit(ctx)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
