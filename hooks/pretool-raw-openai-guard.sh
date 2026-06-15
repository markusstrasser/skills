#!/bin/bash
# pretool-raw-openai-guard.sh — Block raw OpenAI SDK calls in .py writes; route GPT through llmx.
# PreToolUse:Write|Edit hook. Reads JSON tool input from stdin.
#
# Why: this stack reaches GPT-5.x via `llmx ... --subscription` (codex-cli, ChatGPT
# subscription = $0) or the llm-dispatch wrapper (governed/logged). Raw `openai` SDK
# calls bill the paid API for zero benefit. Evidence: 2026-06-10 emb-elevation session —
# an eval used `chat.completions.create` + `uv pip install openai` for a paid GPT judge
# when --subscription was free. User flagged it; pair-rule says structural fix = hook.
#
# Scope: ONLY .py files (docs/memories that MENTION openai are exempt). Near-zero false
# positives — grep shows no legitimate raw-OpenAI python anywhere in the stack. Gemini's
# generate_content is deliberately NOT matched (emb/cag.py + contextualize.py use it
# legitimately as library internals; File Search has no llmx wrapper either).

INPUT=$(cat)

read -r FILE CONTENT <<<"$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d) or {}
    fp = ti.get('file_path', '') or ''
    # Write uses 'content'; Edit uses 'new_string'
    body = ti.get('content', ti.get('new_string', '')) or ''
    # emit file_path then a sentinel-free flag of whether body has raw-openai code
    import re
    # Import is the unambiguous gate — you cannot use the SDK without it, and nobody
    # writes 'import openai' in a comment/docstring. Method-call matches (.chat.completions
    # .create / OpenAI() ) were dropped: they appear in prose/examples → false-block risk.
    hit = bool(re.search(r'^\s*(import openai\b|from openai\b)', body, re.M))
    print(fp, '1' if hit else '0')
except Exception:
    print('', '0')
" 2>/dev/null)"

# Only .py files, only when the raw-openai pattern is present
case "$FILE" in
  *.py) ;;
  *) exit 0 ;;
esac
[ "$CONTENT" = "1" ] || exit 0

cat >&2 <<'MSG'
BLOCKED: raw OpenAI SDK in a .py file. This stack routes GPT through llmx, not the paid API:
  • $0 (ChatGPT subscription):  llmx chat -p codex-cli -m gpt-5.5 --subscription ...
  • governed/logged dispatch:   ~/Projects/skills/scripts/llm-dispatch.py --profile gpt_general
The raw `openai` SDK bills the paid API for no benefit (see memory route-model-calls-through-llmx).
Legit exceptions are NOT OpenAI: gemini embeddings/File Search use google.genai directly — those aren't matched.
If you genuinely need the raw SDK, say so explicitly and note why in the file.
MSG
exit 2
