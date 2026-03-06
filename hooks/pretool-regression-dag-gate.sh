#!/usr/bin/env bash
# Advisory hook: fires when agent writes Python code containing regression
# patterns without evidence of DAG construction. Reminds about /causal-dag.
#
# Event: PreToolUse (Write, Edit)
# Mode: advisory (exit 0 always, prints STDERR reminder)

set -euo pipefail

# Only fire on Write/Edit to .py files
TOOL_NAME="${CLAUDE_TOOL_NAME:-}"
if [[ "$TOOL_NAME" != "Write" && "$TOOL_NAME" != "Edit" ]]; then
    exit 0
fi

# Read tool input from stdin
INPUT=$(cat)

# Check if the content targets a .py file
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('file_path', d.get('path', '')))
except:
    print('')
" 2>/dev/null)

if [[ "$FILE_PATH" != *.py ]]; then
    exit 0
fi

# Get the content being written/edited
CONTENT=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    # For Write, check content; for Edit, check new_string
    print(d.get('content', d.get('new_string', '')))
except:
    print('')
" 2>/dev/null)

# Check for regression patterns
REGRESSION_PATTERNS="ols|OLS|logit|Logit|probit|Probit|sm\.formula|statsmodels|linearmodels|lm\(|glm\(|regress|LinearRegression|LogisticRegression|sklearn\.linear_model|fixedeffects|FixedEffects|PanelOLS|control.for|adjust.for|covariate"

if echo "$CONTENT" | grep -qiE "$REGRESSION_PATTERNS"; then
    # Check if there's evidence of DAG thinking in the content
    DAG_PATTERNS="dag|DAG|causal.graph|back.door|backdoor|adjustment.set|collider|mediator|descendant.of.treatment|causal.dag|pre.treatment|post.treatment"

    if ! echo "$CONTENT" | grep -qiE "$DAG_PATTERNS"; then
        echo "⚠ REGRESSION WITHOUT DAG: This code specifies a regression model but contains no evidence of DAG/causal-graph thinking." >&2
        echo "  Before specifying controls/covariates, consider:" >&2
        echo "  - /causal-dag to construct and validate the causal graph" >&2
        echo "  - dag_check.py to verify adjustment set against back-door criterion" >&2
        echo "  - Classify each control: pre-treatment confounder? mediator? descendant of treatment?" >&2
        echo "  Key risk: descendants of treatment as controls create collider bias (T3 benchmark: LLMs miss this 92% of the time)" >&2
    fi
fi

exit 0
