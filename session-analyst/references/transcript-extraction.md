<!-- Reference file for session-analyst skill. Loaded on demand. -->
# Transcript Extraction & Pre-Filtering

## Step 1: Extract Transcripts

Parse the project argument from $ARGUMENTS. Default: last 5 sessions.

```bash
# Claude Code sessions
python3 ~/Projects/skills/session-analyst/scripts/extract_transcript.py <project> --sessions <N> --output ~/Projects/meta/artifacts/session-analyst/input.md

# Codex CLI sessions (GPT-5.4 via OpenAI) — same interface, reads ~/.codex/state_5.sqlite + rollout JSONL
python3 ~/Projects/skills/session-analyst/scripts/extract_codex_transcript.py <project> --sessions <N> --output ~/Projects/meta/artifacts/session-analyst/input.md
```

Use whichever extractor matches the sessions you want to analyze. Both produce identical markdown format.
Verify the output is reasonable (<100KB, readable markdown).

## Step 1.5: Build Coverage Context

Before dispatching to Gemini, generate the existing-coverage digest so Gemini doesn't re-report known patterns:

```bash
bash ~/Projects/meta/scripts/coverage-digest.sh > ~/Projects/meta/artifacts/session-analyst/coverage-digest.txt
```

This produces ~2000 tokens of existing finding titles, active hook descriptions, and key rules. Prepend it to the Gemini prompt. Gemini should only report genuinely new patterns not already covered by the digest.

## Shape Pre-Filter (Optional, before Step 2)

Before dispatching to Gemini, check which sessions are structurally anomalous:

```bash
uv run python3 ~/Projects/meta/scripts/session-shape.py --days 1 --project <project>
```

Focus deep analysis on flagged sessions. Skip sessions with normal structural profiles unless you have specific concerns.
