---
name: rsi
description: "Use when: /rsi close, session-end digest nudge, goal achieved + verify one claim. fm.py evidence or one [obs]. NOT deep retro (/observe retro)."
user-invocable: true
argument-hint: close
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: medium
---

# RSI — session close

Thin Tier 1 close for the goal-gated learning loop. Reads the latest digest from
`~/.claude/reflect-close-digest.jsonl`, verifies one principal claim, attaches evidence.

**Do not run mid-goal** unless the user explicitly invoked `/rsi close`. SessionEnd
already skipped Tier 1 when goal is still active.

## When to invoke

- User says `/rsi close` or asks for session retrospective with evidence
- SessionStart nudge: "Prior session … has an RSI close digest"
- Goal was achieved this session and digest exists

## Workflow

### 1. Load digest

```bash
tail -1 ~/.claude/reflect-close-digest.jsonl | python3 -m json.tool
```

If empty: run drain then retry:

```bash
python3 ~/Projects/agent-infra/scripts/reflect_session_close.py --drain
```

### 2. Verify one load-bearing claim

Pick ONE claim from the session episode (not the `/goal` Haiku evaluator — that is a proxy):

- Pipeline: `just sample-state`, receipt hash, `_STATUS.json` mtime
- Code: test exit code, `just validate` leaf gate
- Artifact: file hash, `gate_truth` output

Record the command + output snippet. If verification fails, report failure — do not attach evidence.

### 3. Attach evidence (max one)

```bash
cd ~/Projects/agent-infra
python3 scripts/fm.py attach-evidence <FM_ID> \
  --session <SESSION_ID> \
  --quote "<verified fact + command output>"
```

If no FM row fits, append at most **one** `[obs]` line to the project's improvement log or
`MAINTAIN.md` — not both.

Then ack the digest (stops SessionStart nudge):

```bash
python3 ~/Projects/agent-infra/scripts/reflect_session_close.py --ack <SESSION_ID>
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
