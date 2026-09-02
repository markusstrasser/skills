#!/usr/bin/env bash
# pretool-streaming-cli-guard.sh — block streaming CLI commands without timeout wrapper.
# Streaming commands (modal app logs, tail -f, docker logs -f) without timeout
# leak exec processes and burn context on unchanging output.
# Evidence: 200+ exec-limit warnings in Codex session 019d6d86.
#
# `| head -N` is NOT an accepted bound: head exits, but the producer only dies on its
# next write (SIGPIPE) — a quiet stream still leaks. Only a timeout bounds wall time.
# `--help`/`-h` never streams, so it passes (2026-08-23: blocked `modal app logs --help`
# twice in codex 01a01da9 while the block text itself recommended a `| head` form).
#
# Heredoc bodies are stripped before matching (2026-09-02): a `cat > brief.md <<'EOF'`
# whose TEXT mentions `modal container exec` is not a stream, and the guard blocked a
# lane-brief write in genomics session fe315f9b on exactly that.

trap 'exit 0' ERR
INPUT=$(cat)

CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || true) || exit 0

[ -z "$CMD" ] && exit 0

# Drop heredoc bodies: from a line carrying `<<TAG` / `<<'TAG'` / `<<-"TAG"` up to the
# line that equals TAG. The opening line itself is kept (it may carry the real command).
read -r -d '' STRIP_HEREDOCS <<'AWKEOF' || true
skip != "" { if ($0 == skip || $0 ~ ("^[[:space:]]*" skip "$")) { skip = "" }; next }
{
    if (match($0, /<<-?[[:space:]]*['"]?[A-Za-z_][A-Za-z0-9_]*['"]?/)) {
        tag = substr($0, RSTART, RLENGTH)
        sub(/^<<-?[[:space:]]*/, "", tag)
        gsub(/['"]/, "", tag)
        skip = tag
    }
    print
}
AWKEOF
SCAN=$(printf '%s\n' "$CMD" | awk "$STRIP_HEREDOCS" 2>/dev/null || printf '%s' "$CMD")

# Streaming commands that need timeout wrapping
if echo "$SCAN" | grep -qE '(modal app logs|modal container exec|tail -f|docker logs -f)'; then
    # help output is static, never a stream
    if echo "$SCAN" | grep -qE '(^|[[:space:]])(--help|-h)([[:space:]]|$|\|)'; then
        exit 0
    fi
    if ! echo "$SCAN" | grep -qE '(timeout |gtimeout |--timeout)'; then
        echo "WARN: Streaming command without timeout wrapper." >&2
        echo "  Add: timeout 60 $CMD" >&2
        echo "  (a trailing '| head -N' does not bound a quiet stream — only timeout does)" >&2
        echo "  Streaming commands without timeout leak exec processes and burn context." >&2
        exit 2
    fi
fi

exit 0
