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
import shlex
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


def _is_test_script(path):
    """Mirror the native_first grader's exclusion (evals/graders/governance/
    native_first.py): tests/fixtures are not 'new capability scripts' — there is
    no native-tool alternative to a unit test, so no Native-First: trailer is
    expected. Keep this predicate in sync with the grader so the advisory fires
    on exactly the population the metric measures (else it nudges on files that
    never count — a false positive)."""
    base = path.rsplit("/", 1)[-1]
    return (
        "/tests/" in path
        or base.startswith("test_")
        or base.endswith("_test.py")
        or base == "conftest.py"
    )


def get_known_scopes():
    """Load canonical scopes from .git-scopes. No fallback: repos without an
    explicit .git-scopes opted out of scope checking (the git-history-guessing
    fallback produced 870 false-positive warns in 8 days, mostly in throwaway
    eval dirs — measured 2026-06-12)."""
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
    return set()


ASSIGNMENT = re.compile(r"""(?:^|[\s;&(])([A-Za-z_]\w*)=("[^"]*"|'[^']*'|[^\s;&|]+)""")


def _expand(text, env):
    return re.sub(r"\$\{(\w+)\}|\$(\w+)", lambda m: env.get(m.group(1) or m.group(2), m.group(0)), text)


def _pathspec_commit(cmd, default_cwd):
    """(workdir, pathspecs) of a `git [-C dir] commit ... -- <paths>` in cmd, or None.

    Only the `--` form is read. `cd dir` segments before the commit and `-C dir` set the workdir;
    simple VAR=value assignments in the command are expanded, and a pathspec that still holds a `$`
    is dropped rather than guessed. A segment shlex cannot split is skipped.
    """
    head = re.split(r"<<-?\s*['\"]?[A-Za-z_]+['\"]?", cmd, maxsplit=1)[0]
    env = {}
    for m in ASSIGNMENT.finditer(head):
        value = m.group(2)
        env[m.group(1)] = value[1:-1] if value[:1] in "\"'" else value
    workdir = default_cwd
    for segment in re.split(r"&&|\|\||;|\n|\|", head):
        try:
            toks = shlex.split(segment)
        except ValueError:
            continue
        if len(toks) > 1 and toks[0] == "cd":
            workdir = os.path.join(workdir, os.path.expanduser(_expand(toks[1], env)))
            continue
        if "git" not in toks or "commit" not in toks[toks.index("git"):]:
            continue
        g = toks.index("git")
        c = toks.index("commit", g)
        wd = workdir
        opts = toks[g + 1:c]
        for i, tok in enumerate(opts[:-1]):
            if tok == "-C":
                wd = os.path.join(wd, os.path.expanduser(_expand(opts[i + 1], env)))
        rest = toks[c + 1:]
        if "--" not in rest:
            return None
        specs = [_expand(t, env) for t in rest[rest.index("--") + 1:]]
        specs = [s for s in specs if s and "$" not in s]
        return (wd, specs) if specs else None
    return None


def untracked_under_pathspecs(cmd, default_cwd):
    """Untracked, non-ignored files under a pathspec commit's paths.

    `git commit -- <dir>` takes only files git already tracks, so new files in a directory that
    holds tracked ones are left out without any message. 2026-09-25: immigration-research 7ec7144
    named a lane directory whose results, inventory and two tests were all new; none landed, and
    the commit body described them (fixed in ed1b623).
    """
    spec = _pathspec_commit(cmd, default_cwd)
    if not spec:
        return []
    workdir, specs = spec
    try:
        r = subprocess.run(
            ["git", "-C", workdir, "ls-files", "--others", "--exclude-standard", "-z", "--", *specs],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return []
    if r.returncode != 0:
        return []
    return [f for f in r.stdout.split("\0") if f]


def untracked_message(files):
    shown = ", ".join(files[:5]) + (f" and {len(files) - 5} more" if len(files) > 5 else "")
    return (
        f"{len(files)} untracked file(s) under this commit's pathspecs stay out of it: a pathspec"
        f" commit takes tracked files only, so git add them first if they belong ({shown})."
    )


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

    untracked = []
    if "git" in cmd and "commit" in cmd:
        untracked = untracked_under_pathspecs(cmd, d.get("cwd") or os.getcwd())

    # Message checks read "git commit" only; `git -C dir commit` gets the untracked check alone,
    # since the wrapper's staged-file checks run in the hook's cwd, not in dir.
    if "git commit" not in cmd:
        print("WARN:" + untracked_message(untracked) if untracked else "SKIP")
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
        print("WARN:" + untracked_message(untracked) if untracked else "SKIP")
        return

    warnings = [untracked_message(untracked)] if untracked else []
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

    # Session-ID: NOT suggested — the prepare-commit-msg git hook auto-appends
    # it; the suggestion was unactionable noise on 97% of commits (1,996/2,065
    # in 8 days, measured 2026-06-12).

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
                    and not _is_test_script(f)
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
