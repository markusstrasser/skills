#!/usr/bin/env bash
# posttool-corpus-attest-remind.sh — Advisory: after record_verdict, agent must call corpus_attest.
#
# Architectural enforcement of the substrate v1 cross-project rule (agent-infra/CLAUDE.md
# <cross_project_rules>): every record_verdict MUST be followed by corpus_attest. Sampled
# phenome transcripts (audit 2026-05-15) showed step 2 skipped — the prose-only rule was
# producing the "instructions = 0% reliable" failure mode the constitution warns against.
#
# Matcher (PostToolUse): mcp__phenome__record_verdict|mcp__intel-theses__record_verdict
# Advisory only (additionalContext). Escalate to Stop-blocking after 14d of telemetry
# if compliance doesn't improve.

trap 'exit 0' ERR

INPUT=$(cat)

PARSED=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tool_name = data.get('tool_name', '')
    parts = tool_name.split('__')
    repo = parts[1] if len(parts) >= 3 else ''
    if repo.endswith('-theses'):
        repo = repo[:-7]
    elif repo.endswith('-mcp'):
        repo = repo[:-4]
    result = data.get('tool_response') or data.get('tool_result') or {}
    if isinstance(result, str):
        try: result = json.loads(result)
        except: result = {}
    verdict_id = ''
    if isinstance(result, dict):
        verdict_id = result.get('verdict_id') or result.get('id') or ''
    claim_id = ''
    ti = data.get('tool_input', {})
    if isinstance(ti, dict):
        claim_id = ti.get('claim_id', '')
    print(f'{repo}|{verdict_id}|{claim_id}')
except Exception:
    print('||')
" 2>/dev/null || echo "||")

REPO=$(echo "$PARSED" | cut -d'|' -f1)
VERDICT_ID=$(echo "$PARSED" | cut -d'|' -f2)
CLAIM_ID=$(echo "$PARSED" | cut -d'|' -f3)

[ -z "$REPO" ] && exit 0

~/Projects/skills/hooks/hook-trigger-log.sh "corpus-attest-remind" "advise" "${REPO}:${VERDICT_ID:-pending}" 2>/dev/null || true

if [ -n "$VERDICT_ID" ]; then
    OUTPUT_URI="${REPO}://verdicts/${VERDICT_ID}"
else
    OUTPUT_URI="${REPO}://verdicts/<verdict_id from this response>"
fi

cat <<JSON
{"additionalContext": "SUBSTRATE V1 — corpus_attest required next.\n\nThe record_verdict call above is step 1 of the 2-call ritual. Now call:\n\n  mcp__corpus__corpus_attest(\n      source_id=...,                    # the source the verdict is about\n      repo=\"${REPO}\",\n      actor_type=\"model\" | \"human\",\n      actor_id=...,                     # session id or human name\n      scope=\"verdict\",\n      output_uri=\"${OUTPUT_URI}\",\n      output_hash=...,                  # sha256 of the verdict payload\n  )\n\nClaim id: ${CLAIM_ID:-<from record_verdict input>}.\n\nWhy: agent-infra/CLAUDE.md <cross_project_rules>. Skipping leaves provenance incomplete; the daily audit-corpus-sync job will flag it within 24h."}
JSON
exit 0
