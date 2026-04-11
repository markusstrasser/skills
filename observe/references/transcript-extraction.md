<!-- Reference file for observe skill (shared transcript extraction). Loaded on demand. -->
# Transcript Extraction & Pre-Filtering

## Step 1: Extract Transcripts

Parse the project argument from $ARGUMENTS. Default: last 5 sessions.

```bash
# Claude Code sessions — use --full for session-analyst dispatch (3-5x more content, preserves corrections)
python3 ${CLAUDE_SKILL_DIR}/scripts/extract_transcript.py <project> --sessions <N> --full --output ~/Projects/meta/artifacts/observe/input.md

# Codex CLI sessions (GPT-5.4 via OpenAI) — reads ~/.codex/state_5.sqlite + rollout JSONL.
# MUST write to codex.md (NOT input.md — that would overwrite Claude Code output).
# Codex runs alongside Claude Code on the same project; absence is non-fatal, but
# presence MUST feed the Step 2 dispatch context (never silently dropped).
python3 ${CLAUDE_SKILL_DIR}/scripts/extract_codex_transcript.py <project> --sessions <N> --output ~/Projects/meta/artifacts/observe/codex.md 2>/dev/null || : > ~/Projects/meta/artifacts/observe/codex.md
```

Run BOTH extractors every time. Claude Code is primary; Codex is additive when sessions exist.
Both produce the same markdown format and must BOTH be concatenated into the dispatch context
in Step 2 — never silently drop Codex. It regularly runs genomics work in parallel with Claude
Code, and omitting it loses roughly half the signal. Empty `codex.md` is a valid state (no Codex
sessions in window) and downstream code must tolerate it via `[ -s codex.md ]` guards.

With `--full`: ~80-400KB per 5 sessions (well within Gemini's 1M). Without: ~20-100KB.
Paper evidence: raw traces beat summaries by +15pp for diagnostic quality (Lee et al. 2026).

## Step 1.3: Build Operational Context

Before dispatching to Gemini, build an operational context file with hook triggers, receipts,
and git commits for the analyzed sessions' time window. This gives the analyst the full
operational picture, not just the transcript.

```bash
# Get session time window from extracted transcript
START_TS=$(head -20 ~/Projects/meta/artifacts/observe/input.md | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}' | head -1)
END_TS=$(tail -5 ~/Projects/meta/artifacts/observe/input.md | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}' | tail -1)

{
  echo "# Operational Context"
  echo "## Hook Triggers (session window)"
  jq -r "select(.ts >= \"$START_TS\" and .ts <= \"$END_TS\") | \"\(.ts) \(.hook) \(.action) \(.detail // \"\")\"" \
    ~/.claude/hook-triggers.jsonl 2>/dev/null | tail -50
  echo ""
  echo "## Session Receipts"
  grep -E "$(grep -oE '[a-f0-9]{8}' ~/Projects/meta/artifacts/observe/input.md | head -10 | paste -sd'|')" \
    ~/.claude/session-receipts.jsonl 2>/dev/null
  echo ""
  echo "## Git Commits (session window)"
  git -C "$CWD" log --oneline --since="$START_TS" --until="$END_TS" 2>/dev/null | head -30
} > ~/Projects/meta/artifacts/observe/operational-context.txt
```

## Step 1.5: Build Coverage Context

Before dispatching to Gemini, generate the existing-coverage digest so Gemini doesn't re-report known patterns:

```bash
bash ~/Projects/meta/scripts/coverage-digest.sh > ~/Projects/meta/artifacts/observe/coverage-digest.txt
```

This produces ~2000 tokens of existing finding titles, active hook descriptions, and key rules. Prepend it to the Gemini prompt. Gemini should only report genuinely new patterns not already covered by the digest.

## Shape Pre-Filter (Optional, before Step 2)

Before dispatching to Gemini, check which sessions are structurally anomalous:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/session-shape.py --days 1 --project <project>
```

Focus deep analysis on flagged sessions. Skip sessions with normal structural profiles unless you have specific concerns.
