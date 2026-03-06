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

# Telemetry log
TELEMETRY_DIR="${HOME}/.claude/hook-telemetry"
mkdir -p "$TELEMETRY_DIR"
TELEMETRY_LOG="${TELEMETRY_DIR}/regression-dag-gate.jsonl"

# Causal/inferential regression patterns (NOT predictive ML like sklearn)
REGRESSION_PATTERNS="ols|OLS|logit|Logit|probit|Probit|sm\.formula|statsmodels|linearmodels|fixedeffects|FixedEffects|PanelOLS|control.for|adjust.for|covariate|sm\.add_constant|RegressionResults|PanelData"

if echo "$CONTENT" | grep -qiE "$REGRESSION_PATTERNS"; then
    MATCHED_PATTERN=$(echo "$CONTENT" | grep -oiE "$REGRESSION_PATTERNS" | head -1)

    # Check if there's evidence of DAG thinking in the content
    DAG_PATTERNS="dag|DAG|causal.graph|back.door|backdoor|adjustment.set|collider|mediator|descendant.of.treatment|causal.dag|pre.treatment|post.treatment"

    if ! echo "$CONTENT" | grep -qiE "$DAG_PATTERNS"; then
        # Log trigger to telemetry
        printf '{"ts":"%s","file":"%s","matched":"%s","fired":true}\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FILE_PATH" "$MATCHED_PATTERN" \
            >> "$TELEMETRY_LOG" 2>/dev/null

        echo "⚠ REGRESSION WITHOUT DAG: This code specifies a regression model but contains no evidence of DAG/causal-graph thinking." >&2
        echo "  Before specifying controls/covariates, consider:" >&2
        echo "  - /causal-dag to construct and validate the causal graph" >&2
        echo "  - dag_check.py to verify adjustment set against back-door criterion" >&2
        echo "  - Classify each control: pre-treatment confounder? mediator? descendant of treatment?" >&2
        echo "  Key risk: descendants of treatment as controls create over-control or collider bias" >&2
    else
        # Matched regression but DAG evidence present — log as suppressed
        printf '{"ts":"%s","file":"%s","matched":"%s","fired":false,"reason":"dag_evidence_found"}\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FILE_PATH" "$MATCHED_PATTERN" \
            >> "$TELEMETRY_LOG" 2>/dev/null
    fi
fi

exit 0
