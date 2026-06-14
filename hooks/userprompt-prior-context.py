#!/usr/bin/env python3
"""userprompt-prior-context.py — front-load prior context on propose/diagnose prompts.

UserPromptSubmit hook. The MAIN-LOOP analog of pretool-inventory-dispatch.py:
that hook front-loads "what's already been done on this topic" when a *subagent*
is dispatched; this one front-loads it when the *user's own prompt* is a
propose / diagnose / status-of-X request whose keywords overlap existing work —
so the main loop reads prior discussion BEFORE it starts proposing, instead of
the human having to interject "check the git logs first."

Why a hook, not an instruction: "check prior context before proposing" failed as
a pure CLAUDE.md instruction (Principle 1 — instructions are ~0% reliable for
this). The blindspot-miner (agent-infra scripts/blindspot_miner.py) measured this
as the #1 recurring loop-miss cluster the human has to catch — across genomics,
intel, hutter, agent-infra. Representative flags:
  genomics/31f0584d "check the git logs about these things we did ... see if we
                     discussed stuff before"
  agent-infra/1098feff "Has somebody done /research into newer ideas?"
  hutter/f94e5339      "how did you forget that or not think of that"
  intel/8bf2bd58       "any updates to graph, docs tools?"
This is the harness supplying recoverable bookkeeping so the policy makes only
the semantic keep/build/supersede decision (state-externalization lens,
decisions/2026-06-07-state-externalization-lens.md, arXiv:2606.02373).

Contract (Claude Code 2.1.x):
  - UserPromptSubmit envelope on stdin: `.user_message` (prompt text), `.cwd`,
    `.session_id`. (Field names verified against the sibling working hook
    userprompt-context-warn.sh.)
  - Advisory ONLY: emits hookSpecificOutput.additionalContext, never blocks.
  - Fails OPEN: any error -> exit 0, no output.
  - Cheap by construction: the intent gate (a regex) runs first; the git-log /
    file scans run ONLY when intent is present, so non-propose prompts (the
    majority) pay one regex and exit. git log is capped at 2.5s.
  - Session-deduped: a given reference-set is surfaced at most once per session
    (a focused multi-turn session must not re-inject the same prior context every
    turn — that is how an advisory hook trains itself to be ignored).

Self-contained on purpose: hooks must be independently fail-open, so the STOP set
and scan logic are NOT shared with pretool-inventory-dispatch.py (a bug in a
shared module would take down both). The surfaces also legitimately differ —
free-form user prose here vs a structured dispatch prompt there. If the keyword
lists measurably drift in a way that matters, extract then (Principle 3).
"""
# Gov-ID: hook:prior-context-front-load
# goal: stop the main loop from proposing/diagnosing without reading prior
#       discussion (git log, research memos, ideas.md) — the #1 blindspot-miner
#       cluster (human has to say "check the git logs first")
# verifier: null  # semantic (did the agent build on the surfaced context?) — on
#                 # generative backlog; ROI tracked via hook-trigger-log
# blast_radius: shared  # global ~/.claude/settings.json UserPromptSubmit; fires
#               # every prompt in every project — intent-gated + fail-open
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# Generic scaffolding / verb tokens that carry no topic signal. Mirrors the
# sibling inventory-dispatch STOP set; intentionally keeps domain nouns OUT of
# STOP (they ARE the topic that must survive to match prior work).
STOP = {
    "research", "researcher", "investigate", "explore", "exploration", "survey",
    "agent", "agents", "subagent", "subagents", "dispatch", "session", "sessions",
    "claude", "codex", "gemini", "opus", "sonnet", "files", "file", "code",
    "codebase", "tests", "test", "data", "update", "updates", "should", "could",
    "would", "about", "there", "their", "which", "where", "while", "these",
    "those", "before", "after", "across", "using", "into", "from", "with", "that",
    "this", "what", "when", "then", "than", "find", "finding", "findings",
    "search", "searching", "look", "looking", "check", "review", "reviewing",
    "write", "writing", "wrote", "report", "reports", "memo", "memos", "paper",
    "papers", "result", "results", "thing", "things", "settings", "marker",
    "markers", "maintenance", "make", "build", "wire", "wired", "scope", "scoped",
    "task", "tasks", "please", "needs", "need", "want", "given", "above", "below",
    "current", "recent", "recently", "everything", "anything", "something",
    "architecture", "architectural", "infrastructure", "implementation",
    "documentation", "framework", "frameworks", "mechanism", "mechanisms",
    "approach", "approaches", "system", "systems", "analysis", "analyze",
    "validate", "validation", "structure", "structures", "generic", "general",
    "design", "designs", "pattern", "patterns", "feature", "features", "improve",
    "improvement", "improvements", "change", "changes", "maybe", "really",
    "actually", "already", "going", "instead", "better", "newer", "stuff",
    "whatever", "somebody", "anyone", "discuss", "discussed", "discussion",
}

