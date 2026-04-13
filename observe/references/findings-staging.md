<!-- Reference file for observe skill (sessions mode). Loaded on demand. -->
# Findings Staging & Validation

## Step 3: Stage Findings

1. Read the Gemini output critically -- it may hallucinate session details
2. **Validate session UUIDs (mandatory — run the script):**
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/validate_session_ids.py" --strip
   ```
   This reads `input.md` and `gemini-output.md` from the artifact dir, checks all session ID
   references against the manifest, and exits non-zero if fabrications are found. `--strip`
   replaces fabricated IDs with `[FABRICATED_ID]` in-place. If it flags fabrications, re-examine
   affected findings — the analysis may be valid but misattributed, or entirely hallucinated.
   Include the real UUIDs as `"session_uuids"` in the JSON output (see template below).
3. Cross-check any specific claims against the transcript
4. Stage each validated item as a backlog candidate in `candidates.jsonl` with `state: candidate`
5. Write the human summary to `digest.md`
6. If the item meets promotion criteria, append a promoted candidate record and then write the corresponding improvement-log entry
7. For novel high-severity findings, stage immediately as a candidate and promote without waiting for recurrence
8. Keep state changes append-only. Do not mutate old JSONL lines; write a new record for each state transition.

## Candidate Record Snapshot

```bash
SID=$(cat ~/.claude/current-session-id 2>/dev/null | head -c8 || date +%s | tail -c 8)
cat >> "$OBSERVE_ARTIFACT_ROOT/candidates.jsonl" <<'EOF'
{"schema":"observe.candidate.v1","kind":"session_finding","candidate_id":"candidate_123456789abc","sessions":["uuid-prefix"],"project":"project-name","source_signal_ids":["signal_123456789abc"],"state":"candidate","promoted":false,"recurrence":1,"checkable":true,"priority":"needs-triage","dedupe_status":"unchecked","summary":"Description of the finding","evidence":"Specific evidence from transcript","evidence_anchors":["input.md#session:uuid-prefix"],"severity":"medium","wasted_turn_estimate":2,"likely_fix_surface":"hook","existing_coverage_match":null,"proposed_fix":"hook|skill|rule|CLAUDE.md change|architectural"}
EOF
```
