#!/usr/bin/env bash
# pretool-consensus-search.sh — Warn on epistemically empty search queries.
# PreToolUse hook. Matcher: same as search-burst (search + consumption tools).
# Advisory only (exit 0 + additionalContext). Does not block.
#
# Consensus queries ("best X", "top Y", "most undervalued Z") return noise.
# This hook nudges the agent toward systematic screens with specific criteria.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract the search query from tool input
QUERY=$(echo "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    inp = d.get("tool_input", {})
    # Different tools use different field names
    # Different tools use different field names for the query
    q = inp.get("query", inp.get("instructions", inp.get("companyName", "")))
    # Perplexity uses messages array
    if not q and "messages" in inp:
        msgs = inp["messages"]
        if msgs and isinstance(msgs, list):
            q = msgs[-1].get("content", "")
    print(q)
except Exception:
    print("")
' 2>/dev/null)

[ -z "$QUERY" ] && exit 0

# Check for consensus/noise query patterns (case-insensitive)
if echo "$QUERY" | grep -qiE '\b(best|top [0-9]|most undervalued|most promising|most recommended|most popular|highest rated|leading|hottest)\b'; then
    echo "{\"additionalContext\": \"CONSENSUS SEARCH: Query '${QUERY:0:80}' will return noise, not signal. Consensus queries retrieve popular opinion, not differentiated insight. Consider a systematic screen with specific criteria (market cap range, financial ratios, sector filters) instead.\"}"
fi

exit 0
