#!/usr/bin/env python3
"""pretool-prebuild-inventory-shadow.py — SHADOW: catch rediscovery at the BUILD action, not the prompt.

Phase-1 finding (agent-infra 2026-06-19): the prompt-gated `userprompt-prior-context.py` shows 0 fires
in agent-infra despite 37 rediscovery corrections, because rediscovery is usually AGENT-INITIATED
(the agent reads a digest/priority/plan and starts building) or follows a TERSE prompt ("go", "ok a")
that carries no topic keyword — so the UserPromptSubmit hook never sees the topic. The fix is to gate
on the ACTION: when the agent creates a NEW substantive artifact, scan for prior work on that topic.

This is the action-gated sibling of prior-context. SHADOW: it logs what it WOULD surface; it does NOT
inject. After a precision window, promote to advisory (`permissionDecision: allow` +
`additionalContext`: "this topic already has history: … — build on / supersede, don't re-derive").

Why self-contained (not importing prior-context's scan): hooks must be independently fail-open; a bug
in a shared module would take down both. If this graduates, a shared `prior_work_scan` module is then
justified (2 proven consumers, proven-common test) — note it in improvement-log at promotion, not now.

PreToolUse envelope (Claude Code 2.1.x): .tool_name, .tool_input{file_path,content}, .cwd, .session_id.
Gate is CHEAP-FIRST: tool must be Write to a NEW buildable artifact, else exit before any I/O.
"""
# Gov-ID: hook:prebuild-inventory-shadow
# goal: catch agent-initiated rediscovery (build a thing that already exists) at the Write action,
#       which the prompt-gated prior-context hook structurally misses (Phase-1 A1, 85 corrections)
# verifier: null  # semantic (did surfaced prior work actually match?) — shadow log reviewed for precision
# blast_radius: shared  # wired agent-infra-first; shadow (log-only), cheap-gated, fails open
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SHADOW_LOG = os.path.expanduser("~/.claude/prebuild-inventory-shadow.jsonl")

# Buildable substantive artifacts — where "I'm starting work on a topic" lives. NOT every Write.
BUILDABLE = re.compile(
    r"(^|/)scripts/[^/]+\.py$"          # a new script
    r"|(^|/)(decisions|research)/[^/]+\.md$"  # a new memo/decision
    r"|(^|/)\.claude/plans/[^/]+\.md$"        # a new plan
    r"|(^|/)src/[^/]+/[^/]+\.py$",            # a new module
    re.I,
)

STOP = {
    "scripts", "decisions", "research", "plans", "claude", "src", "test", "tests",
    "shadow", "hook", "hooks", "gate", "draft", "notes", "index", "report", "the",
    "and", "for", "with", "from", "into", "this", "that", "your", "our", "new",
}


def _kw_from_path(path: str) -> list[str]:
    base = Path(path).name.lower()
    base = re.sub(r"\d{4}-\d{2}-\d{2}", " ", base)          # strip ISO dates
    base = re.sub(r"\.(py|md|sql|sh|json)$", "", base)
    toks = re.findall(r"[a-z][a-z0-9]{3,}", base)
    out, seen = [], set()
    for t in toks:
        if t in STOP or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return sorted(out, key=len, reverse=True)[:6]


def _kw_from_content(content: str) -> list[str]:
    """A few distinctive tokens from the first ~600 chars (title/docstring carry the topic)."""
    head = content[:600].lower()
    toks = re.findall(r"[a-z][a-z0-9_-]{5,}", head)
    out, seen = [], set()
    for t in toks:
        if t in STOP or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= 6:
            break
    return out


def _scan_prior(base: Path, kw: list[str]) -> list[str]:
    strong = [k for k in kw if len(k) >= 6] or kw
    if not strong:
        return []
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
                    refs.append(m.group(1) if m else line.strip()[:60])
    except Exception:
        pass
    for sub in ("research", "decisions"):
        d = base / sub
        try:
            if d.is_dir():
                for f in d.glob("*.md"):
                    if any(k in f.name.lower() for k in strong):
                        refs.append(f"{sub}/{f.name}")
        except Exception:
            pass
    # dedup, cap
    out, seen = [], set()
    for r in refs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out[:6]


def _scan_git(cwd: str, kw: list[str]) -> list[str]:
    strong = [k for k in kw if len(k) >= 6] or kw
    if not strong:
        return []
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "log", "--no-merges", "-200", "--since=45.days", "--format=%h%x09%s"],
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
        if any(re.search(rf"\b{re.escape(k)}\b", sl) for k in strong):
            hits.append(f"{h}  {subj.strip()}")
        if len(hits) >= 6:
            break
    return hits


def _dedup_path(session_id: str) -> Path:
    sid = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "nosession")[:64] or "nosession"
    return Path.home() / ".claude" / f".prebuild-inv-seen-{sid}.txt"


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        return
    env = json.loads(raw)
    if env.get("tool_name") != "Write":
        return
    ti = env.get("tool_input") or {}
    fpath = ti.get("file_path") or ""
    if not fpath or not BUILDABLE.search(fpath.replace(os.sep, "/")):
        return
    # NEW file only — overwriting an existing file is not a fresh build.
    try:
        if Path(fpath).exists():
            return
    except Exception:
        pass

    cwd = env.get("cwd") or "."
    session_id = env.get("session_id") or ""
    content = ti.get("content") or ""

    kw = list(dict.fromkeys(_kw_from_path(fpath) + _kw_from_content(content)))[:8]
    if not kw:
        return

    base = Path(cwd)
    memos = _scan_prior(base, kw)
    commits = _scan_git(cwd, kw)
    if not (memos or commits):
        return  # nothing prior on this topic — the common, correct case; stay silent

    sig = hashlib.sha1("|".join(memos + commits).encode()).hexdigest()[:12]
    seen_p = _dedup_path(session_id)
    try:
        if seen_p.is_file() and sig in seen_p.read_text(errors="ignore").split():
            return
    except Exception:
        pass

    row = {
        "ts": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "session_id": session_id,
        "cwd": cwd,
        "new_file": fpath,
        "kw": kw,
        "would_surface_memos": memos,
        "would_surface_commits": commits[:4],
    }
    try:
        with open(SHADOW_LOG, "a") as fh:
            fh.write(json.dumps(row) + "\n")
        with seen_p.open("a") as fh:
            fh.write(sig + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
