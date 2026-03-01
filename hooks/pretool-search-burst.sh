#!/usr/bin/env bash
# pretool-search-burst.sh — Detect search query bursts without intermediate reads.
# PreToolUse hook. Matcher: mcp__exa|mcp__research|mcp__paper-search|WebSearch|WebFetch
# Fires on search tools (increment) and result-consumption tools (reset).
# Warns at WARN_THRESHOLD, soft-blocks at BLOCK_THRESHOLD.
#
# No `trap 'exit 0' ERR` — intentional. The trap would swallow exit 2 (the block).
# All non-blocking paths exit 0 explicitly: python fallback via `|| echo ""`,
# case `*` falls through, script ends with `exit 0`.
#
# Testing: SEARCH_BURST_COUNTER=/tmp/test-burst bash pretool-search-burst.sh

COUNTER_FILE="${SEARCH_BURST_COUNTER:-/tmp/claude-search-burst-${PPID:-0}}"
WARN_THRESHOLD=4
BLOCK_THRESHOLD=8

INPUT=$(cat)

# Extract tool name from PreToolUse input
TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_name', ''))
except:
    print('')
" 2>/dev/null || echo "")

# Classify: is this a search tool?
case "$TOOL_NAME" in
    mcp__exa__web_search_exa|mcp__exa__web_search_advanced_exa|\
    mcp__exa__company_research_exa|mcp__exa__get_code_context_exa|\
    mcp__research__search_papers|\
    mcp__paper-search__search_arxiv|mcp__paper-search__search_pubmed|\
    mcp__paper-search__search_biorxiv|mcp__paper-search__search_medrxiv|\
    mcp__paper-search__search_google_scholar|\
    WebSearch)
        # Search tool — increment counter
        COUNT=0
        [ -f "$COUNTER_FILE" ] && COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
        COUNT=$((COUNT + 1))
        echo "$COUNT" > "$COUNTER_FILE"

        if [ "$COUNT" -ge "$BLOCK_THRESHOLD" ]; then
            echo "$COUNT consecutive search queries without reading results." >&2
            echo "Earlier results should inform what you search next." >&2
            echo "Read/scan existing results before adding more queries." >&2
            exit 2
        elif [ "$COUNT" -ge "$WARN_THRESHOLD" ]; then
            echo "NOTE: $COUNT search queries fired without pausing to read results." >&2
            echo "Results from earlier queries could narrow what you search next." >&2
            echo "Consider reading/scanning what you have before adding more." >&2
        fi
        ;;
    mcp__research__read_paper|mcp__research__fetch_paper|\
    mcp__research__get_paper|mcp__research__ask_papers|\
    mcp__paper-search__read_*|mcp__paper-search__download_*|\
    WebFetch)
        # Consuming search results — reset counter
        echo "0" > "$COUNTER_FILE" 2>/dev/null
        ;;
    Read|Grep|Glob|mcp__exa__crawling_exa|mcp__exa__deep_researcher_check|\
    mcp__research__get_source|mcp__research__list_corpus|\
    mcp__research__save_paper|mcp__research__save_source)
        # Processing results — reset counter
        echo "0" > "$COUNTER_FILE" 2>/dev/null
        ;;
    *)
        # Other tools — don't reset (writing, editing, etc. aren't "reading results")
        ;;
esac

exit 0
