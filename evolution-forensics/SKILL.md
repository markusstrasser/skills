---
name: evolution-forensics
description: "Longitudinal codebase forensics — tracks concept lifecycles (not just commits), joins sessions to outcomes, measures rule decay and self-improvement velocity, predicts tooling from survival analysis and failure diffusion. The time-series complement to session-analyst (snapshot) and design-review (architecture)."
user-invocable: true
context: fork
argument-hint: "[--days N] [--project PROJECT] [--phase 1|2|3|4] [--quick]"
effort: high
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
  - Agent
---

# Evolution Forensics

Longitudinal analysis of how the codebase *actually evolves*. Tracks concepts through lifecycle states, joins AI sessions to their downstream outcomes, measures which rules decay and which fixes stick, and predicts what tooling to build next.

**session-analyst** sees one session. **design-review** sees workflow patterns. **This skill** sees the trajectory — which corrections stuck, which regressed, which failure classes resist mitigation across weeks.

## Current Environment
`!echo "Date: $(date +%Y-%m-%d) | CWD: $(basename $PWD) | Projects: $(ls ~/Projects/ | wc -l | tr -d ' ') | Improvement-log entries: $(grep -c '^### ' ~/Projects/meta/improvement-log.md 2>/dev/null) | Hook count: $(grep -c '"command"' ~/.claude/settings.json 2>/dev/null)"`

## Argument Parsing

Parse `$ARGUMENTS`:
- `--days N` (default: 14) — lookback window
- `--project PROJECT` — single project focus (default: all of meta, intel, selve, genomics, skills)
- `--phase N` — start from specific phase (for resuming)
- `--quick` — phases 1-2 only, skip prediction

---

## Phase 1: Evolution Index

Data collection — commits, session→commit joins, concept inference. **The index IS the skill. Analysis without evidence is speculation.**

1. **Git history + session attribution** — extract commits with Session-ID trailers across projects. See `references/git-extraction.md`.
2. **Commit classification** — classify each commit as FIX / FIX-OF-FIX / REVERT / FEATURE / RULE / RESEARCH / CHORE. FIX-OF-FIX = file touched by FIX again within 3 days. See `references/commit-classification.md`.
3. **Session→commit→outcome join** — group by Session-ID, check if session's files needed later correction. High correction rate = fragile code. See `references/session-outcome-joins.md`.
4. **Concept lifecycle inference** — infer concepts from git history (don't maintain a manual registry). Track states: RESEARCH → PROTOTYPE → INTEGRATED → PROMOTED / NARROWED / SUPERSEDED / RETIRED. Track typed relationships (implements, replaces, narrows, extends, deprecates). See `references/concept-lifecycle.md`.
5. **Cross-reference sources** — improvement-log, hook triggers, failure modes, vetoed decisions. See `references/git-extraction.md` (Phase 1e section).

**Phase 1 output:** `evolution-index.md`, `session-outcomes.md`, `concept-lifecycle.md`.

---

## Phase 2: Pattern Extraction + Decay Metrics

Instances become classes. Quantitative decay signals surface what's working and what isn't.

1. **Failure patterns** — fix-of-fix chains, session-correlated fragility, build-then-retire, cross-project contagion, concept stalls (PROTOTYPE >7 days).
2. **Rule compliance decay** — for each rule added in the window, compute compliance at day 1/7/14. Half-life <14d = promote to hook. Half-life >30d = instruction is working.
3. **Improvement-log cycle time** — median finding→implemented time, measurement rate, stuck findings (>14d), zombie findings (implemented but never measured).
4. **Reinvention detection** — retired/superseded concepts being rebuilt. High reinvention = retrieval failure, not building failure.
5. **Failure class taxonomy** — group patterns into named classes with evidence, frequency, blast radius, mitigations, gaps.

See `references/pattern-extraction.md` for procedures and output templates, `references/failure-taxonomy.md` for class template.

**Phase 2 output:** analysis integrated into `failure-taxonomy.md`.

---

## Phase 3: Causal Analysis + Survival

Why do mitigations fail? How long do artifacts survive? What predicts durability?

1. **Mitigation failure modes** — classify gaps as COVERAGE_GAP / DECAY / NOVEL / ROUTING_GAP / SEMANTIC.
2. **Artifact survival analysis** — survival stats by type (hook, script, rule, research memo). Test: do artifacts with prior RESEARCH-state concepts survive longer?
3. **Root cause clustering** — cluster failure classes by addressable root cause.

See `references/causal-analysis.md` for categories, templates, and worked examples.

**Phase 3 output:** `causal-analysis.md`.

---

## Phase 4: Predictions

Ranked proposals for what to build next.

1. **Rank by** `frequency × blast_radius × (1 - mitigation_coverage)`.
2. **Veto check** — re-read `vetoed-decisions.md`, drop matches. Check Claude Code native features for coverage.
3. **Final output** — system health metrics, priority actions, deferred proposals, concept lifecycle summary.

See `references/predictions.md` for proposal template and final output format.

**Phase 4 output:** `predictions.md`.

---

## Key Judgment Calls

**When to bail:** If Phase 1 produces <10 commits in the window, the data is too thin. Report "insufficient data" and suggest extending `--days`.

**Rule decay → hook promotion threshold:** Half-life <14 days is the trigger. This directly validates the constitution's "architecture over instructions" principle. Don't promote rules that are working as instructions (half-life >30d).

**Reinvention vs. retrieval:** When you find reinvention events, the fix is surfacing existing things, not building more things. Always frame recommendations this way.

**Concept stalls:** PROTOTYPE >7 days with no commits = dead weight. Recommend retire or integrate, not "keep watching."

**Don't conflate frequency with severity.** Rare catastrophic > frequent trivial. The ranking formula accounts for blast radius, not just count.

## Anti-Patterns

- **Don't maintain a manual concept registry.** Infer from git history and improvement-log. Manual upkeep rots.
- **Don't re-propose vetoed decisions.**
- **Don't count dev effort as cost.** Filter by maintenance burden.
- **Don't fabricate instances.** Every failure class cites a commit hash or improvement-log entry.
- **Don't skip Phase 1.** The index IS the skill.
- **Don't treat reinvention as failure to build.** It's failure to retrieve.
