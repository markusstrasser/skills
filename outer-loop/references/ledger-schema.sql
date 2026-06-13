-- outer-loop canonical ledger schema (the STRUCTURE layer — the part that transfers cross-repo).
--
-- This is the GENERIC superset. A repo's real ledger (hutter's `experiments`, arc-agi's designed
-- table, agent-infra's `maintenance-actions.jsonl`) is ONE INSTANCE of this shape under
-- domain-specific column names. Repos do NOT rename their columns to match — the per-repo
-- `LOOP.md` contract carries a `ledger.field_map` (canonical → that repo's actual column) and the
-- conformance linter (`scripts/lint_ledger_conformance.py`) checks the MAPPED columns exist. So
-- this file is two things: (1) the reference contract the linter enforces, (2) a ready schema a
-- NEW repo can adopt verbatim.
--
-- Field tiers (the linter's contract — see scripts/lint_ledger_conformance.py):
--   REQUIRED        — every loop's ledger must provide these (mapped). Absent → linter FAILS.
--   REQUIRED-IF     — required only when the contract declares a regime/feature that reads them.
--   RECOMMENDED     — absent → linter WARNS (advisory; measure-before-enforce). gate_version lives
--                     here: clean+deterministic gates defeat silent gate-gaming structurally (you
--                     cannot p-hack an exact byte count), so the audit field is belt-and-suspenders
--                     in clean regimes and load-bearing only where the gate is soft (partial/principal).
--   EXTENDED        — repo-specific columns the loop never reads; unconstrained.
--
-- The accept-gate verdict is the SPINE: it is CONSUMED (gates the ratchet), never merely reported,
-- and it is a STRUCTURED enum, never a bare exit code. `modify_the_gate` is a human-only action
-- (protected verifier boundary) — the loop never silently edits its own accept-gate.

CREATE TABLE IF NOT EXISTS ledger (
  -- ── REQUIRED core (present in every mature loop today: hutter, agent-infra, arc-agi-designed) ──
  id              INTEGER PRIMARY KEY,
  ts              TEXT    NOT NULL,        -- REQUIRED  timestamp (ISO-8601)
  candidate       TEXT    NOT NULL,        -- REQUIRED  what was tried (hutter: variant; agent-infra: finding)
  verdict         TEXT    NOT NULL,        -- REQUIRED  STRUCTURED outcome enum — the consumed spine.
                                           --           accept-class: ACCEPT | BASELINE | GATE_PASS
                                           --           reject-class: REJECT
                                           --           error-class:  ERROR  (gate failed / not bit-exact → fail-closed)
                                           --           probe-class:  PROBE_WIN | PROBE_LOSS | PROBE_BASELINE (never ratchets)
                                           --           (repos may add verdicts; the contract's accept_verdicts list is authoritative)
  lineage_parent  INTEGER,                 -- REQUIRED (nullable)  parent row id — feeds restart-from-fertile-parent
  reason          TEXT,                    -- REQUIRED (nullable)  human/agent note; on ERROR, the failure cause
  tags            TEXT,                    -- REQUIRED (nullable)  comma-sep technique/family tags — proposer dedup edge
  dead_end        INTEGER DEFAULT 0,       -- REQUIRED  1 = do-not-retry — proposer dedup edge

  -- ── REQUIRED-IF clean regime (numeric verifier — calibration honesty) ──
  score           REAL,                    -- the verifier's measured score (hutter: s_bytes)
  predicted_score REAL,                    -- PREREGISTERED prediction stamped at propose-time → v_calibration.
                                           --   the falsifiable-contract / anti-self-p-hack field (AHE pattern;
                                           --   hutter: predicted_ds). Required wherever acceptance is greedy.
  baseline_score  REAL,                    -- the score being ratcheted against at eval time
  delta_score     REAL,                    -- score - baseline (sign convention is the repo's; hutter: negative=better)

  -- ── REQUIRED-IF clean-EXPENSIVE regime (proxy + dual-gate + rate-limited ground truth) ──
  proxy_score        REAL,                 -- cheap/local proxy verifier (arc-agi: synthetic-env score)
  ground_truth_score REAL,                 -- expensive/rate-limited true verifier (arc-agi: Kaggle RHAE)
  budget_consumed    REAL,                 -- units of the rate-limited resource this row spent (arc-agi: submissions)

  -- ── REQUIRED-IF a human-gated action recorded here (partial/principal) ──
  human_approver  TEXT,                    -- who signed off (discovery/irreversible/taste). NULL on unattended rows.

  -- ── RECOMMENDED (audit / reproducibility / protected-boundary trail) ──
  gate_command    TEXT,                    -- the exact accept_gate command that produced `verdict`
  gate_version    TEXT,                    -- accept_gate version — stamped so a gate change is DETECTABLE post-hoc.
                                           --   RECOMMENDED not REQUIRED: clean deterministic gates catch silent
                                           --   gate-gaming structurally; soft gates (partial/principal) need this.
  artifact_hash   TEXT,                    -- hash of what actually RAN (hutter: binary_sha256) — stale-artifact provenance
  data_snapshot   TEXT,                    -- the data/slice the verdict is over (hutter: slice)
  env_version     TEXT,                    -- tool/env version (model id, lib pin, harness sha)
  proposer_version TEXT,                   -- which proposer/skill version generated the candidate
  skill_version   TEXT,                    -- outer-loop skill version active for this decision (global skill must
                                           --   not silently change a repo's behavior — pin + stamp)
  quarantine_state TEXT,                   -- ERROR triage (hutter: error_class: RUN_FAIL/CANARY/HARNESS_RC)
  rollback_pointer TEXT,                   -- how to undo an accepted change (git sha / parent ref)

  FOREIGN KEY (lineage_parent) REFERENCES ledger(id)
);

CREATE INDEX IF NOT EXISTS idx_ledger_verdict ON ledger(verdict);
CREATE INDEX IF NOT EXISTS idx_ledger_candidate ON ledger(candidate);

-- Calibration: preregistered prediction vs actual — "is the proposer honest?" The anti-self-p-hack
-- signal (PACE arXiv:2606.08106: greedy keep-if-score-up is self-p-hacking at 30–42%). Generic over
-- the canonical names; a repo whose columns differ exposes its own equivalent view (hutter: v_calibration
-- over predicted_ds/d_s). Excludes ERROR rows (phantom deltas poison the average).
CREATE VIEW IF NOT EXISTS v_calibration AS
  SELECT id, candidate, predicted_score, score, delta_score,
         (delta_score - predicted_score) AS miss
  FROM ledger
  WHERE predicted_score IS NOT NULL AND delta_score IS NOT NULL
    AND verdict NOT IN ('ERROR')
  ORDER BY ts DESC;

-- Dead-ends + rejects — the proposer reads this to not re-propose. Excludes crash rows (a crash is
-- not a gate-measured death; asserting it forecloses families the gate never judged).
CREATE VIEW IF NOT EXISTS v_dead_ends AS
  SELECT id, ts, candidate, verdict, delta_score, tags, reason
  FROM ledger
  WHERE (dead_end = 1 OR verdict IN ('REJECT','ERROR'))
    AND (score IS NULL OR score > 0)
  ORDER BY ts DESC;

-- Clade yield — a node's own score weakly predicts its lineage's future (HGM CMP estimator:
-- own-score r≈0.28–0.44 vs clade-pooled 0.63–0.78). Restart-from-fertile-parent reads this:
-- pick the restart base by DESCENDANT accept-yield, not own score or recency.
CREATE VIEW IF NOT EXISTS v_clade_yield AS
  WITH RECURSIVE clade(root_id, node_id) AS (
    SELECT e.id, c.id FROM ledger e JOIN ledger c ON c.lineage_parent = e.id
    UNION
    SELECT cl.root_id, c.id FROM clade cl JOIN ledger c ON c.lineage_parent = cl.node_id
  )
  SELECT cl.root_id AS id, r.candidate, r.verdict, r.delta_score AS own_delta,
         COUNT(*) AS clade_n,
         SUM(CASE WHEN n.verdict = 'ACCEPT' THEN 1 ELSE 0 END) AS clade_accepts,
         MIN(n.delta_score) AS clade_best_delta
  FROM clade cl
  JOIN ledger n ON n.id = cl.node_id
  JOIN ledger r ON r.id = cl.root_id
  GROUP BY cl.root_id
  ORDER BY clade_accepts DESC, clade_best_delta ASC;
