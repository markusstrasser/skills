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
    blob=$(git show ":$f" 2>/dev/null) || continue
    [ -z "$blob" ] && continue

    # Determine the checker by extension, falling back to the shebang so that
    # EXTENSIONLESS hooks (e.g. `.githooks/pre-commit` itself) are still checked.
    # Order matters: python before zsh before bash/sh; zsh before sh ("zsh"
    # contains "sh").
    kind=""
    case "$f" in
        *.sh|*.bash) kind=sh ;;
        *.zsh) kind=zsh ;;
        *.py) kind=py ;;
        *)
            first=$(printf '%s' "$blob" | head -1)
            case "$first" in
                "#!"*python*) kind=py ;;
                "#!"*zsh*) kind=zsh ;;
                "#!"*bash*|"#!"*sh*) kind=sh ;;
            esac
            ;;
    esac
    [ -z "$kind" ] && continue  # not a recognized script — not our concern

    CHECKED=$((CHECKED + 1))
    err=""
    case "$kind" in
        sh)  printf '%s\n' "$blob" | bash -n 2>/tmp/_hookchk.$$ || err=1 ;;
        py)  printf '%s\n' "$blob" | python3 -c \
                'import sys; compile(sys.stdin.read(), sys.argv[1], "exec")' "$f" 2>/tmp/_hookchk.$$ || err=1 ;;
        zsh)
            # Do NOT bash -n a zsh script — bash grammar false-blocks valid zsh.
            # Skip (don't block) when zsh is unavailable.
            if command -v zsh >/dev/null 2>&1; then
                printf '%s\n' "$blob" | zsh -n 2>/tmp/_hookchk.$$ || err=1
            else
                echo "  (skip $f — zsh not installed; cannot safely syntax-check zsh)"
                CHECKED=$((CHECKED - 1))
            fi
            ;;
    esac
    if [ -n "$err" ]; then
        echo "BLOCKED: $f has a $kind syntax error:"
        sed 's/^/    /' /tmp/_hookchk.$$ 2>/dev/null | head -8
        FAILED=1
    fi
done

rm -f /tmp/_hookchk.$$ 2>/dev/null

# ── Input-contract gate ──────────────────────────────────────────────────
# Tool input arrives on stdin as the full envelope; fields live under
# .tool_input. CLAUDE_TOOL_* env vars are unset under Claude Code. A hook that
# reads $CLAUDE_TOOL_INPUT or extracts top-level .command is silently dead — the
# 2026-06-07 audit found 15 such fleet-wide guards (incl. bash-loop / append-only
# / llmx). This gate blocks new occurrences. Lints STAGED content.
CONTRACT_LINT="$(dirname "$0")/lint_hook_input_contract.py"
if [ -f "$CONTRACT_LINT" ]; then
    _ctmp=$(mktemp -d)
    _cfiles=()
    for f in "${STAGED[@]}"; do
        case "$f" in *.sh|*.bash) ;; *) continue ;; esac
        is_hook_path "$f" || continue
        git show ":$f" > "$_ctmp/$(basename "$f")" 2>/dev/null || continue
        _cfiles+=("$_ctmp/$(basename "$f")")
    done
    if [ "${#_cfiles[@]}" -gt 0 ] && ! _cout=$(python3 "$CONTRACT_LINT" "${_cfiles[@]}" 2>&1); then
        echo "$_cout"
        echo ""
        echo "BLOCKED: a staged hook violates the Claude/Codex input contract."
        echo "Read input from stdin (INPUT=\"\${CLAUDE_TOOL_INPUT:-\$(cat)}\") and extract"
        echo "tool fields from .tool_input.<field>, not the top level."
        FAILED=1
    fi
    rm -rf "$_ctmp"
fi

if [ "$FAILED" -ne 0 ]; then
    echo ""
    echo "A staged hook is broken (syntax or input-contract). Fix it before committing —"
    echo "a broken shared hook blocks or silently disables tool handling across sessions."
    exit 1
fi

exit 0
