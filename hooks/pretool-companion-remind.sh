#!/usr/bin/env bash
# PreToolUse — remind agent to load mandatory companion skills
# Advisory only (exit 0). Checks tool input for domain signals.
# Tracks reminders per-session to avoid nagging (max 1 per skill per session).

REMINDER_DIR="/tmp/companion-remind-${CLAUDE_SESSION_ID:-default}"
mkdir -p "$REMINDER_DIR" 2>/dev/null

already_reminded() { [ -f "$REMINDER_DIR/$1" ]; }
mark_reminded() { touch "$REMINDER_DIR/$1"; }

remind() {
  local skill="$1" msg="$2"
  if ! already_reminded "$skill"; then
    mark_reminded "$skill"
    echo "[companion] $msg" >&2
  fi
}

INPUT="$CLAUDE_TOOL_INPUT"
TOOL="$CLAUDE_TOOL_NAME"

# Extract command for Bash tools, query for search tools, file path for Write/Edit
CMD=""
QUERY=""
FPATH=""
IS_SEARCH_TOOL=false
if [ "$TOOL" = "Bash" ]; then
  CMD=$(echo "$INPUT" | jq -r '.command // empty' 2>/dev/null)
elif echo "$TOOL" | grep -qE 'mcp__exa|mcp__research|mcp__paper-search|mcp__brave-search|mcp__firecrawl|mcp__perplexity|WebSearch|WebFetch'; then
  QUERY=$(echo "$INPUT" | jq -r '(.query // .search_query // .prompt // .url // .claim // "") | ascii_downcase' 2>/dev/null)
  IS_SEARCH_TOOL=true
elif [ "$TOOL" = "Write" ] || [ "$TOOL" = "Edit" ]; then
  FPATH=$(echo "$INPUT" | jq -r '.file_path // empty' 2>/dev/null)
  # Also grab content for Write, new_string for Edit
  CONTENT=$(echo "$INPUT" | jq -r '(.content // .new_string // "") | .[0:2000]' 2>/dev/null)
fi

# --- Counter-based triggers (fires after N occurrences, not on first) ---
COUNTER_DIR="$REMINDER_DIR/counters"
mkdir -p "$COUNTER_DIR" 2>/dev/null

increment_counter() {
  local name="$1"
  local file="$COUNTER_DIR/$name"
  local count=0
  [ -f "$file" ] && count=$(cat "$file")
  count=$((count + 1))
  echo "$count" > "$file"
  echo "$count"
}

# Track search API calls for researcher skill reminder
if $IS_SEARCH_TOOL; then
  SEARCH_COUNT=$(increment_counter "search-api")
  if [ "$SEARCH_COUNT" -eq 3 ]; then
    remind "researcher" "3+ search API calls this session. Load the researcher skill (/researcher) for routing guidance: S2 for literature (free, structured), Exa for semantic discovery, Brave for triangulation, verify_claim for spot-checks. Axis diversity and phase separation prevent shallow convergence."
  fi
fi

# =============================================================
# HIGH-VALUE companions (clear signal, low false-positive risk)
# =============================================================

# --- llmx-guide: Bash command calls llmx ---
if [ -n "$CMD" ] && echo "$CMD" | grep -q 'llmx'; then
  remind "llmx-guide" "You're calling llmx. Load the llmx-guide skill if you haven't — it has valid model names, flags, and gotchas."
fi

# --- llmx-guide: Python code dispatching to CLI models ---
if [ -n "$CONTENT" ] && echo "$CONTENT" | grep -qE 'subprocess.*(llmx|codex|gemini )|Popen.*(llmx|codex|gemini )'; then
  remind "llmx-guide" "Code dispatches to CLI models. Load llmx-guide for subprocess gotchas (shell=True breaks on parens, output capture, timeouts)."
fi

# --- epistemics: search with bio/medical terms ---
if [ -n "$QUERY" ] && echo "$QUERY" | grep -qiE 'biotech|antiaging|anti-aging|neuroscience|genomic|pharmacogen|supplement|longevity|clinical.trial|drug.target|gene.therapy|CRISPR|mRNA|peptide|nootropic|senolytic|rapamycin|metformin|NAD\+?|telomere|mitochondri|epigenetic|proteom|metabolom|microbiome|statin|GLP.?1|semaglutide|autophagy|senescen|oxidative.stress|inflammation.*marker|blood.brain.barrier'; then
  remind "epistemics" "Bio/medical research detected. Load the epistemics skill — it enforces evidence hierarchy and anti-hallucination rules for health claims."
fi

# --- entity-management: search/write involving entity patterns ---
if [ -n "$QUERY" ]; then
  # Ticker symbols (1-5 uppercase letters, common patterns)
  if echo "$QUERY" | grep -qE '\b(ticker|stock|equity|company|CEO|founder|executive|board.member)\b'; then
    remind "entity-management" "Entity-related search detected. Use /entity-management to create/update structured entity files instead of ad-hoc notes."
  fi
fi
if [ -n "$FPATH" ] && echo "$FPATH" | grep -qiE 'entities/|dossier|profile'; then
  remind "entity-management" "Writing to entity path. Load entity-management skill for schema and versioning conventions."
fi

# --- modal: Bash or code involving Modal ---
if [ -n "$CMD" ] && echo "$CMD" | grep -qE '\bmodal\b.*deploy|\bmodal\b.*run|\bmodal\b.*serve|from modal import|import modal'; then
  remind "modal" "Modal CLI/code detected. Load the modal skill for API gotchas, GPU configs, and v1.0-1.3.x patterns."
