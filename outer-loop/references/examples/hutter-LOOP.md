---
loop:
  repo: hutter
  outer_loop_skill:
    name: outer-loop
    version: 2026-06-13
    expected_schema: 1

verifier:
  regime: clean-cheap

schedule:
  driver: "/loop /dream  (unattended: launchd claude -p /dream — local, zero quota; NOT /schedule)"
  noop_on: queue-healthy          # queue ≥10 unused ideas AND no STALL AND no proposals-pending
  lock: scripts/dreamer_lock.sh   # single-writer Dreamer; acquire at takeover, heartbeat each tick

proposer:
  skills: [leverage, research, brainstorm, critique]
  dedup_against: [v_dead_ends, v_revisit]
  max_per_fire: 8                 # cap fresh ideas so the grinder isn't flooded

bus:
  ledger: ledger.db#experiments
  queue: queue/
  human_queue: decisions-pending/
  flags: [queue/STALL, queue/QUEUE_LOW]
  discovery_flags: proposals-pending/

accept_gate:
  cmd: "python3 scripts/eval.py --variant {variant} --slice {slice} [--probe|--gate|--new-baseline] --predicted-ds {n} --tags {tags}"
  verdict_field: verdict          # stdout `verdict:` line + the experiments.verdict column
  accept_verdicts: [ACCEPT, BASELINE, GATE_PASS]
  error_verdicts: [ERROR]
  independence: external          # bit-exact deterministic round-trip — ground truth, not a model
  gate_version: null              # recommended only: the deterministic byte-count ratchet defeats
                                  # silent gate-gaming structurally (you cannot p-hack an exact size)
  budget: null                    # free / infinite / deterministic — no rate limit

ledger:
  path: scripts/ledger_schema.sql # source of truth (ledger.db is gitignored / rederivable)
  table: experiments
  field_map:                      # canonical → hutter's compression-specific column
    candidate: variant
    score: s_bytes
    predicted_score: predicted_ds
    baseline_score: baseline_s
    delta_score: d_s
    lineage_parent: parent_id
    artifact_hash: binary_sha256
    data_snapshot: slice
    quarantine_state: error_class
    reason: notes
  calibration: {predicted: predicted_ds, actual: d_s, view: v_calibration}

actions:
  enqueue_idea:       {autonomy: unattended, reversible: true, blast_radius: local}   # append to queue/
  run_candidate:      {autonomy: unattended, reversible: true, blast_radius: local}   # eval.py probe / measure
  accept_candidate:   {autonomy: route(), reversible: true, blast_radius: local}      # ratchet — clean+accept → unattended
  mark_dead_end:      {autonomy: unattended, reversible: true, blast_radius: local}   # dead_end=1
  flag_discovery:     {autonomy: human_required, blast_radius: shared, reason: "model-class move — discovery gate; cross-lab critique → decisions-pending/, never greenlight"}
  modify_the_gate:    {autonomy: human_required, reason: "protected verifier boundary — never edit grinder code/ledger/harness"}
  model_class_change: {autonomy: human_required, reason: "discovery tier — paradigm/architecture swap is Markus's call"}

human_owned:
  - strategic-move-checklist       # OUTER-LOOP.md "Dreamer strategic-move checklist" — propose, never self-evolve
  - GOALS
---

# hutter — clean-cheap `LOOP.md` (the reference instance)

This is the **clean-cheap** instantiation of the outer-loop contract, derived faithfully from
hutter's `OUTER-LOOP.md` Dreamer. It is the Phase-1 vertical slice: the outer-loop skill + this
contract reproduce the OUTER-LOOP Dreamer's behaviour, verified by
`tests/test_route_trace_equivalence.py`.

**Why clean-cheap is the simplest point:** the accept-gate (`eval.py`) is a deterministic bit-exact
compression measurement — free, infinite, and impossible to game (a wrong result fails the round-trip
and is recorded `ERROR`, never a fake win). So low-blast actions (run a candidate, accept a ratchet,
mark a dead-end, enqueue an idea) are **unattended**, and only the discovery tier (a model-class
change) and the gate/GOALS themselves are human-gated.

**The split that makes it work:** the *inner* loop is the GPT-5.5 grinder (NEVER-STOP on a VM,
runtime-bound). This contract + skill are the *outer* loop (the Dreamer) — runtime-agnostic, git-bus
only, never touching the VM or the harness. The outer loop shells `eval.py` and consumes its
structured verdict; it never re-implements the gate.

**Mapping note:** hutter's `experiments` table predates this schema, so `field_map` aliases every
canonical field to its compression-specific column (`variant`→candidate, `s_bytes`→score,
`predicted_ds`→predicted_score, …). The conformance linter checks the *mapped* columns — hutter
passes today with zero schema change. The RECOMMENDED audit fields it lacks (`gate_version`,
`proposer_version`, `skill_version`, …) warn-only; `eval.py:db()` already self-migrates columns, so
adopting them in Phase 2 is a one-line addition, not a migration.

**This file is the Phase-1 example, not yet hutter's live contract.** Phase 2 plants the
authoritative copy into hutter and archives the `OUTER-LOOP.md` Dreamer body (the strategic-move
checklist stays — it is human-owned and referenced, not replaced).
