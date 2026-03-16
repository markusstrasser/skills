#!/usr/bin/env bash
# PreToolUse:Bash — catch common llmx dispatch mistakes
# Advisory (exit 0) for warnings, BLOCK (exit 2) for Gemini 2.5 and invalid flags

if [ "$CLAUDE_TOOL_NAME" != "Bash" ]; then exit 0; fi

INPUT="$CLAUDE_TOOL_INPUT"
CMD=$(echo "$INPUT" | jq -r '.command // empty' 2>/dev/null)
[ -z "$CMD" ] && exit 0

# Only check commands that invoke llmx
echo "$CMD" | grep -q 'llmx' || exit 0

WARNINGS=""

# --- SPIN-LOOP detection (per-session llmx call counter) ---
LLMX_COUNTER="/tmp/claude-llmx-count-${PPID:-0}"
LLMX_COUNT=0
[ -f "$LLMX_COUNTER" ] && LLMX_COUNT=$(cat "$LLMX_COUNTER" 2>/dev/null || echo 0)
LLMX_COUNT=$((LLMX_COUNT + 1))
echo "$LLMX_COUNT" > "$LLMX_COUNTER"

if [ "$LLMX_COUNT" -ge 6 ]; then
  echo "[llmx-guard] BLOCKED: $LLMX_COUNT llmx calls this session. This looks like a spin loop." >&2
  echo "  - Diagnose WHY previous calls failed (check stderr, exit code)" >&2
  echo "  - Don't retry the same command — try a different model or approach" >&2
  echo "  - If rate-limited, wait or use a different provider" >&2
  # Log trigger for ROI analysis
  ~/Projects/skills/hooks/hook-trigger-log.sh "llmx-spin-loop" "block" "$LLMX_COUNT calls" 2>/dev/null || true
  exit 2
fi

if [ "$LLMX_COUNT" -ge 4 ]; then
  WARNINGS="${WARNINGS}[llmx-guard] WARNING: $LLMX_COUNT llmx calls this session. Approaching spin-loop territory.\n"
  WARNINGS="${WARNINGS}  - After 2 failures: diagnose before retrying (check stderr/exit code)\n"
  WARNINGS="${WARNINGS}  - Use --fallback for automatic model fallback on rate limits\n"
  WARNINGS="${WARNINGS}  - Blocked at 6 calls.\n"
fi

# --- BLOCKING checks (exit 2) ---

# Gemini 2.5 forbidden — user mandate: always use gemini-3.1-pro
if echo "$CMD" | grep -qiE 'gemini.?2\.5'; then
  echo "[llmx-guard] BLOCKED: Gemini 2.5 is forbidden. Use gemini-3.1-pro-preview instead." >&2
  exit 2
fi

# Invalid/hallucinated flags — these don't exist in llmx
# Known valid long flags (from `llmx chat --help`):
# --model --provider --temperature --reasoning-effort --stream --no-stream
# --compare --providers --timeout --debug --json --list-providers --no-thinking
# --use-old --fast --search --system --file --schema --max-tokens --output --fallback
INVALID_FLAGS=""
for flag in $(echo "$CMD" | grep -oE -- '--[a-z][-a-z]*' | sort -u); do
  case "$flag" in
    --model|--timeout|--max-tokens|--reasoning-effort|--fallback) ;;
    --stream|--schema|--search|--output|--fast|--use-old|--no-thinking|--debug) ;;
    --provider|--providers|--no-stream|--mini|--help|--version) ;;
    --compare|--json|--temperature|--system|--file|--list-providers) ;;
    *) INVALID_FLAGS="${INVALID_FLAGS} ${flag}" ;;
  esac
done
if [ -n "$INVALID_FLAGS" ]; then
  echo "[llmx-guard] BLOCKED: Unknown llmx flags:${INVALID_FLAGS}. Check llmx-guide skill for valid flags." >&2
  exit 2
fi

