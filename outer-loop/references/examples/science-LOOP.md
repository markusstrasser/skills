---
loop:
  repo: science                     # the genomics/phenome research domain (synthesis + discovery)
  outer_loop_skill:
    name: outer-loop
    version: 2026-06-13
    expected_schema: 1

verifier:
  regime: partial                   # synthesis/gap/discovery has NO ground truth — generate-only unattended

schedule:
  driver: "dispatched BY /improve maintain (the conductor) on its research rotation; or launchd claude -p '/research-ops cycle' for Lane A; or /loop /research-ops cycle by hand"
  noop_on: queue-healthy            # queue ≥8 unused proposals AND no fresh STEER/quality signal AND decisions-pending empty
  lock: null
  # NOTE: science is NOT a standalone conductor. Since the 2026-06-12 three-conductor merge, the single
  # RSI-loop conductor is /improve maintain; this loop is the research-domain WORKER it dispatches. So
  # science's DEPLOY (driving it via the outer-loop skill) is coupled to the conductor migration (plan
  # Phase 3), not independent. This contract is the partial-regime REFERENCE instance + the route.py
  # partial-fix proof; it is not yet science's live driver.

proposer:
  skills: [leverage, brainstorm, research, critique]   # leverage missing/generators; research = SOTA sweep
  dedup_against: [git-log, research-memos]              # no ledger view; dedup vs git history + memos
  max_per_fire: 8
  sota_sweep: every-fire             # science standing rule: newest validated papers (search_preprints +
                                     # traverse_citations since last fire) + newest tools (/trending-scout)

bus:
  ledger: CYCLE.md                  # git-native (see ledger.kind) — the fire log, not a table
  queue: queue/
  human_queue: decisions-pending/
  flags: []                         # no inner-loop flag files; the conductor's signals drive refill
  discovery_flags: null             # the "never autonomous" set goes straight to decisions-pending/

accept_gate:
  cmd: "research-ops cycle Lane B Verify — Track B: extract 3-5 falsifiable claims (numbers/dates/entities/causal) → verify_claim each"
  verdict_field: verify_verdict
  accept_verdicts: [VERIFIED, PASS]
  error_verdicts: [CONTRADICTED]    # any claim contradicted >0.7 confidence → FAIL → archive + git revert
  independence: differential        # claims checked against EXTERNAL sources (verify_claim/Exa), decorrelated
  gate_version: null
  budget: null
  # TRACE-ISOMORPHIC ENHANCEMENT (from the /eval survey, 2026-06-13): the current gate verifies extracted
  # CLAIMS against external sources (strong — decomposes to falsifiable checks, anti-Goodhart). A further
  # upgrade is to grade the evidence TRACE (were the claims grounded in sources actually retrieved/traversed,
  # phenome's KG-verifier audit pattern) — structure-checking verifiers block reward-hacking that output/claim
  # checking alone can miss (evals/research/2026-06-13-frontier-agentic.md §B; arXiv:2604.15149). Recommended
  # for the science gate; not built in Phase 2 (the claim-verification gate is already consumed + decomposed).

ledger:
  kind: git-native                  # the attempt graph IS git history; failures → artifacts/failed-experiments/
                                    # *.json (gap-fingerprint.json schema); the log is CYCLE.md. NOT a SQL table.
  # The SQL conformance linter (lint_ledger_conformance.py) does NOT apply to a git-native ledger — it skips
  # with kind=git-native. Conformance here = "writes CYCLE.md + a failed-experiments fingerprint on FAIL +
  # commits the bus". Whether science should gain a STRUCTURED ledger (to get calibration/dedup views) is a
  # deferred enhancement (Phase 3+); the loop runs on git today and YAGNI applies until a gap is measured.

actions:
  generate_finding:    {autonomy: unattended, reversible: true, blast_radius: local}   # Lane A — write proposal to queue/, never executes
  execute_finding:     {autonomy: attended,   reversible: true, blast_radius: local}   # Lane B — implement greenlit; LITERAL attended (the partial ship action: a noisy verifier can't auto-trust execution). The ADR's narrow+reversible→unattended exception would be a deliberate literal flip here, NOT a route() default.
  accept_candidate:    {autonomy: route(),    reversible: true, blast_radius: local}   # verify-passed finding → route() → partial → ATTENDED (a human confirms the noisy accept)
  mark_failed:         {autonomy: unattended, reversible: true, blast_radius: local}   # archive to failed-experiments/, skip 2 cycles
  flag_clinical:       {autonomy: human_required, blast_radius: shared, reason: "clinical-implication threshold — never autonomous; → decisions-pending/ with cross-lab critique"}
  new_verifier_tooling: {autonomy: human_required, reason: "new verification tooling is a gate change — protected boundary"}
  modify_the_gate:     {autonomy: human_required, reason: "protected verifier boundary"}
  update_goals:        {autonomy: human_required, reason: "GOALS direction is human-owned"}

human_owned:
  - never-autonomous-set            # clinical thresholds, validated clinical logic, new verifier tooling, GOALS
  - GOALS
---

# science — partial-regime `LOOP.md` (the reference instance)

The **partial-verifier** instantiation of the outer-loop contract, derived faithfully from
`research-ops` cycle Lane A/B. It is the second reference instance (hutter = clean-cheap) and the
**proof of the route.py partial-regime fix**: a partial accept routes to ATTENDED, not the unattended
auto-ratchet, because a noisy verifier cannot be trusted to auto-commit (that is the intel/genomics
report-not-gate failure inverted). Validated by `tests/test_route_partial_regime.py`.

**The generate/execute split is the heart of the partial regime.** Lane A (Generate) produces
*reversible drafts* for a human yes/no — unattended, safe to run while you sleep ("wake up to N
ideas"). Lane B (Execute) ships greenlit changes — **attended**, because the partial verifier
(`verify_claim` + cross-model + the human) sits here and can't auto-ratchet. Do NOT port hutter's
auto-ratchet / parking-lot / preregistered-ΔS machinery — those need a clean metric, and faking one
is the vetoed `session_quality` trap.

**Two honest divergences from the naive plan, surfaced by ground truth:**
1. **Science is conductor-coupled, not a standalone loop.** `/research-ops cycle` is a worker the
   single conductor (`/improve maintain`) dispatches. So science's DEPLOY belongs with the conductor
   migration (Phase 3); this contract is build-and-prove only (the reference instance + the fix proof).
2. **Science's ledger is git-native, not SQL.** The attempt graph is git history; the log is CYCLE.md;
   failures are `failed-experiments/` fingerprints. The shared SQL ledger schema + conformance linter
   fit the structured loops (hutter, arc-agi, intel, genomics) but not the research loop — the linter
   skips `kind: git-native`. A structured science ledger is a deferred enhancement, not a Phase-2 port.
