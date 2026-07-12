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

Claude: fires on the `Agent` (Task/subagent dispatch) tool. Codex: firing is
UNVERIFIED — do not assume this protects Codex sessions. Codex 0.137 source defines
a `spawn_agent`->`Agent` matcher alias, but an empirical probe (2026-06-07) could
NOT confirm any file-edit/Agent PreToolUse hook actually fires under `codex exec`
(only shell/Bash fired, non-deterministically); `--dangerously-bypass-approvals-
and-sandbox` disables hooks entirely, and hooks are gated by positional trust state
in config.toml that the parity sync doesn't generate. Full record:
agent-infra decisions/2026-06-02-codex-cli-project-parity.md §FINAL. Treat as a
Claude-effective advisory; Codex coverage is best-effort/unverified.

v1 signal: git log subjects in cwd (recent commits == "completed work"; this repo
family auto-commits per task, so finished work is in the log). agentlogs FTS is a
DEFERRED v2 enrichment — a single term matched 34k events in the 11GB index, so it
needs query-scoping (recent-run + task-message scope) before it's low-noise enough
for a synchronous pre-dispatch hook. Measure v1 first (Constitution Principle 3).
"""
# Gov-ID: hook:inventory-before-dispatch
# goal: stop research/exploration subagents from re-deriving already-completed
#       work on a topic (the twice-failed "inventory before dispatch" instruction)
# verifier: null  # not yet capability-testable; on generative backlog
# blast_radius: shared  # global ~/.claude/settings.json; Claude-effective.
#               Codex firing unverified (see decision doc §FINAL)
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


def _scan_knowledge_store(cwd: str, kw: list[str]) -> list[tuple[str, list[str]]]:
    """Match dispatch keywords against the CURATED knowledge store, not just git log.

    git log only sees the last 21 days; completed research lives in research/ memos
    (often months old) and the research-index. THIS is where rediscovery happens —
    a March memo is invisible to the commit scan by construction. Sources, cheap +
    high-signal: (1) research-index.md rows, (2) research/ and decisions/ filenames.
    """
    base = Path(cwd)
    strong = [k for k in kw if len(k) >= 6] or kw
    refs: list[tuple[str, list[str]]] = []

    idx = base / ".claude/rules/research-index.md"
    try:
        if idx.is_file():
            for line in idx.read_text(errors="ignore").splitlines():
                if "|" not in line:
                    continue
                ll = line.lower()
                hits = [k for k in strong if re.search(rf"\b{re.escape(k)}\b", ll)]
                if hits:
                    m = re.search(r"`([^`]+\.md)`", line)
                    refs.append((m.group(1) if m else line.strip()[:70], hits))
    except Exception:
        pass

    for sub in ("research", "decisions"):
        d = base / sub
        try:
            if d.is_dir():
                for f in d.glob("*.md"):
                    nl = f.name.lower()
                    hits = [k for k in strong if k in nl]
                    if hits:
                        refs.append((f"{sub}/{f.name}", hits))
        except Exception:
            pass

    seen: set[str] = set()
    out: list[tuple[str, list[str]]] = []
    for ref, hits in refs:
        if ref in seen:
            continue
        seen.add(ref)
        out.append((ref, hits))
        if len(out) >= 6:
            break
    return out


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
    # Check the structured isolation FIELD, not a substring of the prompt: a research
    # dispatch ABOUT worktrees (e.g. surveying worktree orchestrators) is not an
    # isolation dispatch and must NOT be skipped (this false-negative let a redundant
    # 245K-token fan-out through on 2026-06-13).
    if env.get("isolation") == "worktree" or ti.get("isolation") == "worktree":
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

    # --- Signal 1: curated knowledge store (research-index + memo filenames).
    # Highest precision and not time-bounded — a months-old memo is the #1 thing
    # rediscovered. Scanned first so it leads the advisory.
    memo_matches = _scan_knowledge_store(cwd, kw)

    # --- Signal 2: git log subjects in cwd (recent commits == completed work).
    matches: list[tuple[str, str, list[str]]] = []
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "log", "--no-merges", "-200", "--since=21.days",
             "--format=%h%x09%s"],
            capture_output=True, text=True, timeout=2.5,
        ).stdout
    except Exception:
        out = ""
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

    if not matches and not memo_matches:
        return

    matched_kw = sorted({k for _, _, ks in matches for k in ks}
                        | {k for _, ks in memo_matches for k in ks})
    parts = ["INVENTORY-BEFORE-DISPATCH (harness-supplied, advisory): this is a "
             f"research/exploration dispatch overlapping existing work on "
             f"[{', '.join(matched_kw)}]. READ these before spawning — narrow the "
             f"subagent to the genuine gap, point it at them, or skip."]
    if memo_matches:
        memo_lines = "\n".join(f"  {ref}" for ref, _ in memo_matches)
        parts.append(f"CURATED memo(s)/decision(s) already on this topic:\n{memo_lines}")
    if matches:
        commit_lines = "\n".join(f"  {h}  {subj}" for h, subj, _ in matches)
        parts.append(f"{len(matches)} recent commit(s) overlap:\n{commit_lines}")
    parts.append("(design provenance: ~/Projects/agent-infra/decisions/2026-06-07-state-externalization-lens.md)")
    ctx = "\n".join(parts)

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
