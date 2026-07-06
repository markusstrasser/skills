# Improve harvest — per-source protocols (Phase 2 detail)

> Moved verbatim from improve/SKILL.md Phase 2 (2026-07-06, progressive disclosure).
> SKILL.md keeps the source list + one line each; this file is the per-source protocol,
> history, and judgment calls. §2e / §2f / §2i are the detail twins of the inline
> 2b / 2c / 2a entries — external pointers to "harvest Phase 2f" (e.g. trending-scout)
> resolve HERE.

**2d. Legacy artifact dirs** (`artifacts/session-retro/`, `artifacts/design-review/`,
`artifacts/session-analyst/`, `artifacts/suggest-skill/`):
- **Mtime guard first:** `ls -t <dir> | head -1` + stat — if nothing in the window, SKIP the
  dir without reading anything. Do not "read each file" in a dir whose newest artifact
  predates the window (design-review/session-analyst have been static since 2026-04).
- session-retro is semi-live (cursor retro runs). Parse `findings[]` (JSON) / `### [FINDING-`
  (md). design-review: prefer `*-synthesis.md`; skip "Already exists". session-analyst:
  `findings[]` arrays. suggest-skill: candidates with frequency + ROI.
- If a legacy producer wakes up again (fresh artifacts in-window), it's just data — parse it.

**2e. Reflect-loop Quarantine (detail)** (`~/.claude/reflect-quarantine/*.jsonl`):
- The learning loop's deep pass (`just reflect-classify` in agent-infra) emits FM-routed
  enforcer/mint proposals here (status `pending`), each tied to a failure-mode dossier with a
  falsifiable verifier sketch (axis: reach/capability/knowledge/taste). These are already
  deduped against the FM taxonomy and arrive pre-generalized (merge-before-mint), so prefer
  them over raw signals. Enforcers are report-only canaries until a human flips them active.
  Run `just reflect-review` for the ranked view. Do NOT auto-apply — promote into the harvest
  ranking for human disposition only.

**2f. Orphaned research findings (detail)** (`research/trending-scout-*.md` adopt-grade verdicts) —
**this is the CANONICAL finding-routing protocol; other generators (trending-scout Pipeline
step 3, future scouts) reference it, never restate it** (constitution principle 9):
- Harvest's read-path historically EXCLUDED `research/` memos, so trending-scout's
  Adopt/Evaluate/Extract/Act-now verdicts silently bypassed the loop for ~3 months
  (generation-without-consumption; reconciled 2026-06-13). The standing consumer is now
  `just orphan-findings` — it flags any trending memo whose actionable verdicts aren't cited
  in `improvement-log.md` (deterministic memo-cite, report-only, over-reports by design).
- Run `just orphan-findings`. The ratchet is **finding-level** (fixed 2026-06-14): it flags each
  un-routed actionable finding individually, so partial promotion no longer hides siblings. For
  each flagged finding, re-verify against the deferred-feature tracker
  (`research/claude-code-native-features-deferred.md`), git log, and the actual stack. Promote
  ONLY genuinely-live, discrete, undone items to `improvement-log` as `[ ]`, **including the
  finding's title verbatim** (the ratchet clears a finding by matching ≥2 distinctive title
  tokens in the log — a bare memo-path cite no longer clears anything). For a memo whose
  remaining findings are all done-inline / evaluated-rejected / Watch-Extract-study-only /
  N/A-to-stack / owned-elsewhere, add ONE `RECONCILIATION:` entry citing the memo stem (the only
  whole-memo clear). Do NOT inflate the `[ ]` queue with non-actionable items (F1 2026-06-08
  miscount lesson). `doctor.py` surfaces the count daily (`global:orphan-findings`).

**2g. Observe shell-env gate** (`artifacts/observe/*/failures/shell-env-candidate.jsonl`):
- Auto-staged when `zsh-env:*` agentlogs volume ≥50/30d AND `doctor.py` cross-harness shell checks fail.
- Treat as **high-priority infra** — same class as bare-python guard gaps; do NOT leave as `[obs]`.

**2h. Cross-project memory generalization** (`~/.claude/projects/*/memory/*.md` + `~/.codex/memories/`) —
the per-project Claude/Codex memory stores accumulate `feedback`/`reference` lessons learned in ONE
project that are often generalizable to a shared rule/skill/tool. This surface was historically NEVER
read by the loop (generation-without-consumption — lessons sit siloed where learned; measured 2026-06-14:
498 memories, 116 feedback-type, 8 cross-project clusters).
- Run `just memory-harvest` (deterministic pre-filter: `scripts/memory_harvest.py` clusters memories by
  theme, flags ★ CANDIDATE = spans ≥2 projects or ≥5-silo, suggests a factor-out target). It does NOT
  judge generalizability — that semantic step is yours here.
- For each ★ CANDIDATE cluster: **dedup against the suggested target FIRST** (read the global rule / skill
  it points to — most P8/subagent lessons are already covered; do not re-propose). Promote ONLY a lesson
  that is (a) genuinely generalizable (not domain-specific), (b) NOT already in the shared home, (c)
  recurs ≥2 projects OR is a high-value single-project silo whose home is a shared skill. The flagship is
  the **Modal ops** cluster (~37 mems, mostly genomics) → `skills/modal`: future Modal users + sessions
  should inherit budget-kill/volume-path/timeout-extrapolation lessons instead of re-learning at cost.
- Output: a factor-out proposal (lesson → target file) into the harvest ranking. Cross-skill/cross-repo
  factoring is **propose-only** (it edits shared skills 3+ projects consume) → route to the human unless
  the user has directed the factoring. Keyword pre-filter over-matches (e.g. "verify" is noisy); the
  dedup-first step is what keeps the `[ ]` queue honest.

**2i. Blindspot misses (detail)** (`agent-infra/.claude/blindspot-digest.md`) — the RSI loop's
highest-signal source: the moments the human had to CATCH a loop miss (a missed prior
decision, an existing tool, a git-log fact, the wrong approach). Produced daily by the
`com.agent-infra.blindspot-miner` launchd job (emb-contrastive over recent sessions;
`/observe blindspot` re-runs on demand). This is the labeled stream of loop coverage
gaps — converting them to detectors IS the declining-supervision objective.
- Read the digest. Cluster the flags (`emb pairs` over the flagged messages, or by eye).
- For the **top recurring cluster**, the harvest output is a CANDIDATE DETECTOR, not just
  a finding: "*what deterministic check / harness state-injection would have caught this
  class autonomously?*" Rank it high (a recurring blindspot = a standing supervision tax).
- Route: agent-infra-local detector → `improvement-log.md` `[ ]`; shared/irreversible →
  `decisions-pending/`. Dedup against existing hooks FIRST (e.g. prior-context blindness
  partially covered by `inventory-dispatch` at the *dispatch* boundary — propose the
  *propose/diagnose-boundary* extension, don't re-propose the existing hook).
