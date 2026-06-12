#!/usr/bin/env bash
# pretool-git-noext-inject.sh — PreToolUse(Bash) hook.
# Rewrites agent `git diff|show|log` invocations to add --no-ext-diff --no-pager
# via the PreToolUse `updatedInput` contract, so configured external differs
# (difft/delta) can't inject SOH/ANSI control bytes or silently truncate.
# This converts the global "use --no-ext-diff" instruction (0% reliable) into
# architecture. Human TTY git invocations are unaffected — only the agent's
# tool calls pass through here.
#
# Contract (binary 2.1.156): exit 0 + JSON
#   {"hookSpecificOutput":{"hookEventName":"PreToolUse","updatedInput":{...}}}
# rewrites the tool input before execution. Exit 0 with no output = no change.
#
# Evidence: ~/.claude/CLAUDE.md <environment> — ~30 min lost to SOH bytes in a
# diff stream; rule was instruction-only until now.

trap 'exit 0' ERR

INPUT=$(cat)

OUT=$(python3 - "$INPUT" <<'PY'
import sys, json, shlex

try:
    data = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)

ti = data.get("tool_input", {}) or {}
cmd = ti.get("command", "")
if not cmd:
    sys.exit(0)

# Only rewrite SIMPLE single git invocations. Compound commands (pipes, &&, ;,
# subshells, command substitution) are left untouched — rewriting them risks
# corruption. ONE redirect shape IS handled: a single trailing `> file` /
# `>> file` — that's the patch-generation form where difftastic output becomes
# a persisted garbage artifact (2× on 2026-06-12: entity-escape patch + p2
# LUT patch, both rejected by git apply as "No valid patches").
if any(tok in cmd for tok in ("|", "&&", "||", ";", "$(", "`", "<", "\n")):
    sys.exit(0)

try:
    parts = shlex.split(cmd)
except ValueError:
    sys.exit(0)

# Trailing-redirect handling: accept exactly [... '>' target] or [... '>>' target]
# with no other '>' anywhere; anything else with '>' bails (fd redirects like
# 2>&1, attached forms like '>file', multiple redirects).
redirect_suffix = []
if ">" in cmd:
    if (
        len(parts) >= 3
        and parts[-2] in (">", ">>")
        and ">" not in parts[-1]
        and not any(">" in p for p in parts[:-2])
    ):
        redirect_suffix = parts[-2:]
        parts = parts[:-2]
    else:
        sys.exit(0)
if not parts or parts[0] != "git":
    sys.exit(0)

# Skip optional leading global flags: git -C <path> / -c k=v / --no-pager etc.
i = 1
while i < len(parts) and parts[i].startswith("-"):
    # -C and -c take an argument
    if parts[i] in ("-C", "-c"):
        i += 2
    else:
        i += 1
if i >= len(parts):
    sys.exit(0)

subcmd = parts[i]
if subcmd not in ("diff", "show", "log"):
    sys.exit(0)

if "--no-ext-diff" in parts and "--no-pager" in parts:
    sys.exit(0)  # already safe

# Inject --no-pager as a git global flag (before subcommand) and --no-ext-diff
# right after the subcommand. Both are idempotent / harmless to re-add once.
new = parts[:i]
if "--no-pager" not in new:
    new += ["--no-pager"]
new += [subcmd]
rest = parts[i + 1 :]
if "--no-ext-diff" not in rest:
    new += ["--no-ext-diff"]
new += rest

new_cmd = " ".join(shlex.quote(p) for p in new)
if redirect_suffix:
    new_cmd += " " + redirect_suffix[0] + " " + shlex.quote(redirect_suffix[1])
if new_cmd == cmd:
    sys.exit(0)

updated = dict(ti)
updated["command"] = new_cmd
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "updatedInput": updated,
    }
}))
PY
)
# Re-emit the rewrite JSON (consumed by Claude Code) and log the trigger so
# the guard accrues ROI telemetry like the rest of the hook fleet.
if [ -n "$OUT" ]; then
    printf '%s\n' "$OUT"
    ~/Projects/skills/hooks/hook-trigger-log.sh "git-noext-inject" "rewrite" "git diff/show/log" 2>/dev/null || true
fi
exit 0