# Intent gate: the prompt looks like a propose / build / diagnose / status-of-X
# request — the surfaces where un-grounded proposals happen. Deliberately broad;
# the keyword-MATCH gate (must overlap real prior work) is what gives precision,
# so a loose intent gate costs nothing when no prior work exists.
INTENT = re.compile(
    r"\b("
    r"build|add|create|implement|propose|set up|wire up|introduce|"           # propose/build
    r"should (we|i)|could (we|i)|can (we|i)|let'?s|why don'?t (we|i)|"         # suggestion
    r"diagnose|why (is|does|are|did|isn'?t|doesn'?t)|investigate|debug|"       # diagnose
    r"figure out|root[- ]cause|what'?s (wrong|broken|failing|happening)|"
    r"what'?s the status|any updates?|do we (have|already)|is there (a|an)|"   # status/prior-existence
    r"have we|did we (already|ever)|has (anyone|somebody|someone)|"
    r"is this (already|a thing)|does (this|that) (already )?exist"
    r")\b",
    re.I,
)


def _kw(text: str) -> list[str]:
    """Distinctive topic keywords (>=5 chars, not generic), longest first."""
    seen: set[str] = set()
    out: list[str] = []
    for t in re.findall(r"[a-z][a-z0-9_-]{4,}", text.lower()):
        if t in STOP or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return sorted(out, key=len, reverse=True)[:8]


def _scan_index_and_files(base: Path, kw: list[str]) -> list[str]:
    """Curated knowledge store: research-index rows + research/decisions filenames.

    Highest precision and not time-bounded — a months-old memo is exactly what
    gets rediscovered, and the commit scan can't see it.
    """
    strong = [k for k in kw if len(k) >= 6] or kw
    refs: list[str] = []
    idx = base / ".claude/rules/research-index.md"
    try:
        if idx.is_file():
            for line in idx.read_text(errors="ignore").splitlines():
                if "|" not in line:
                    continue
                ll = line.lower()
                if any(re.search(rf"\b{re.escape(k)}\b", ll) for k in strong):
                    m = re.search(r"`([^`]+\.md)`", line)
                    refs.append(m.group(1) if m else line.strip()[:70])
    except Exception:
        pass
    for sub in ("research", "decisions"):
        d = base / sub
        try:
            if d.is_dir():
                for f in d.glob("*.md"):
                    nl = f.name.lower()
                    if any(k in nl for k in strong):
                        refs.append(f"{sub}/{f.name}")
        except Exception:
            pass
    return refs


def _scan_ideas(base: Path, kw: list[str]) -> list[str]:
    """ideas.md backlog lines whose text overlaps the prompt keywords."""
    strong = [k for k in kw if len(k) >= 6] or kw
    out: list[str] = []
    f = base / "ideas.md"
    try:
        if f.is_file():
            for line in f.read_text(errors="ignore").splitlines():
                s = line.strip().lstrip("-*# ").strip()
                if len(s) < 12:
                    continue
                sl = s.lower()
                if any(re.search(rf"\b{re.escape(k)}\b", sl) for k in strong):
                    out.append(s[:90])
    except Exception:
        pass
    return out


