# Observe: forensics

Apply [analysis safeguards](analysis-safeguards.md), and [candidate lifecycle](candidate-lifecycle.md) if staging findings. Read the source sessions before judging their downstream outcomes.

Longitudinal analysis of how the codebase actually evolves — concepts through lifecycle states, AI
sessions joined to downstream outcomes, which rules decay and which fixes stick. `retro` sees one
session; `architecture` sees workflow patterns; **forensics sees the trajectory.**

1. **Evolution index** (the index IS the mode; analysis without evidence is speculation): git history
   + session attribution → commit classification FIX / FIX-OF-FIX / REVERT / FEATURE / RULE /
   RESEARCH / CHORE → session→commit→outcome join → concept lifecycle inference RESEARCH → PROTOTYPE
   → INTEGRATED → PROMOTED/NARROWED/SUPERSEDED/RETIRED → cross-reference improvement-log, hook
   triggers, failure modes, vetoed decisions. References: [git-extraction.md](git-extraction.md),
   [commit-classification.md](commit-classification.md), [session-outcome-joins.md](session-outcome-joins.md), [concept-lifecycle.md](concept-lifecycle.md).
2. **Patterns + decay metrics** — fix-of-fix chains, session-correlated fragility, build-then-retire,
   concept stalls (PROTOTYPE >7 days) · rule compliance at day 1/7/14 · improvement-log cycle time
   and zombie findings · **reinvention detection** (a retired concept being rebuilt is a *retrieval*
   failure, not a building failure). [pattern-extraction.md](pattern-extraction.md), [failure-taxonomy.md](failure-taxonomy.md).
3. **Causal + survival** — mitigation failure modes COVERAGE_GAP / DECAY / NOVEL / ROUTING_GAP /
   SEMANTIC ([causal-analysis.md](causal-analysis.md)), artifact survival by type, root-cause clustering.
4. **Predictions** — rank by `frequency × blast_radius × (1 - mitigation_coverage)`, veto-check
   against `vetoed-decisions.md` and Claude Code native features ([predictions.md](predictions.md)).

**Judgment calls:** <10 commits in the window → report "insufficient data", extend `--days` · rule
half-life <14 days → promote to a hook, >30 days → the instruction is working · PROTOTYPE stalled >7
days → retire or integrate · **don't conflate frequency with severity** (rare catastrophic beats
frequent trivial).
