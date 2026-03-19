#!/usr/bin/env python3
"""Parse git commit message and check format rules.

Reads hook JSON from stdin, outputs one of:
  SKIP        — not a git commit
  BLOCK:msg   — must block (Co-Authored-By)
  WARN:msg    — advisory warnings (pipe-separated)
  OK          — all checks pass

Correction rate logging: warnings are logged to ~/.claude/commit-check-log.jsonl
for measuring adoption rates over time.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime

GOVERNANCE_PATTERNS = re.compile(
    r"(CLAUDE\.md|MEMORY\.md|improvement-log|\.claude/rules/|hooks/|settings\.json)"
)

DESIGN_KEYWORDS = re.compile(
    r"(design|architect|choose|select|prefer|instead of|alternative|trade.?off)",
    re.IGNORECASE,
)


def get_staged_files():
    """Get list of staged files (for trailer scaffolding)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        pass
    return []


def get_known_scopes():
    """Load canonical scopes from .git-scopes, or extract from recent history."""
    # Try .git-scopes in repo root
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if root.returncode == 0:
            scopes_path = os.path.join(root.stdout.strip(), ".git-scopes")
            if os.path.isfile(scopes_path):
                with open(scopes_path) as f:
                    return {
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    }
    except Exception:
        pass

    # Dynamic fallback: scopes with 2+ uses in last 200 commits
    try:
        result = subprocess.run(
            ["git", "log", "--format=%s", "-200"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            scope_counts = {}
            for line in result.stdout.strip().split("\n"):
                m = re.match(r"\[([^\]]+)\]", line)
                if m:
                    scope_counts[m.group(1)] = scope_counts.get(m.group(1), 0) + 1
            return {s for s, c in scope_counts.items() if c >= 2}
    except Exception:
        pass
    return set()


def log_check(subject, warnings, suggestions):
    """Log commit check results for correction rate measurement."""
    log_path = os.path.expanduser("~/.claude/commit-check-log.jsonl")
    try:
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "subject_len": len(subject),
            "warnings": warnings,
            "suggestions": suggestions,
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
    except Exception:
        pass


def main():
    try:
        d = json.load(sys.stdin)
        cmd = d.get("tool_input", {}).get("command", "")
    except Exception:
        print("SKIP")
        return

    if "git commit" not in cmd:
        print("SKIP")
        return

    # Blocking: Co-Authored-By: Claude
    if re.search(r"Co-Authored-By.*Claude", cmd, re.IGNORECASE):
        print("BLOCK:Commit contains Co-Authored-By: Claude — remove it.")
        return

    # Extract commit message from heredoc or -m flag
    msg = ""
    heredoc = re.search(r"<<\s*'?EOF'?\s*\n(.*?)\nEOF", cmd, re.DOTALL)
    if heredoc:
        msg = heredoc.group(1)
    else:
        m_match = re.search(r'-m\s+"(.*?)"', cmd, re.DOTALL)
        if not m_match:
            m_match = re.search(r"-m\s+'(.*?)'", cmd, re.DOTALL)
        if m_match:
            msg = m_match.group(1)

    if not msg.strip():
        print("SKIP")
        return

    warnings = []
    suggestions = []
    lines = msg.strip().split("\n")
    subject = lines[0].strip()

    # --- Scope prefix ---
    scope_match = re.match(r"\[([^\]]+)\]", subject)
    if not scope_match:
        warnings.append("Missing [scope] prefix.")
    else:
        scope = scope_match.group(1)
        known = get_known_scopes()
        if known and scope not in known:
            sample = ", ".join(sorted(known)[:8])
            warnings.append(f"Unknown scope [{scope}]. Known: {sample}.")

    # --- Subject length ---
    if len(subject) > 80:
        warnings.append(
            f"Subject is {len(subject)} chars (>80). Move the why to the body."
        )

    # --- Em-dash separator ---
    if "\u2014" not in subject:
        warnings.append("Subject lacks em-dash. Format: [scope] Verb thing \u2014 why.")

    # --- Body presence (shell wrapper filters by staged file count) ---
    body_lines = [
        l for l in lines[1:]
        if l.strip() and not re.match(r"^[A-Za-z-]+:\s", l)
    ]
    if len(body_lines) < 1:
        warnings.append("NOBODY")

    # --- Parse existing trailers ---
    trailers = {}
    for l in lines[1:]:
        tm = re.match(r"^([A-Za-z-]+):\s+(.+)", l)
        if tm:
            trailers[tm.group(1)] = tm.group(2)

    # --- Trailer scaffolding ---
    staged = get_staged_files()

    # Governance files → suggest Evidence:
    if staged and any(GOVERNANCE_PATTERNS.search(f) for f in staged):
        if "Evidence" not in trailers:
            suggestions.append(
                "Governance files staged \u2014 add Evidence: trailer."
            )

    # Design-choice language → suggest Rejected:
    if DESIGN_KEYWORDS.search(msg) and "Rejected" not in trailers:
        suggestions.append(
            "Design choice detected \u2014 consider Rejected: trailer for discarded alternatives."
        )

    # Always suggest Session-ID: if available and missing
    if "Session-ID" not in trailers:
        sid_path = os.path.join(os.getcwd(), ".claude", "current-session-id")
        if os.path.isfile(sid_path):
            try:
                with open(sid_path) as f:
                    sid = f.read().strip()
                if sid:
                    suggestions.append(f"Add Session-ID: {sid}")
            except Exception:
                pass

    # New script gate → suggest Native-First: trailer
    if staged and "Native-First" not in trailers:
        try:
            added = subprocess.run(
                ["git", "diff", "--cached", "--diff-filter=A", "--name-only"],
                capture_output=True, text=True, timeout=5,
            )
            if added.returncode == 0:
                new_scripts = [
                    f for f in added.stdout.strip().split("\n")
                    if f.startswith("scripts/") and f.endswith(".py")
                ]
                if new_scripts:
                    names = ", ".join(os.path.basename(f) for f in new_scripts)
                    suggestions.append(
                        f"New script(s): {names} — add Native-First: trailer"
                        " explaining what native approach was considered."
                    )
        except Exception:
            pass

    # --- Log for correction rate measurement ---
    if warnings or suggestions:
        log_check(subject, warnings, suggestions)

    # --- Output ---
    all_msgs = warnings + [f"Suggest: {s}" for s in suggestions]
    if all_msgs:
        print("WARN:" + " | ".join(all_msgs))
    else:
        print("OK")


if __name__ == "__main__":
    main()
