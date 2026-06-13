#!/usr/bin/env bash
# pretool-predelete-ref-guard.sh — PreToolUse:Bash advisory.
# Before a `git rm` / `rm` of a path whose basename is named in a live routing doc
# (CLAUDE.md / AGENTS.md / README.md / GEMINI.md / .claude/rules/*.md), warn: a file
# referenced in a routing doc is WIRED by definition — deleting it orphans the ref.
# Advisory only (never blocks). Codifies the PRE-DELETE REFERENCE CHECK that caught a
# real skill over-cut on 2026-06-13 (intel/genomics finance+bio skills were documented).
#
# Gov-ID: hook:predelete-ref-guard
# goal: prevent orphaning routing-doc references by deleting a referenced (=wired) file
# verifier: null
# blast_radius: shared

trap 'exit 0' ERR

INPUT=$(cat)

echo "$INPUT" | python3 -c '
import sys, json, os, re, shlex

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

cmd = (data.get("tool_input", {}) or {}).get("command", "") or ""
if not cmd:
    sys.exit(0)

# Only deletions of repo paths. Require a slash-bearing path token so bare `rm tmpfile`
# and `rm -rf /tmp/...` scratch deletes stay quiet.
if not re.search(r"\b(git\s+rm|rm)\b", cmd):
    sys.exit(0)

cwd = data.get("cwd") or os.getcwd()

try:
    toks = shlex.split(cmd)
except Exception:
    toks = cmd.split()

# Candidate deletion targets: non-flag tokens that look like in-repo paths.
SCRATCH = ("/tmp/", "/var/", "node_modules/", ".venv/", "__pycache__", ".git/")
paths = []
for t in toks:
    if t.startswith("-") or t in ("git", "rm"):
        continue
    if "/" not in t:
        continue
    if any(s in t for s in SCRATCH) or t.startswith("/tmp"):
        continue
    paths.append(t)

bases = set()
for p in paths:
    b = os.path.basename(p.rstrip("/"))
    # skip generic basenames that would false-match everywhere
    if b and b not in ("__init__.py", "index.md", "SKILL.md", "README.md"):
        bases.add(b)
if not bases:
    sys.exit(0)

docs = []
for name in ("CLAUDE.md", "AGENTS.md", "README.md", "GEMINI.md"):
    fp = os.path.join(cwd, name)
    if os.path.isfile(fp):
        docs.append(fp)
rules_dir = os.path.join(cwd, ".claude", "rules")
if os.path.isdir(rules_dir):
    for f in sorted(os.listdir(rules_dir)):
        if f.endswith(".md"):
            docs.append(os.path.join(rules_dir, f))

# Dedup symlinked docs (AGENTS.md / GEMINI.md commonly symlink CLAUDE.md).
_seen_real, _docs = set(), []
for d in docs:
    rp = os.path.realpath(d)
    if rp in _seen_real:
        continue
    _seen_real.add(rp)
    _docs.append(d)
docs = _docs

hits = []
for d in docs:
    try:
        text = open(d, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    for b in bases:
        if b in text:
            hits.append((os.path.relpath(d, cwd), b))

if hits:
    seen = []
    for d, b in hits:
        tag = f"{b} → {d}"
        if tag not in seen:
            seen.append(tag)
    listed = "; ".join(seen[:6])
    msg = ("PRE-DELETE REFERENCE CHECK: " + listed +
           ". A path named in a routing doc is wired by definition — clean the reference(s) "
           "or confirm the deletion is intentional AND update the doc in the same change. "
           "(2026-06-13: this exact pattern caught a documented-skill over-cut.)")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": msg,
    }}))
    sys.stderr.write("predelete-ref-guard: " + listed + "\n")
' 2>/dev/null

# Best-effort telemetry (matches sibling hooks); never fail the tool call.
if echo "$INPUT" | grep -qE '"(git rm|rm )' 2>/dev/null; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "predelete-ref-guard" "advisory" "delete reference scan" 2>/dev/null || true
fi

exit 0
