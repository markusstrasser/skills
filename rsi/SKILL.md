---
name: rsi
description: "Use when: /rsi close, session-end digest nudge, goal achieved + verify one claim. fm.py evidence or one [obs]. NOT deep retro (/observe retro)."
user-invocable: true
argument-hint: close
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: medium
---

# RSI — session close

Thin Tier 1 close for the goal-gated learning loop. Loads this session's close digest,
verifies one principal claim, captures one structural lesson, acks.

**Do not run mid-goal** unless the user explicitly invoked `/rsi close`. SessionEnd
already skipped Tier 1 when goal is still active.

## When to invoke

- User says `/rsi close` or asks for session retrospective with evidence
- SessionStart nudge: "Prior session … has an RSI close digest"
- Goal was achieved this session and digest exists

## Workflow

### 1. Load digest

```bash
uv run --project ~/Projects/agent-infra python3 \
  ~/Projects/agent-infra/scripts/reflect_session_close.py \
  --latest-digest "$(cat .claude/current-session-id 2>/dev/null)"
```

Selects this session's last `reflect.close-digest.v1` row — never a `close-ack.v1`
(acks share the file and dominate the tail; blind `tail -1` returns an ack). An empty
session arg falls back to the latest **un-acked** digest — the SessionStart-nudge case,
where the digest belongs to a prior session.

If exit 1 (no digest): drain the queue, then retry:

```bash
uv run --project ~/Projects/agent-infra python3 \
  ~/Projects/agent-infra/scripts/reflect_session_close.py --drain
```

The drain is fail-loud: it prints `N intents read, M digests written, K skipped (…)`
and exits nonzero on a silent zero. Still no digest after a clean drain → this session
had no Tier-1-eligible close; stop here.

### 2. Verify one load-bearing claim

First read the digest's `real_issue_kinds` + `verify_hint` — they name WHY this close fired and
point the verify at the right claim:
- `unsupported_completion` → **fabrication risk**: re-run the claimed-successful command, confirm the outcome.
- `user_rescued_failure` → verify the fix actually landed (test exit / gate / hash), not the recovery narration.
- `goal_achieved` / `operator_flag` → verify the achievement or what the operator flagged.

Pick ONE claim from the session episode (not the `/goal` Haiku evaluator — that is a proxy):

- Pipeline: `just sample-state`, receipt hash, `_STATUS.json` mtime
- Code: test exit code, `just validate` leaf gate
- Artifact: file hash, `gate_truth` output

Record the command + output snippet. If verification fails, report failure — do not attach evidence.

### 3. Close: structural lesson + ack

The close centers on the Step-2 verify plus ONE durable capture — write the structural
lesson where the next session finds it: a project memory file (+ MEMORY.md pointer), OR
at most **one** `[obs]` line in the project's improvement log / `MAINTAIN.md`. One
destination, not several.

`fm.py attach-evidence` is **optional** — `fm-evidence.jsonl` is auto-fed by the capture
path (~1.7K rows); attach manually ONLY when the verify surfaced novel evidence no
automated row carries:

```bash
cd ~/Projects/agent-infra && uv run python3 scripts/fm.py attach-evidence <FM_ID> \
  --session <SESSION_ID> --quote "<verified fact + command output>"
```

Then ack the digest (stops SessionStart nudge):

```bash
uv run --project ~/Projects/agent-infra python3 \
  ~/Projects/agent-infra/scripts/reflect_session_close.py --ack <SESSION_ID>
```

### 4. Steward proposal (optional, max one)

If a concrete, reversible guard would prevent recurrence:

```bash
# Write to ~/.claude/steward-proposals/YYYY-MM-DD-<slug>.md
# /improve maintain reads these on next tick
```

One proposal max. Prefer attach-evidence over new infrastructure.

## Vetoes

- Never hook Stop for this workflow
- No LLM on SessionEnd (capture is already done)
- Do not trust goal-achieved without independent verification
- Max one `[obs]` OR one steward proposal per close

## Related

- ADR: `agent-infra/decisions/2026-06-15-rsi-session-close-gate.md`
- Capture: `agent-infra/scripts/reflect_capture.py`
- Digest: `agent-infra/scripts/reflect_session_close.py`
- Deep retro: `/observe retro` (manual, heavier)
