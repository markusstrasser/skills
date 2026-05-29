#!/usr/bin/env bash
# pretool-git-add-all-guard.sh — PreToolUse(Bash) hook.
# Blocks `git add -A`, `git add --all`, and `git add .` — the global rule
# (~/.claude/CLAUDE.md <git_rules>) bans them: they sweep in untracked scratch
# files, .scratch/ artifacts, and temp outputs. Stage specific files or use
# `git add -p` instead.
#
# Blocking contract: exit 2 with a message on stderr re-prompts the model.
# Exit 0 (silent) = allow. Fails open on parse errors.
#
# This converts an instruction (0% reliable per Principle 1) into architecture.
# A standalone "." token or -A/--all flag is the signal; `git add ./path/file`
# and `git add -p` are untouched.
#
# NOTE: no `trap 'exit 0' ERR` here — it would swallow Python's exit 2
# (documented gotcha in ~/.claude/CLAUDE.md). We rely on the Python block's
# own try/except to fail open, and propagate its exit code verbatim.

INPUT=$(cat)

python3 - "$INPUT" <<'PY'
import sys, json, re, shlex

try:
    data = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)

cmd = (data.get("tool_input", {}) or {}).get("command", "")
if not cmd or "add" not in cmd:
    sys.exit(0)

# Split into segments on shell separators so `git add -A && ...` is caught.
segments = re.split(r"&&|\|\||;|\||\n", cmd)

def offends(seg):
    seg = seg.strip()
    try:
        parts = shlex.split(seg)
    except ValueError:
        # Unparseable segment — cheap regex fallback, anchored to segment start.
        return bool(re.match(r"(?:[A-Za-z_]\w*=\S+\s+)*git\s+add\b.*(\s-A\b|\s--all\b|\s\.(\s|$))", seg))
    # Require `git` as the segment's first real token (after optional VAR=val
    # env assignments) — so `echo ... git add -A` and commit messages that
    # merely mention the banned form aren't matched.
    i = 0
    while i < len(parts) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", parts[i]):
        i += 1
    if i >= len(parts) or parts[i] != "git":
        return False
    j = i + 1
    while j < len(parts) and parts[j].startswith("-"):
        j += 2 if parts[j] in ("-C", "-c") else 1
    if j >= len(parts) or parts[j] != "add":
        return False
    args = parts[j + 1:]
    for a in args:
        if a in ("-A", "--all", "."):
            return True
        # bundled short flags like -An are unusual; catch -A inside a -xA combo
        if re.fullmatch(r"-[A-Za-z]*A[A-Za-z]*", a):
            return True
    return False

if any(offends(s) for s in segments):
    sys.stderr.write(
        "BLOCK: `git add -A` / `git add .` / `git add --all` are banned "
        "(global <git_rules>) — they sweep in untracked scratch/temp files. "
        "Stage specific files (`git add path/to/file`) or use `git add -p`.\n"
    )
    sys.exit(2)

sys.exit(0)
PY
rc=$?
# Log blocks for ROI / false-positive analysis. The BLOCK message itself was
# already written to stderr by the Python block (preserved for re-prompting).
if [ "$rc" -eq 2 ]; then
    _cmd=$(printf '%s' "$INPUT" | python3 -c "import sys,json;print(((json.load(sys.stdin).get('tool_input',{}) or {}).get('command','') or '')[:80])" 2>/dev/null)
    ~/Projects/skills/hooks/hook-trigger-log.sh "git-add-all-guard" "block" "$_cmd" 2>/dev/null || true
fi
exit $rc
