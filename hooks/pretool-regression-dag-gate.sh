#!/usr/bin/env bash
# Advisory hook: fires when agent writes Python code containing regression
# patterns without evidence of DAG construction. Reminds about /analyze dag.
#
# Event: PreToolUse (Write, Edit)
# Mode: advisory (exit 0 always, prints the reminder as additionalContext)

set -euo pipefail

# Read tool input from stdin (Claude Code sets no CLAUDE_TOOL_* env vars)
INPUT="${CLAUDE_TOOL_INPUT:-$(cat)}"

# Derive tool_name from the input envelope
TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")

# Only fire on Write/Edit to .py files
if [[ "$TOOL_NAME" != "Write" && "$TOOL_NAME" != "Edit" ]]; then
    exit 0
fi

# Check if the content targets a .py file
FILE_PATH=$(printf '%s' "$INPUT" | jq -r '(if has("tool_input") then (.tool_input // {}) else . end) | if has("file_path") then (.file_path // "") else (.path // "") end' 2>/dev/null || echo "")

if [[ "$FILE_PATH" != *.py ]]; then
    exit 0
fi

# Get the content being written/edited
# For Write, check content; for Edit, check new_string
CONTENT=$(printf '%s' "$INPUT" | jq -r '(if has("tool_input") then (.tool_input // {}) else . end) | if has("content") then (.content // "") else (.new_string // "") end' 2>/dev/null || echo "")

# Telemetry log
TELEMETRY_DIR="${HOME}/.claude/hook-telemetry"
mkdir -p "$TELEMETRY_DIR"
TELEMETRY_LOG="${TELEMETRY_DIR}/regression-dag-gate.jsonl"

# Causal/inferential regression patterns (NOT predictive ML like sklearn)
REGRESSION_PATTERNS="ols|OLS|logit|Logit|probit|Probit|sm\.formula|statsmodels|linearmodels|fixedeffects|FixedEffects|PanelOLS|control.for|adjust.for|covariate|sm\.add_constant|RegressionResults|PanelData"

# -w: whole words only. As a substring, "ols" matched "tools" and "logit" matched "logits":
# 3,285 of the 3,382 fires in the 30 days to 2026-11-23 (hook-telemetry/regression-dag-gate.jsonl).
if echo "$CONTENT" | grep -qiwE "$REGRESSION_PATTERNS"; then
    MATCHED_PATTERN=$(echo "$CONTENT" | grep -oiwE "$REGRESSION_PATTERNS" | head -1)

    # Check if there's evidence of DAG thinking in the content
    DAG_PATTERNS="dag|DAG|causal.graph|back.door|backdoor|adjustment.set|collider|mediator|descendant.of.treatment|causal.dag|pre.treatment|post.treatment"

    if ! echo "$CONTENT" | grep -qiE "$DAG_PATTERNS"; then
        # Log trigger to telemetry
        printf '{"ts":"%s","file":"%s","matched":"%s","fired":true}\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FILE_PATH" "$MATCHED_PATTERN" \
            >> "$TELEMETRY_LOG" 2>/dev/null

        # Claude never sees stderr from a hook that exits 0: collect the lines and print them as context.
        {
        echo "⚠ REGRESSION WITHOUT DAG: This code specifies a regression model but contains no evidence of DAG/causal-graph thinking." >&2
        echo "  Before specifying controls/covariates, consider:" >&2
        echo "  - /analyze dag to construct and validate the causal graph" >&2
        echo "  - dag_check.py to verify adjustment set against back-door criterion" >&2
        echo "  - Classify each control: pre-treatment confounder? mediator? descendant of treatment?" >&2
        echo "  Key risk: descendants of treatment as controls create over-control or collider bias" >&2
        } 2>&1 | jq -Rs '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: (. | gsub("^\\s+|\\s+$"; ""))}}'
    else
        # Matched regression but DAG evidence present — log as suppressed
        printf '{"ts":"%s","file":"%s","matched":"%s","fired":false,"reason":"dag_evidence_found"}\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FILE_PATH" "$MATCHED_PATTERN" \
            >> "$TELEMETRY_LOG" 2>/dev/null
    fi
fi

exit 0