fi
if [ -n "$CONTENT" ] && echo "$CONTENT" | grep -qE 'from modal import|import modal|@modal\.(function|cls|method)|modal\.App|modal\.Image|modal\.Volume'; then
  remind "modal" "Modal code detected. Load the modal skill for API gotchas, GPU configs, and v1.0-1.3.x patterns."
fi

# --- skill-authoring: writing a SKILL.md file ---
if [ -n "$FPATH" ] && echo "$FPATH" | grep -qE 'SKILL\.md$'; then
  remind "skill-authoring" "Writing a SKILL.md. Load skill-authoring for frontmatter validation, progressive disclosure, and scope-check conventions."
fi

# --- source-grading: intel-context DuckDB/SQL queries ---
if [ -n "$CMD" ] && echo "$CMD" | grep -qiE 'duckdb|\.sql|SELECT.*FROM.*WHERE' && echo "$CLAUDE_PROJECT_DIR" | grep -qiE 'intel'; then
  remind "source-grading" "SQL query in intel context. Consider source-grading for data provenance — NATO Admiralty grades on source reliability."
fi

# --- perplexity demotion: nudge away from demoted endpoints ---
if echo "$TOOL" | grep -qE 'perplexity_search|perplexity_ask'; then
  remind "perplexity-demoted" "perplexity_search/ask are demoted (5x Exa cost). Use Exa or Brave for breadth queries. Reserve perplexity_reason (complex why) and perplexity_research (deep survey) for decisive use only."
fi

# --- S2 nudge: paper-by-name queries should use Semantic Scholar first ---
if [ -n "$QUERY" ] && echo "$TOOL" | grep -qE 'mcp__exa|mcp__brave|WebSearch'; then
  if echo "$QUERY" | grep -qiE 'paper|arxiv|preprint|et al\.?|icml|neurips|emnlp|acl |iclr|cvpr|aaai|naacl|colm |iccv'; then
    remind "s2-for-papers" "Paper/venue name detected in web search. Use S2 (search_papers) first — free, structured metadata, citation counts, zero hallucinated citations. Fall back to Exa only if S2 misses."
  fi
fi

# --- verify_claim: intel entity/research writes should spot-check claims ---
if [ -n "$FPATH" ] && echo "$CLAUDE_PROJECT_DIR" | grep -qiE 'intel'; then
  if echo "$FPATH" | grep -qiE 'entities/|docs/research/|analysis/'; then
    remind "verify-claims-intel" "Writing intel research/entity file. Use verify_claim to spot-check key financial claims (~\$0.005/call, cached 7d). Cheap insurance against hallucinated numbers."
  fi
fi

# =============================================================
# MEDIUM-VALUE companions (noisier signal, still useful)
# =============================================================

# --- causal-check: "why" analysis in research/analysis contexts ---
if [ -n "$QUERY" ] && echo "$QUERY" | grep -qiE 'why (does|did|do|is|are|was|were|has|have|would|could)\b.*\b(cause|effect|impact|lead|result|driven|because|correlation|associate)'; then
  remind "causal-check" "Causal 'why' question detected in search. Consider loading causal-check to enforce explanatory specificity and prevent factor-listing."
fi

# --- causal-dag + causal-robustness: regression/OLS in code ---
if [ -n "$CONTENT" ] && echo "$CONTENT" | grep -qE 'statsmodels.*OLS|LinearRegression|sm\.OLS|lm\(.*~|regression_results|\.fit\(\).*summary|causal_effect|treatment_effect|ATE\b|ATT\b'; then
  remind "causal-dag" "Regression/causal estimation in code. Load causal-dag to validate DAG structure and adjustment sets before fitting. Follow with causal-robustness for sensitivity analysis."
fi
if [ -n "$CMD" ] && echo "$CMD" | grep -qE 'statsmodels|causal|regression.*ols|dowhy'; then
  remind "causal-dag" "Causal/regression analysis detected. Load causal-dag for DAG validation and causal-robustness for sensitivity (PySensemakr)."
fi

# --- competing-hypotheses: multiple explanations being compared ---
if [ -n "$QUERY" ] && echo "$QUERY" | grep -qiE '(fraud.*(error|mistake|legitimate)|bug.*(design|feature|intentional)|alternative.*(explanation|hypothesis|theor)|competing.*(hypothesis|explanation)|root.cause.*(analysis|investigation)|differential.diagnosis)'; then
  remind "competing-hypotheses" "Multiple competing explanations detected. Load competing-hypotheses (ACH) for structured Bayesian analysis instead of narrative comparison."
fi

# --- data-acquisition: web scraping/download patterns ---
if [ -n "$CMD" ] && echo "$CMD" | grep -qE 'curl_cffi|scrapfly|playwright|browserbase|selenium|requests\.get.*html|beautifulsoup|scrapy'; then
  remind "data-acquisition" "Web scraping code detected. Load data-acquisition for tool selection matrix, fallback chains, and macOS-specific gotchas."
fi
if [ -n "$CONTENT" ] && echo "$CONTENT" | grep -qE 'from curl_cffi|from scrapfly|from playwright|from browserbase|import scrapy|BeautifulSoup|httpx.*scrape'; then
  remind "data-acquisition" "Web scraping imports detected. Load data-acquisition for tool selection, API keys, and authenticated session approaches."
fi

# --- investigate: forensic/OSINT patterns ---
if [ -n "$QUERY" ] && echo "$QUERY" | grep -qiE 'shell.company|beneficial.owner|money.laundering|audit.trail|follow.the.money|OSINT|due.diligence|corporate.registry|UBO|sanctions.screen|related.party|insider.trading|SEC.filing.*fraud|whistleblow'; then
  remind "investigate" "Forensic/OSINT investigation pattern detected. Load the investigate skill for adversarial methodology and cross-domain techniques."
fi

exit 0