# Invalid model names — catch common hallucinations
MODEL=$(echo "$CMD" | grep -oE '(-m|--model)\s+[a-zA-Z0-9._-]+' | head -1 | sed 's/^-m\s*//;s/^--model\s*//')
if [ -n "$MODEL" ]; then
  case "$MODEL" in
    gemini-3.1-pro-preview|gemini-3-flash-preview|gemini-3.1-flash-image-preview) ;;
    gpt-5.4|gpt-5.2|gpt-5.3-chat-latest|gpt-5-codex|o4-mini) ;;
    kimi-k2.5|kimi-k2-thinking) ;;
    claude-sonnet-4-6|claude-opus-4-6|claude-haiku-4-5) ;;
    *gemini-3.1-pro*|*gemini-3-flash*) ;; # close enough variants
    *)
      # Catch common hallucinations
      if echo "$MODEL" | grep -qE '^gemini-3\.1-pro$'; then
        echo "[llmx-guard] BLOCKED: Model 'gemini-3.1-pro' needs '-preview' suffix. Use gemini-3.1-pro-preview." >&2
        exit 2
      elif echo "$MODEL" | grep -qE '^gemini-3-flash$|^gemini-flash-3'; then
        echo "[llmx-guard] BLOCKED: Model '$MODEL' is wrong. Use gemini-3-flash-preview." >&2
        exit 2
      elif echo "$MODEL" | grep -qE '^gpt-5\.3$'; then
        echo "[llmx-guard] BLOCKED: Model 'gpt-5.3' needs '-chat-latest' suffix. Use gpt-5.3-chat-latest." >&2
        exit 2
      fi
      # Unknown model — warn but don't block (might be newly added)
      WARNINGS="${WARNINGS}[llmx-guard] Unrecognized model '${MODEL}'. Check llmx-guide for valid names.\n"
      ;;
  esac
fi

# --- ADVISORY checks (warnings only) ---

# 1. Shell redirect with llmx output
if echo "$CMD" | grep -qE 'llmx\s+(chat|research|image|svg|vision)?.*[^2]>\s*["\$\./~a-zA-Z]'; then
  WARNINGS="${WARNINGS}[llmx-guard] Shell redirect detected. Use --output/-o instead of > file — shell redirects buffer until process exit.\n"
fi

# 2. PYTHONUNBUFFERED cargo cult
if echo "$CMD" | grep -qE 'PYTHONUNBUFFERED.*llmx|llmx.*PYTHONUNBUFFERED'; then
  WARNINGS="${WARNINGS}[llmx-guard] PYTHONUNBUFFERED does nothing for llmx output capture. Use --output/-o flag instead.\n"
fi

# 3. stdbuf/script with llmx
if echo "$CMD" | grep -qE '(stdbuf|script\s+-q).*llmx'; then
  WARNINGS="${WARNINGS}[llmx-guard] stdbuf/script won't fix output buffering. Use --output/-o flag instead.\n"
fi

# 4. max_tokens with GPT-5.x reasoning models — warn about small values
if echo "$CMD" | grep -qE 'gpt-5\.[234]' && echo "$CMD" | grep -qE -- '--max-tokens\s+[0-9]{1,4}(\s|$)'; then
  WARNINGS="${WARNINGS}[llmx-guard] Small --max-tokens with GPT-5.x reasoning model. max_completion_tokens includes reasoning tokens — use 16384+ to avoid truncated output.\n"
fi

# 5. Old LiteLLM model prefixes (deprecated in v0.6.0)
if echo "$CMD" | grep -qE 'llmx.*(-m|--model)\s+(gemini/|openai/|xai/|moonshot/)'; then
  WARNINGS="${WARNINGS}[llmx-guard] LiteLLM-style model prefix detected. Prefixes are deprecated in v0.6.0 — use bare model names.\n"
fi

# 6. -f with Gemini models (known to hang — use stdin pipe or -o)
if echo "$CMD" | grep -qE 'gemini' && echo "$CMD" | grep -qE 'llmx.*\s-f\s' && ! echo "$CMD" | grep -qE -- '--output|-o\s'; then
  WARNINGS="${WARNINGS}[llmx-guard] Using -f with Gemini without --output. Consider using stdin pipe (echo | llmx) or add -o for reliable output capture.\n"
fi

# 7. Background dispatch without -o (output lost)
if echo "$CMD" | grep -qE 'llmx.*&\s*$' && ! echo "$CMD" | grep -qE -- '--output|-o\s'; then
  WARNINGS="${WARNINGS}[llmx-guard] Background llmx (&) without --output/-o. Output will be lost. Add -o file.md.\n"
fi

if [ -n "$WARNINGS" ]; then
  echo -e "$WARNINGS" >&2
fi
exit 0
