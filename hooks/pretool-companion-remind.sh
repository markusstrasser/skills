#!/usr/bin/env bash
# PreToolUse — remind agent to load mandatory companion skills
# Advisory only (exit 0). Checks tool input for domain signals.
# Tracks reminders per-session to avoid nagging (max 1 per skill per session).

REMINDER_DIR="/tmp/companion-remind-${CLAUDE_SESSION_ID:-default}"
mkdir -p "$REMINDER_DIR" 2>/dev/null

already_reminded() {
  [ -f "$REMINDER_DIR/$1" ]
}

mark_reminded() {
  touch "$REMINDER_DIR/$1"
}

INPUT="$CLAUDE_TOOL_INPUT"

# --- llmx-guide: any Bash command containing llmx ---
if [ "$CLAUDE_TOOL_NAME" = "Bash" ]; then
  CMD=$(echo "$INPUT" | jq -r '.command // empty' 2>/dev/null)
  if echo "$CMD" | grep -q 'llmx' && ! already_reminded "llmx-guide"; then
    mark_reminded "llmx-guide"
    echo "[companion] You're calling llmx. Load the llmx-guide skill if you haven't — it has valid model names, flags, and gotchas." >&2
  fi
fi

# --- epistemics: search/research tools with bio/medical terms ---
if echo "$CLAUDE_TOOL_NAME" | grep -qE 'mcp__exa|mcp__research|mcp__paper-search|mcp__brave-search|mcp__firecrawl|WebSearch|WebFetch'; then
  QUERY=$(echo "$INPUT" | jq -r '(.query // .search_query // .prompt // .url // "") | ascii_downcase' 2>/dev/null)
  if echo "$QUERY" | grep -qiE 'biotech|antiaging|anti-aging|neuroscience|genomic|pharmacogen|supplement|longevity|clinical.trial|drug.target|gene.therapy|CRISPR|mRNA|peptide|nootropic|senolytic|rapamycin|metformin|NAD|telomere' && ! already_reminded "epistemics"; then
    mark_reminded "epistemics"
    echo "[companion] Bio/medical research detected. Load the epistemics skill — it enforces evidence hierarchy and anti-hallucination rules for health claims." >&2
  fi
fi

exit 0
