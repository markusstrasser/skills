# Model-guide validation checklists (post-output, per model)

> Moved verbatim from model-guide/SKILL.md (2026-07-06, progressive disclosure).
> Consult AFTER receiving output from a routed model — these are post-hoc verification
> lists, not routing input. Update alongside any system-card digest change.

## Validation Checklists

### All Outputs
- [ ] Verify current facts, prices, names, laws, schedules, and claims with source tools.
- [ ] Verify code completion with tests, type checks, lint, git diff, and actual runtime state.
- [ ] Treat reasoning traces as diagnostics, not proof.
- [ ] For "nothing found" or "done" claims, prefer deterministic null checks over model confidence.

### After Claude Fable 5 (paid opt-in — llmx/headless lanes only, not Agent tool; see SKILL.md Verified Transport)
- [ ] Bind completion to parsed evidence — Fable regresses slightly vs Opus 4.8 on self-report honesty.
- [ ] Treat unsourced factual specifics as unverified: 55% of its closed-book misses are confident fabrications even when invited to abstain (AA-Omniscience non-hallucination 45% vs Opus 64%).
- [ ] Confirm it didn't take an unrequested action (drafted email, backup branch) or execute a guessed command without checking.
- [ ] Check it surfaced defects as mistakes, not reframed them as "design decisions."
- [ ] Watch for `stop_reason:"refusal"` and confirm fallback to Opus 4.8 fired where expected.
- [ ] Keep prompt-injection boundaries around tool outputs.

### After Claude Sonnet 5
- [ ] Bind completion to parsed evidence — disclosed training-health issue + highest abstention rate of compared models on closed-book recall (AA-Omniscience) are reasons for slightly less trust in self-report than usual.
- [ ] Watch for prefill/system-prompt-susceptibility — numerically the weakest of the compared models on this axis (absolute rates still low).
- [ ] If the dispatch is architecture/design/high-reasoning critique, don't route here — that verdict hasn't been revisited for Sonnet 5 (see OPEN QUESTION).
- [ ] On long agentic loops, check actual turn/token count against Opus 4.8 before assuming the lower $/token wins on $/task — Sonnet 5 runs more turns on long-horizon work in its own benchmarks.
- [ ] Keep prompt-injection boundaries around tool outputs (though Sonnet 5 measures strongest-in-class here).

### After Claude Opus 5.5
- [ ] Confirm the served model when it matters: the `opus` alias moved to `claude-opus-5-5` on 2026-09-22; exact-ID lanes still serve Opus 5.
- [ ] Check that computed numbers came from executed code or the required tool; answering tool-required tasks from memory is its one reward-hack subclass above Mythos 5.1 (card §6.2.1).
- [ ] For research or synthesis output, check the effort it ran at: `low` collapses on research (DRACO 72.5, WANDR 31.2).
- [ ] If it relayed a user approval to a subagent or acted on one, find the user message that grants it (card §6.3.1: rare overclaiming of user intent; more acceptance of unverifiable authorization claims).
- [ ] If the input contained pasted third-party text, confirm it did not act on instructions inside it (card §6.5.1).
- [ ] On contested political or social questions, check that the strongest opposing case is stated in full rather than offered for later (API opposing-perspectives rate 26.9%).
- [ ] After a stance change under pushback, check that new evidence was named (MASK honesty 87.4% vs Opus 5 94.8%).
- [ ] Cyber or dual-use biology refusals: re-run on `claude-opus-5` by exact ID; `reasoning_extraction` refusals do not fall back.

### After Claude Opus 4.8
- [ ] Check math and quantitative derivations, especially if not tool-backed.
- [ ] Best-calibrated frontier model measured (AA-Omniscience non-hallucination 64%) — appropriate as monitor, but it still fabricates on a third of its misses; sources still required.
- [ ] Watch over-abstention on answerable questions.
- [ ] Bind completion to parsed evidence, not the model's own progress summary.
- [ ] Keep prompt-injection boundaries around tool outputs.

### After GPT-5.6 Sol/Terra
- [ ] Check that it did not take action when the user only asked a question.
- [ ] Treat every unsourced factual specific as unverified-by-default: 86% of its closed-book misses are confident fabrications even when explicitly invited to abstain (AA-Omniscience non-hallucination 14% — worst of the frontier set). Weight its critiques by their reasoning, never their asserted facts.
- [ ] Check that it preserved pre-existing user/worktree changes.
- [ ] For impossible or intentionally blocked tasks, verify it admitted the block instead of pretending success.
- [ ] Fact-check dense professional prose; improved factuality is not source-grade accuracy.

### After GPT-5.6 Sol (pro mode)
- [ ] Verify every intermediate quantitative step.
- [ ] Re-run decisive calculations with code or a second model.
- [ ] Make sure the task justified pro-mode token spend on Sol.

### After GLM-5.2 (opt-in review)
- [ ] Best measured calibration among large routed models (72% non-hallucination on AA-Omniscience misses) — still verify novel specifics; abstention is better, not perfect.
- [ ] Expensive by structure (`high`/`xhigh` only); don't promote to default cosigner or extractor without `evals/critique_replay` measurement.
- [ ] Weight its reasoning on impossibility/contradiction flags; don't treat its factual recall as ground truth without sources.

### After Grok 4.7 (repo-grounded critique / Cursor pool / agentic niche)
- [ ] Confirm preflight passed exact registry slug `grok-4.7-high` (no `cursor-` prefix) and the unrevealed repo-HEAD canary. 4.5 AA calibration below is not a 4.7 measurement.
- [ ] Confirm transport was `cursor-agent --mode ask --workspace` for critique (receipt `transport: cursor-agent-workspace`) — not llmx packet-only cursor.
- [ ] Re-run 1–2 of its load-bearing greps yourself; weight reasoning, not asserted facts (~46% AA-Omniscience non-hallucination).
- [ ] Do not treat CursorBench / vendor coding scores as decisive (Cursor blog: training contamination).
- [ ] Hard physics / CritPt-shaped claims: distrust — AA CritPt 15%; escalate to GPT-5.6 Sol max/pro.
- [ ] If xAI API path was attempted: 403 `API key is currently blocked` is a **key** problem, not EU geo.
