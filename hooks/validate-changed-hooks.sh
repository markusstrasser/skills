#!/usr/bin/env bash
# Pre-commit syntax gate for hook scripts. Repo-agnostic.
#
# Validates the STAGED CONTENT (not the working tree — robust to `git add -p`)
# of every changed hook file, so a hook that doesn't parse can never land:
#   *.sh / *.bash  -> bash -n
#   *.zsh          -> zsh -n   (falls back to bash -n if zsh absent)
#   *.py           -> python3 compile()
#
# A "hook file" is any staged file whose path is under a `hooks/` directory or
# under `.claude/hooks/` (covers both ~/Projects/skills/hooks/ and a project's
# .claude/hooks/). Non-hook files are ignored — this gate is narrow on purpose.
#
# Why this exists (2026-05-29 retro #3): an unclosed `$(` landed in
# ~/Projects/skills/hooks/pretool-git-noext-inject.sh and blocked ALL Bash across
# every session until fixed. ~/Projects/skills/ had no pre-commit at all. A
# syntactically-broken SHARED hook is a fleet-wide outage. Pure validation,
# zero false-positive surface (only flags genuine parse failures).
#
# Exit 0 = all staged hooks parse (or none changed). Exit 1 = a hook is broken.

set -u

# Only operate inside a git work tree.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    exit 0
fi

# Staged, added/copied/modified files (skip deletions).
mapfile -t STAGED < <(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)
[ "${#STAGED[@]}" -eq 0 ] && exit 0

is_hook_path() {
    case "$1" in
        */hooks/*|hooks/*|*/.githooks/*|.githooks/*|*/.claude/hooks/*|.claude/hooks/*) return 0 ;;
        *) return 1 ;;
    esac
}

FAILED=0
CHECKED=0

for f in "${STAGED[@]}"; do
    is_hook_path "$f" || continue
    case "$f" in
        *.sh|*.bash)
            CHECKED=$((CHECKED + 1))
            if ! git show ":$f" 2>/dev/null | bash -n 2>/tmp/_hookchk.$$; then
                echo "BLOCKED: $f has a shell syntax error:"
                sed 's/^/    /' /tmp/_hookchk.$$ 2>/dev/null | head -8
                FAILED=1
            fi
            ;;
        *.zsh)
            CHECKED=$((CHECKED + 1))
            CHECKER="bash -n"
            command -v zsh >/dev/null 2>&1 && CHECKER="zsh -n"
            if ! git show ":$f" 2>/dev/null | $CHECKER 2>/tmp/_hookchk.$$; then
                echo "BLOCKED: $f has a shell syntax error:"
                sed 's/^/    /' /tmp/_hookchk.$$ 2>/dev/null | head -8
                FAILED=1
            fi
            ;;
        *.py)
            CHECKED=$((CHECKED + 1))
            if ! git show ":$f" 2>/dev/null | python3 -c \
                'import sys; compile(sys.stdin.read(), sys.argv[1], "exec")' "$f" 2>/tmp/_hookchk.$$; then
                echo "BLOCKED: $f has a Python syntax error:"
                sed 's/^/    /' /tmp/_hookchk.$$ 2>/dev/null | head -8
                FAILED=1
            fi
            ;;
    esac
done

rm -f /tmp/_hookchk.$$ 2>/dev/null

if [ "$FAILED" -ne 0 ]; then
    echo ""
    echo "A staged hook does not parse. Fix it before committing — a broken shared"
    echo "hook blocks tool calls across every active session."
    exit 1
fi

exit 0
