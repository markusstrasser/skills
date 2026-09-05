# Observe: retro

This workflow stays local. Read [candidate lifecycle](candidate-lifecycle.md) only if staging or promoting beyond the local retrospective artifact; no bulk preparation or model review is needed.

End-of-session retrospective. **Local only — no dispatch.** Classification and template in
[retro-reflection.md](../lenses/retro-reflection.md).

**CAPTURE, don't fix.** *Append* findings — do not implement fixes in the moment. Fixing at session
end is the fix-spiral trap (~15 turns lost optimizing one script at a tail by guessing instead of
measuring). Actionable `[ ]` items get batched and human-dispositioned by `harvest` + `maintain`.

**Phase 0 — idempotency.** Check `artifacts/session-retro/` for `$(date +%F)-${SID}-*.json`; if any
exist and `--force` was not passed, report "already retro'd" and **stop**. Five retros on one session
were observed, each adding zero new findings after the second.

**Phase 1 — evidence.** Scan THIS session for concrete events: failures (commands that errored,
tools that returned wrong results, approaches abandoned) · corrections (where the user redirected
you, what they said, what you were doing wrong) · wasted work (code written then deleted, searches
that found nothing, repeated attempts) · environment friction (missing deps, wrong paths, hook
blocks, rate limits) · time sinks · and **agent self-process anti-patterns, the lens nothing else
captures.** Be honest about your OWN failures, not just the environment's: guessing a cause before
measuring it, fix-spirals, thrash loops on one target, `--no-verify` as an escape hatch, long edit
churn on one file, collapsing a general ask to a narrow case. Much of this is deterministic from
agentlogs — repeated identical failed `tool_calls`, `--no-verify` in commit args, N edits to one
path — so **mine it, don't just introspect**.

**Phases 2-5.** Classify into exactly one category · check prior art (`candidates.jsonl` first, then
`grep improvement-log.md` for already-promoted parallels → "RECURRING: matches YYYY-MM-DD"; check
whether a hook/rule/skill already covers it) · write
`artifacts/session-retro/{date}-{SID}-manual.json`:

```json
{"findings": [{"category": "…", "summary": "…", "severity": "high|medium|low",
               "evidence": "…", "project": "…", "proposed_fix": "…"}], "source": "manual-retro"}
```
