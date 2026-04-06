#!/usr/bin/env bash
# pretool-exa-context-guard.sh — Advisory guard on Exa advanced search
# PreToolUse:mcp__exa__web_search_advanced_exa command hook.
#
# Warns when contextMaxCharacters is unset on broad queries (no includeDomains).
# Broad Exa queries without context limits return 100K-200K chars, triggering
# temp file saves that are unusable. 3+ confirmed incidents.

trap 'exit 0' ERR

INPUT="$CLAUDE_TOOL_INPUT"

# Parse with Python — check for contextMaxCharacters and includeDomains
RESULT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    tool_input = d if isinstance(d, dict) else d.get('tool_input', {})
    has_context_limit = 'contextMaxCharacters' in tool_input
    has_domain_filter = bool(tool_input.get('includeDomains'))
    has_category = bool(tool_input.get('category'))
    num_results = tool_input.get('numResults', 10)

    # Only warn if: no context limit AND no domain filter AND requesting many results
    if not has_context_limit and not has_domain_filter and not has_category and num_results >= 5:
        print('WARN')
    else:
        print('OK')
except:
    print('OK')
" 2>/dev/null)

if [ "$RESULT" = "WARN" ]; then
    echo '{"decision": "allow", "additionalContext": "⚠ Exa broad query without contextMaxCharacters — results may exceed 100K chars and get saved to a temp file you cannot use. Add contextMaxCharacters: 2000-3000 for broad searches. Only omit for narrow/domain-filtered queries."}'
fi

exit 0
