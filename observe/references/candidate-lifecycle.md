# Observe candidate lifecycle

Load for candidate staging, backlog draining, or promotion. Record formats and machine gates are in the [artifact contract](artifact-contract.md); the raw source remains the evidence authority.

**Check the dedup baselines before staging.** Read the relevant entries in `improvement-log.md`
and `.claude/rules/vetoed-decisions.md`; a search match locates the entry, not its disposition.
`improvement-log.md` gives TRACKED (implemented → skip,
proposed → mark reinforced, in-progress → skip); `.claude/rules/vetoed-decisions.md` gives VETOED —
never re-propose one without concrete new evidence. Count recurrence by **distinct source type**:
two mentions in one retro is one source, not two.

**Denominator rule (every extractor, every mode).** Each miner reports files scanned, records
parsed, items matched — and the output quotes them. A bare `0 found` is indistinguishable from a
broken parser; the `#f` extractor returned a silent false-zero for months because nothing forced
`matched 0 / parsed 0` into view (fixed skills@837f4d2). `matched 0` with a healthy denominator is
signal. **`parsed 0` is a BROKEN SOURCE** — fix it before trusting the run.

**Two-stream status discipline (F1, `agent-infra/.claude/rules/gov-id.md`).** Pick the glyph by what
the finding *is*, not by habit:

- **Behavioral observation** (TOKEN WASTE, SYCOPHANCY, MISSING PUSHBACK, REASONING-ACTION MISMATCH,
  OVER-ENGINEERING, CAPABILITY ABANDONMENT…) → **`[obs]`**, never `[ ]`. Append-only calibration
  ledger; its consumer is recurrence→rule promotion, not a build. It can never be `[x]`.
- **Actionable infra/tooling/architecture** (a concrete hook/lint/script/rule) → **`[ ]` proposed**.
- Behavioral AND spawning a build → write both, separately.
- **Moot** (subject deleted/eradicated) → `[~] retired — subject no longer exists`. Free drain.

Not pedantry: tagging behavioral findings `[ ]` inflated the actionable-open count from a real ~23
into a 131-item panic number (2026-06-08: 92 of 131 were behavioral, ~13 named eradicated infra).

**Two rankings, because the loop does two jobs.** *New items* = `recurrence × severity × novelty`
(severity 3/2/1; recurrence = distinct source types 1-6; novelty 1.5 new / 1.0 reinforcing / 0.5
tangential). *The drain* = `leverage × staleness`, where leverage is the size of the win (10-100×
friction removed, a failure class closed, dead infra eradicated). **Not** recurrence×severity — the
highest-leverage infra fixes are often single-source (one human finding at a session tail), so the
new-item formula buries them.

**Promotion gate — mandatory before writing `improvement-log.md`:**
`uv run python3 "${CLAUDE_SKILL_DIR}/scripts/observe_gates.py" --artifact-root "$ARTIFACT_DIR" preflight`.
Write entries only for candidates with `verdict=promote` in `promotion-verdicts.jsonl` **and**
`preflight.json → promotions_allowed=true` ([promotion-gates.md](promotion-gates.md)). Criteria: recurs 2+
sessions, not already covered, a checkable predicate or an architectural change. Severity does not
bypass recurrence or any other gate: the [promotion CLI](../scripts/observe_gates.py) runs the
[canonical gate implementation](../scripts/observe_gates_lib.py). Not promotable → leave it in
`candidates.jsonl` with an explicit state; do not force a log entry.

**Recurring classifier false positives** — do not stage these: "unprompted commit" flagged HIGH
(global CLAUDE.md authorizes auto-commit) · `done_with_denials` (a governance approval gate, not a
failure) · "agent paused before executing" when an actual unmet approval gate applies. Check the
user's existing authorization before classifying the pause; an unnecessary repeat request is not
protected by this exemption.

**Promotion sink format** (`improvement-log.md`, only after the gate):

```markdown
### [YYYY-MM-DD] [CATEGORY]: [summary]
- **Session:** [project] [session-id-prefix]      - **Evidence:** [what happened, with excerpts]
- **Failure mode:** [agent-failure-modes.md category, or "NEW"]
- **Proposed fix:** [hook | skill | rule | CLAUDE.md change | architectural]
- **Root cause:** [system-design | agent-capability | task-specification | skill-router | skill-weakness | skill-execution | skill-coverage]
- **Status:** [ ] proposed   ← ONLY for an actionable infra/tooling/architecture build
```

## Queue backpressure

**Backpressure — measured 2026-09-02, not a style choice.** Before minting a steward proposal or a
`decisions-pending/` question, run `just steward-reconcile` / `just questions`: above 40 open
proposals or 40 stale questions the queue is **frozen** — drain first (`just questions-drain
--dispatch`, then `--apply-verdicts <memo>` for the MOOT/SUPERSEDED residue) instead of adding. A
queue nobody drains is the flooding GOALS.md forbids (105 open, 118 stale, zero dispositions in 22 days).

## Harvest and repeat-run safeguards

**Harvest and the loop.** Re-analyzing sessions instead of reading existing artifact output ·
re-proposing vetoed items without concrete new evidence · inflating recurrence (count distinct source
*types*) · skipping dedup — if everything is already tracked, say so · proposing maintenance as
"improvement" (this finds infrastructure/tooling/architecture change) · re-running on the same commit
range — check `docs/audit/sweep-*/` and the run manifest first, run the delta only.
