# Transcript preparation and pre-filtering

Load for a retrospective mode that actually needs transcript extraction. `retro` uses the current
session locally; `harvest` consumes existing producer artifacts. Prefer the size-safe native entry:

```bash
just -f ~/Projects/agent-infra/justfile observe-run <mode> [project] [days]
```

For a manual single-mode run, choose a fresh run artifact directory and use the existing prep script:

```bash
uv run python3 ~/Projects/agent-infra/scripts/observe_prepare_context.py \
  --project P --sessions N --days D --artifact-dir "$ARTIFACT_DIR" --full
```

Drift uses `observe_drift_context.py --sessions 60 --projects … --artifact-dir "$ARTIFACT_DIR"`.
Read `--help` when selecting flags. Do not concatenate raw extractor output into an uncapped blob.
Read the prepared file's byte count and any trim notes; the dispatch cap is 600KB, enforced in code.
For truncation, batch by project or reduce the extraction window. Keep the lost scope explicit in
`manifest.json` and the digest. See [analysis dispatch](analysis-dispatch.md) before sending a bundle.

## Source and coverage contract

Read raw rollout turns for session judgments. Include Claude Code JSONL under
`~/.claude/projects/-Users-alien-Projects-{project}/` and Codex's `~/.codex/state_5.sqlite` + rollout
JSONL matched by cwd. The preprocessor strips thinking and base64. Record every input and every
omission in `manifest.json`; preserve the [artifact contract](artifact-contract.md).

An empty Codex file is valid only when no matching sessions were found. A failed extractor is a
broken source, not evidence of no sessions: inspect return status/stderr and scan/parse/match
denominators before treating empty output as a clean run. Do not suppress failures into empty files.
The prep helpers propagate extractor failures. Healthy empty windows succeed with empty output;
drift retains either source when the other is empty. Neither clipping nor a healthy summary replaces
a raw-source check.

Historical evidence retained from the original workflow: omitting concurrent Codex work lost roughly
half the record; uncapped multitask concatenation produced 10MB contexts. Full raw traces were kept
because summaries miss corrections (the earlier guide cited Lee et al. 2026, +15pp diagnostic quality).

Build operational context for the analyzed time window (hook triggers, receipts, git commits), then
the coverage digest and shape pre-filter below. Weekly full-corpus steer mining uses `just steer-mine`
with incremental state in `~/.claude/steer-mining/`; recent-window runs miss older buried corrections.
The following manual operational-context recipe applies when the native run has not already built it.
Set `OBSERVE_PROJECT_ROOT` to the repo root, `OBSERVE_ARTIFACT_ROOT` to this run directory, and `CWD`
to the analyzed checkout; use manifest timestamps/session IDs if they are already available.

## Step 1.3: Build Operational Context

Before external analysis, build an operational context file with hook triggers, receipts,
and git commits for the analyzed sessions' time window. This gives the analyst the full
operational picture, not just the transcript.

```bash
# Get session time window from extracted transcript
START_TS=$(head -20 "$OBSERVE_ARTIFACT_ROOT/input.md" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}' | head -1)
END_TS=$(tail -5 "$OBSERVE_ARTIFACT_ROOT/input.md" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}' | tail -1)

{
  echo "# Operational Context"
  echo "## Hook Triggers (session window)"
  jq -r "select(.ts >= \"$START_TS\" and .ts <= \"$END_TS\") | \"\(.ts) \(.hook) \(.action) \(.detail // \"\")\"" \
    ~/.claude/hook-triggers.jsonl 2>/dev/null | tail -50
  echo ""
  echo "## Session Receipts"
  grep -E "$(grep -oE '[a-f0-9]{8}' "$OBSERVE_ARTIFACT_ROOT/input.md" | head -10 | paste -sd'|')" \
    ~/.claude/session-receipts.jsonl 2>/dev/null
  echo ""
  echo "## Git Commits (session window)"
  git -C "$CWD" log --oneline --since="$START_TS" --until="$END_TS" 2>/dev/null | head -30
} > "$OBSERVE_ARTIFACT_ROOT/operational-context.txt"
```

## Step 1.5: Build Coverage Context

Before external analysis, generate the existing-coverage digest so Gemini doesn't re-report known patterns:

```bash
bash "$OBSERVE_PROJECT_ROOT/scripts/coverage-digest.sh" > "$OBSERVE_ARTIFACT_ROOT/coverage-digest.txt"
```

This produces ~2000 tokens of existing finding titles, active hook descriptions, and key rules. Include it in the prepared context. The analyst should only report genuinely new patterns not already covered by the digest.

## Shape Pre-Filter (Optional, before Step 2)

Before external analysis, check which sessions are structurally anomalous:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/session-shape.py --days 1 --project <project>
```

Focus deep analysis on flagged sessions. Skip sessions with normal structural profiles unless you have specific concerns.
