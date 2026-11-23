#!/usr/bin/env bash
# pretool-search-burst.sh — Detect search query bursts without intermediate reads.
# PreToolUse hook. Matcher (settings.json):
#   mcp__exa__.*|mcp__claude_ai_Exa__.*|mcp__research__.*|
#   mcp__firecrawl__.*|mcp__scite__.*|mcp__parallel__.*|WebSearch|WebFetch
# A bare server prefix (mcp__exa) is read as an exact tool name and matches nothing: until
# 2026-11-23 this hook saw WebSearch and WebFetch only.
#
# Search tools add to a per-agent count; tools that consume results clear it. Read, Grep, Glob,
# Write and Edit never reach this matcher group: pretool-universal-dispatch.py clears the count
# for them. At WARN_THRESHOLD the agent gets one advisory. At BLOCK_THRESHOLD one search is
# refused and the count restarts, so the block is a speed bump and never a wall: in Code Mode a
# script reads results in JS with no tool call this hook could see, and a replay of 30 days of
# transcripts showed the old "block until a read" rule refusing 78 searches across 6 agents.
#
# The count is one "s" line per search (appends are atomic; a fan-out script fires searches in
# parallel) plus a "w" line once warned.
#
# No `trap 'exit 0' ERR` — intentional. The trap would swallow exit 2 (the block).
#
# Testing: SEARCH_BURST_COUNTER=/tmp/test-burst bash pretool-search-burst.sh

WARN_THRESHOLD=10
BLOCK_THRESHOLD=30

INPUT=$(cat)

# One counter per calling agent: parallel researcher subagents share the CLI's PID, so a
# $PPID-only counter summed every sibling's searches and let any sibling's Read reset it.
. "$(dirname "$0")/lib_hook_identity.sh" 2>/dev/null || exit 0
hook_identity "$INPUT"
COUNTER_FILE="${SEARCH_BURST_COUNTER:-${CLAUDE_HOOK_STATE_DIR:-/tmp}/claude-search-burst-${HOOK_OWNER}}"

TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")
# The claude.ai Exa connector exposes the same tools under its own server name.
TOOL_NAME="${TOOL_NAME/#mcp__claude_ai_Exa__/mcp__exa__}"

case "$TOOL_NAME" in
    mcp__exa__web_search*|mcp__exa__people_search*|mcp__exa__company_research*|\
    mcp__exa__get_code_context*|\
    mcp__research__search_papers|mcp__research__search_preprints|\
    mcp__scite__search_literature|\
    mcp__parallel__*search*|\
    mcp__firecrawl__firecrawl_search|\
    WebSearch)
        echo "s" >> "$COUNTER_FILE" 2>/dev/null || exit 0
        COUNT=$(grep -c '^s' "$COUNTER_FILE" 2>/dev/null || echo 0)

        if [ "$COUNT" -ge "$BLOCK_THRESHOLD" ]; then
            : > "$COUNTER_FILE" 2>/dev/null
            echo "$COUNT search queries in a row with no tool call that reads a result." >&2
            echo "This one search is refused; the count restarts, so the next goes through." >&2
            echo "Scan what the earlier queries returned, then decide what is still worth asking." >&2
            ~/Projects/skills/hooks/hook-trigger-log.sh "search-burst" "block" "$COUNT queries" 2>/dev/null || true
            exit 2
        elif [ "$COUNT" -ge "$WARN_THRESHOLD" ] && ! grep -q '^w' "$COUNTER_FILE" 2>/dev/null; then
            echo "w" >> "$COUNTER_FILE" 2>/dev/null
            ~/Projects/skills/hooks/hook-trigger-log.sh "search-burst" "warn" "$COUNT queries" 2>/dev/null || true
            jq -n --arg c "$COUNT" --arg b "$BLOCK_THRESHOLD" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: "SEARCH BURST: \($c) search queries in a row with no tool call that reads a result. Earlier results could narrow what you search next; scan them before adding more. One search is refused at \($b)."}}'
        fi
        ;;
    mcp__research__read_paper|mcp__research__fetch_paper|\
    mcp__research__get_paper|mcp__research__ask_papers|\
    mcp__research__get_source|mcp__research__list_corpus|\
    mcp__research__save_paper|mcp__research__save_source|\
    mcp__research__extract_table|mcp__research__prepare_evidence|\
    mcp__firecrawl__firecrawl_scrape|mcp__firecrawl__firecrawl_crawl|\
    mcp__firecrawl__firecrawl_extract|mcp__firecrawl__firecrawl_agent|\
    mcp__firecrawl__firecrawl_map|\
    mcp__exa__crawling_exa|mcp__exa__web_fetch*|mcp__exa__deep_researcher_check|\
    mcp__scite__read_fulltext|\
    mcp__parallel__*extract*|mcp__parallel__*fetch*|\
    WebFetch)
        # Consuming search results — clear the count
        [ -s "$COUNTER_FILE" ] && : > "$COUNTER_FILE" 2>/dev/null
        ;;
    *)
        # Other tools in the matcher group neither count nor clear.
        ;;
esac

exit 0
