#!/bin/bash
# epistemics-remind.sh — Advisory PreToolUse hook for selve
# Fires on web search tools when query contains bio/medical keywords.
# Reminds agent to invoke /epistemics companion skill.

trap 'exit 0' ERR

INPUT=$(cat)

echo "$INPUT" | python3 -c "
import sys, json, re

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool = data.get('tool_name', '')
# Only fire on search tools
search_tools = ('web_search', 'brave', 'perplexity', 'exa', 'search_papers', 'search_preprints')
if not any(t in tool.lower() for t in search_tools):
    sys.exit(0)

# Check tool input for bio/medical keywords
params = json.dumps(data.get('tool_input', {})).lower()
keywords = r'biotech|drug|gene\b|clinical|supplement|aging|anti.?aging|neuroscience|medical|pharma|genomic|health|vitamin|peptide|hormone|longevity|nootropic|dosage|receptor|pathway|enzyme|protein|variant|allele|snp|gwas'
if re.search(keywords, params):
    output = {
        'decision': 'allow',
        'additionalContext': 'Bio/medical search detected. Invoke /epistemics if not already active.'
    }
    print(json.dumps(output))
" 2>/dev/null

exit 0