def _scan_git(cwd: str, kw: list[str]) -> list[str]:
    """Recent commit subjects in cwd (this repo family auto-commits per task,
    so finished work IS the log). Tightly capped — runs on substantive prompts."""
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "log", "--no-merges", "-200", "--since=30.days",
             "--format=%h%x09%s"],
            capture_output=True, text=True, timeout=2.5,
        ).stdout
    except Exception:
        return []
    hits: list[str] = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        h, subj = line.split("\t", 1)
        sl = subj.lower()
        strong = [k for k in kw if len(k) >= 6 and re.search(rf"\b{re.escape(k)}\b", sl)]
        any_hits = [k for k in kw if re.search(rf"\b{re.escape(k)}\b", sl)]
        if strong or len(any_hits) >= 2:
            hits.append(f"{h}  {subj.strip()}")
    return hits


def _dedup_path(session_id: str) -> Path:
    sid = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "nosession")[:64] or "nosession"
    return Path.home() / ".claude" / f".prior-context-seen-{sid}.txt"


def _already_surfaced(session_id: str, sig: str) -> bool:
    p = _dedup_path(session_id)
    try:
        if p.is_file() and sig in p.read_text(errors="ignore").split():
            return True
    except Exception:
        return False
    return False


def _mark_surfaced(session_id: str, sig: str) -> None:
    p = _dedup_path(session_id)
    try:
        with p.open("a") as fh:
            fh.write(sig + "\n")
    except Exception:
        pass


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        return
    env = json.loads(raw)
    prompt = (env.get("user_message") or "").strip()
    cwd = env.get("cwd") or "."
    session_id = env.get("session_id") or ""
    if not prompt or len(prompt) < 8:
        return

    # --- Cheap gate FIRST: no propose/diagnose intent -> exit before any I/O.
    if not INTENT.search(prompt):
        return

    kw = _kw(prompt)
    if not kw:
        return

    base = Path(cwd)
    memos = _scan_index_and_files(base, kw)
    ideas = _scan_ideas(base, kw)
    commits = _scan_git(cwd, kw)
    if not (memos or ideas or commits):
        return  # intent present but no prior work -> nothing to front-load

    # De-dup within the session on the surfaced reference-set: a focused session
    # re-asking about the same topic must not re-inject the same context.
    def _dedup(seq: list[str]) -> list[str]:
        seen: set[str] = set()
        keep: list[str] = []
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            keep.append(x)
        return keep

    memos, ideas, commits = _dedup(memos)[:5], _dedup(ideas)[:4], _dedup(commits)[:6]
    sig = hashlib.sha1("|".join(memos + ideas + commits).encode()).hexdigest()[:12]
    if _already_surfaced(session_id, sig):
        return

    matched_kw = sorted({
        k for k in kw
        if any(re.search(rf"\b{re.escape(k)}\b", s.lower()) for s in memos + ideas + commits)
        or any(k in s.lower() for s in memos)
    }) or kw[:4]

    parts = [
        "PRIOR-CONTEXT (harness-supplied, advisory): your request touches "
        f"[{', '.join(matched_kw)}], which already has history. READ the relevant "
        "ones before proposing/diagnosing — build on, narrow to the real gap, or "
        "supersede them; don't re-derive."
    ]
    if memos:
        parts.append("Curated memo(s)/decision(s):\n" + "\n".join(f"  {m}" for m in memos))
    if commits:
        parts.append(f"{len(commits)} recent commit(s):\n" + "\n".join(f"  {c}" for c in commits))
    if ideas:
        parts.append("ideas.md backlog:\n" + "\n".join(f"  {i}" for i in ideas))
    parts.append("(blindspot-miner #1 cluster; decisions/2026-06-07-state-externalization-lens.md)")

    _mark_surfaced(session_id, sig)

    # Best-effort ROI trigger log (Constitution Principle 3 — measure to promote/demote).
    try:
        subprocess.run(
            [str(Path.home() / "Projects/skills/hooks/hook-trigger-log.sh"),
             "prior-context", "warn",
             f"kw={','.join(matched_kw)} m={len(memos)} c={len(commits)} i={len(ideas)}"],
            timeout=1.0, capture_output=True,
        )
    except Exception:
        pass

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(parts),
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
