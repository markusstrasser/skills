#!/usr/bin/env bash
# pretool-search-burst.sh — Detect search query bursts without intermediate reads.
# PreToolUse hook. Matcher: mcp__exa|mcp__research|mcp__paper-search|WebSearch|WebFetch
# Fires on search tools (increment) and result-consumption tools (reset).
# Advisory only: warns after threshold, never blocks.

trap 'exit 0' ERR

COUNTER_FILE="/tmp/claude-search-burst-${PPID:-0}"
THRESHOLD=6

INPUT=$(cat)

# Extract tool name from PreToolUse input
TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_name', ''))
except:
    print('')
" 2>/dev/null)

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

        if [ "$COUNT" -ge "$THRESHOLD" ]; then
            echo "NOTE: $COUNT search queries fired without pausing to read results." >&2
            echo "Results from earlier queries could narrow what you search next." >&2
            echo "Consider reading/scanning what you have before adding more." >&2
            # Don't reset — let it keep counting so the message persists
        fi
        ;;
    mcp__research__read_paper|mcp__research__fetch_paper|\
    mcp__research__get_paper|mcp__research__ask_papers|\
    mcp__paper-search__read_*|mcp__paper-search__download_*|\
    WebFetch)
        # Consuming search results — reset counter
        echo "0" > "$COUNTER_FILE" 2>/dev/null
        ;;
    *)
        # Other tools — don't reset (writing, editing, etc. aren't "reading results")
        ;;
esac

exit 0
