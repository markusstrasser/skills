<!-- Reference file for session-analyst skill. Loaded on demand. -->
# Findings Staging & Validation

## Step 3: Stage Findings

1. Read the Gemini output critically -- it may hallucinate session details
2. **Validate session UUIDs (mandatory, automated):**
   - The input.md starts with a "VALID SESSION IDS" table. Extract the prefix column.
   - Grep the Gemini output for any 8-char hex patterns (`[0-9a-f]{8}`).
   - **Reject** any finding whose session ID does not match a prefix from the table.
   - If Gemini returns IDs like `019d4xxx` that aren't in the table, they are fabricated (2 confirmed incidents: 2026-04-03, 2026-04-05).
   - Include the real UUIDs as `"session_uuids"` in the JSON output (see template below).
3. Cross-check any specific claims against the transcript
4. For findings that meet promotion criteria (recurs 2+ sessions, not already covered, checkable predicate or architectural), append directly to `~/Projects/meta/improvement-log.md` using the improvement-log output format
5. For novel high-severity findings, also append directly (don't wait for recurrence)
6. Save raw findings as JSON for the session-retro pipeline artifact trail:

```bash
SID=$(cat ~/.claude/current-session-id 2>/dev/null | head -c8 || date +%s | tail -c 8)
cat > ~/Projects/meta/artifacts/session-analyst/$(date +%Y-%m-%d)-${SID}-findings.json << 'EOF'
{
  "findings": [
    {
      "category": "TOKEN WASTE",
      "summary": "Description of the finding",
      "severity": "medium",
      "evidence": "Specific evidence from transcript",
      "root_cause": "system-design|agent-capability|task-specification",
      "proposed_fix": "hook|skill|rule|CLAUDE.md change|architectural",
      "session_uuid": "uuid-prefix",
      "project": "project-name"
    }
  ],
  "session_uuids": ["uuid1-from-input.md", "uuid2-from-input.md"],
  "sessions_analyzed": 5,
  "actionable_count": 3
}
EOF
```
