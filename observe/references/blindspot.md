# Observe: blindspot

Read the existing miner output before re-extracting. Use [candidate lifecycle](candidate-lifecycle.md) before staging a detector or requesting its approval.

**"What did the loop MISS that the human had to catch?"** — the RSI signal. Every time the human
reproaches or corrects the agent for missing something it should have caught (a prior decision, an
existing tool, a git-log fact, the right approach), that is a labeled example of a loop coverage
gap. The objective (Constitution: *declining supervision*) is to drive the RATE toward zero by
converting each recurring cluster into a **detector**. (Markus, 2026-06-14: *"every time I mention
something, ask why the loop didn't find it, and metaimprove a way for the next loop to find stuff
like it."*)

`failures` finds broken *tools*; `supervision` audits wasted *human time* broadly; `blindspot` is
the sharp cut — the human catching a loop miss — and it feeds the CONVERT step in `maintain`.
Run `just -f ~/Projects/agent-infra/justfile blindspot`; the launchd tick runs it daily.

**Why not regex or fuzzy matching:** the distinction is *pragmatic* (is the human reproaching a
miss?), not topical. "Did you check the git log" and "can you check the tests" are topically
identical and pragmatically opposite. Measured (improvement-log 2026-06-14): regex 43% recall; fuzzy
hits a lexical ceiling; emb-contrastive (blind-centroid minus normal-centroid) is the only method
catching semantic paraphrases at precision.

**CONVERT (the loop closure).** Cluster the flagged messages with `emb pairs`. For the **top
recurring cluster** ask: *what deterministic check or state-injection would have caught this
autonomously?* Dedup against existing hooks first, then route the proposed detector to
`improvement-log.md` `[ ]` (agent-infra-local) or `decisions-pending/` (shared/irreversible). The
blindspot-flag rate is the pre-registered success metric — it should fall as detectors land.
