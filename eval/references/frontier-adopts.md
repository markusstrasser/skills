# Eval — 2026-06 frontier adopts + confirmations (full evidence)

> Moved verbatim from eval/SKILL.md (2026-07-06, progressive disclosure). The SKILL.md
> digest carries one line per adopt; this file is the full mechanics, arXiv evidence, and
> the DeepSWE / LifeSciBench confirmations + guards. Update HERE; keep the digest line in sync.

## 2026-06 frontier adopts (folded from `evals/research/2026-06-13-frontier-*.md`; ADR 0001)

Cross-axis convergence of 5 frontier memos: **outcome-only scoring is structurally
insufficient — verify the trace/structure.** That is the same lesson the phenome KG-verifier
trace audit forced (2026-06-13); the field now backs it (`arXiv:2605.08545` log-analysis as a
third validity pillar; `arXiv:2604.15149` isomorphic verifiers, causal). Adopt:

- **Isomorphic verifier (Phase 1 verifier-regime).** For agentic/tool-use SUTs, the check is not
  "did it return verdict X?" but "did it traverse the path that *reaches* X?" — score the trace
  (which KG nodes/edges queried), not the output (which may be parametric recall). Causal backing:
  checking structure (not just output) removes the gaming incentive.
- **Gold-leak guard (Phase 2/4).** Call `evalcore.leakguard.assert_no_gold_leak(sut_prompt, gold)`
  before EVERY SUT dispatch — the twin of `assert_blind`. It default-denies all gold-only fields
  (criteria_flags/evidence/failure_modes/route_hints/why_selected/Q-tags + the `gold_verdict`
  *binding*; the bare answer-space label is fine). This is the structural form of the MACVB
  criteria_flags→F1=1.0 leak. **Held-out criteria:** the agent must never see the full scoring
  contract; hold out ≥30% of scoring dimensions (reward-hacking gap grows with task horizon).
- **Block mirror domains (Phase 1 contamination).** For retrieval/web-search SUTs, block
  `huggingface.co`, `paperswithcode.com` and benchmark mirrors in the tool config — search-time
  contamination (the agent retrieves a copy of the test set) hit ~3–4% of queries in a study and
  standard provenance checks miss it. (Canaries: weak for *training*-contamination, but a synthetic
  canary in gold-only fields, asserted absent from prompts, is a cheap *leak* tripwire.)
- **Rubric decomposition before grading (Phase 4).** Decompose each task into sub-rubrics (claim-type
  / traversal / evidence / verdict / uncertainty) and grade each; rubric-decomposed judges agree with
  humans at κ≈0.79 vs ≈0.51 for a holistic trajectory judge. Don't use a holistic LLM judge as primary.
- **Item-quality flag + FDR (Phase 4 stats).** After ≥3 arms accumulate, `evalcore.stats.point_biserial`
  flags suspect items (stronger arms fail more ⇒ candidate mislabel/contamination) — an INVESTIGATION
  FLAG for manual gold review, never an auto-gate (noisy at N≈20). `evalcore.stats.benjamini_hochberg`
  is EXPLORATORY-only; decision claims stay Holm/FWER or bootstrap CIs.
- **Read ≥5 traces (Phase 3.5 gate).** Before accepting a probe/verdict, read full traces for ≥1 pass
  + ≥1 fail of each top arm, against the 4 questions (`arXiv:2605.08545`): did it (1) read the answer
  off a mirror, (2) exploit a scoring loophole, (3) take a dangerous intermediate action, (4) fail from
  scaffold limits not capability? A decision-grade verdict must cite *verifiable* trace anchors
  (id + excerpt), not a boolean "I read them."
- **Metamorphic vocabulary for invariant claims (Phase 5).** State invariants as
  `source_relation ⇒ output_relation` (the MT discipline behind our "invariant claims"). An oracle-free
  invariance tier (paraphrase/reorder a gold claim, assert verdict-invariance, report % invariant) is
  **discovery-only** — preregister invariants, calibrate its ~40% false-positive rate on negatives, and
  NEVER mix it into pass/fail or the materiality call.
- **Q-matrix tags (Phase 2 template).** Tag each case to a fixed 3–5-dim capability ontology
  (retrieval/inference/abstention/binding/query, + `unknown`) as **gold-only** metadata (never in a
  SUT/judge prompt — it's on the leak deny-list). Enables a diagnostic mIRT capability profile *later*;
  do NOT fit IRT params at N=10–60 (needs ≥100 items × ≥20 arms).
- **Deterministic-grader constructs (LatchBio bio-agent benchmarks scBench/SpatialBench/SB-Long, audited
  2026-06-15, 3 readers).** For an eval with a deterministic numeric/structured grader (not a judge),
  four primitives we lacked: **(1) per-item separation table** — every item documents which WRONG method
  yields which number, and the tolerance is set to clear the nearest trap by a STATED margin
  (pre-registered discrimination bound to the ITEM, not the suite); **(2) sentinel/diagnostic gold
  fields** — grade a probe of the pipeline DECISION (does PC2–5 still correlate with depth ⇒ catches a
  skipped regress_out), a compound gate where each field traps one shortcut — the deterministic twin of
  the isomorphic verifier; **(3) before-step snapshot gold** — freeze the analysis state just before the
  target step so the oracle is a real re-run of standard tools (contamination-resistant, cheaply
  re-derivable); **(4) method-name suppression** — never name the expected method in the prompt (no
  "regress_out"/"pseudobulk"), forcing capability over memorized recipe. Plus **reproduce-or-discard
  candidate gold** (admit a literature claim as gold only after independent reproduction yields a stable
  answer; log the excluded) and logging **cost + trajectory length** beside accuracy as first-class axes.
  (Item-difficulty rank-stability is another diagnostic use; the deferral on FITTING IRT at our N stands.)
- **Measurement-science canon — cross-domain imports** (folded from `evals/research/2026-06-15-measurement-canon-cross-domain.md`;
  6 primary sources saved to corpus). The mature measurement sciences solved problems we hit; the net-new delta
  AFTER inventorying what we had (Metamorphic Testing, Goodhart, IRT already covered): **(1) Equating for a
  DRIFTING instrument** — when the SUT itself changes across versions (a skill's prompt/rules/goals), it is an
  instrument with drift; freeze ANCHOR items constant across versions and read capability deltas RELATIVE to the
  anchor — an uncontrolled drift is a confound, not a measurement (psychometric NEAT design; Kolen & Brennan).
  This is the answer to "what does a frozen measurement of a moving target mean." **(2) Signal Detection Theory
  for hit/false-alarm evals** — separate detection SKILL (d′) from trigger-happiness (criterion c); ranking arms
  by RAW detection conflates them (an arm that finds more may just be liberal). Coded ref impl:
  `critique_replay/sdt.py` (+ bootstrap d′ CI, rank-inversion catch; Green & Swets). **(3) Proper scoring rules**
  (Brier/log; Gneiting & Raftery) for ANY probabilistic/confidence output — uniquely maximized by reporting the
  true probability, so hedging can't game it; Murphy-decompose into calibration + resolution. **(4) Pre-flight as
  a GRADED bias instrument** — Cochrane RoB-2's 5 domains (randomization / deviations / missing-data / outcome
  MEASUREMENT / selective REPORTING) map onto our confound/gold/judge/trace gates; import the per-domain
  low/some-concern/high judgment, not a binary pass. (Metrology's invariant-anchoring → Phase 5 §6b below.)
- **Measurement-canon round 2 — opaque/novel-mind analogs** (folded from `evals/research/2026-06-15-eval-analogs-SYNTHESIS.md`
  + 5 domain memos; COMPLEMENTS the bullet above, no overlap). Six unrelated sciences converge on how to credit an
  unobservable capability; net-new transfers: **(1) Ground-truth-free scoring via PEER PREDICTION** (Qiu et al. ICLR'26
  `arXiv:2601.20299`, Algorithm 1) — score an answer by the PMI between it and *other independent* answers as judged by a
  (possibly weak) jury; incentive-compatible, NO gold, with an **inverse-scaling** bonus (a weak cheap jury grades a
  STRONGER model better as the capability gap widens). **WIRED + VALIDATED 2026-06-15** (`evalcore.elicit` +
  `evals/critique_replay/score_invention.py`, a deterministic anchor jury, $0): on a real run the gold-free PP arm
  ranking was **IDENTICAL to the gold-based detection ordering (Spearman ρ=1.0)** — convergent validity, and it RETIRED
  the clean-stratum rebuild for ranking. (`inspect_ai` scanned — no built-in scorer; ours is the in-tree primitive.)
  FAILS under ≥50% correlated/colluding pool — enforced in code by `evalcore.elicit.pool_independence`/`collusion_risk`,
  never assumed. **Honest bound:** on a defect-heavy set every packet is collusion-flagged so PP ≈ corroboration-weighted
  detection — it ranks gold-free but doesn't isolate *pure* invention (uncorroborated-but-real); for that, keep a few
  no-defect probes or the per-finding judge. **(2) Capability is the LAST-RESORT hypothesis** — Morgan's Canon (comparative
  cognition) ≡ "life is last-resort" (astrobiology Ladder criterion 8): a score is evidence of a *capability* only after
  contamination/shortcut/memorization are affirmatively excluded. Make it a NAMED hard gate, not a footnote. **(3) Verdict
  as a graded ARGUMENT** — NASA CoLD scale (7 named confidence gates, post-hoc-confound bar α₂≪α₁) as the confidence axis
  × GSN assurance case (claim→strategies→leaf-evidence, with an ODD scope + an Assurance-Claim-Point saying screening-vs-
  confirmatory) as the structure. **(4) Competence ≠ performance / elicitation gap** — measure best-case-elicited ability;
  a probe that *represents* a capability (mech-interp) is weaker evidence than a causal-patch that shows it's *used* (CoLD
  L3 "could" vs L4 "did"); probes are gameable (`arXiv:2512.11949`) so white-box is a measurement aid, not a certificate.
  **(5) Anti-Clever-Hans** — a benchmark answerable from a surface cue measures the cue (backs leak-guard from a 2nd field).
  **(6) DIF probe** — flag items where equal-capability models from different FAMILIES diverge (family/format confound);
  cheap, reuses run data.
  **(7) Verdict = a machine-checkable GATE-LEDGER, REALIZED** (evals ADR 0007 + `scripts/check_verdict.py`; the
  CoLD×GSN ladder, built not proposed). A VERDICT-of-record carries a json front-matter ledger:
  `confidence_level` × `call` + `odd{scope,excludes}` + 7 gates `{status,evidence}`: `discrimination`,
  `representativeness` (does the ODD sample match the production decision surface? — added by adversarial
  review), `last_resort`, `independence`, `noise_budget`, `power`, `materiality`. The confidence/call CLAIM is
  EARNED by discharged gates (CoLD α₂≪α₁): `confirmatory`⇒noise+power+representativeness pass; `promote`⇒
  last_resort+discrimination+representativeness pass; a `pass` MUST cite a leaf (run_id/§/number), else it is
  `deferred`. A deferred gate CAPS confidence, never forbids the verdict. The gates are POINTERS to scorers this
  skill already names (independence→`pool_independence`; noise→`dispatch_repeated` flip_rate; power/noise leaf→
  `stats.variance_components` G-study; last_resort→the prereg gate). Any repo with the evalcore dep can adopt the
  pattern; the validator is in evals. Build-rank context: the synthesis memo.
  **Process reflex (extends Pre-Build #1):** before INVENTING a metric or grading scheme, inventory the measurement
  sciences (psychometrics, metrology, mechanism design, mech-interp, comparative cognition, astrobiology) for an
  existing instrument — every net-new transfer above was already a solved problem in some mature field. "We have no
  way to grade this" almost always means "we haven't checked who grades the unobservable for a living."

**Confirmed by DeepSWE** (datacurve, 2026-06 — independent production coding-agent benchmark, 113
tasks, frontier 70%→5% spread; `evals/research/2026-06-13-frontier-agentic.md` §Transfer): authored-
fresh-over-real-pinned-repo + hidden behavioral verifier + sealed env independently realize the adopts
above. Two portable patterns: **(1) withheld grader** — ship the scoring tests as a patch applied
ONLY at grade time (DeepSWE's `test.patch`), so the agent provably can't enumerate the contract (the
structural form of held-out criteria); **(2) seal the env if you can, domain-block if you can't** —
DeepSWE sets `allow_internet=false` to kill search-time contamination by construction; a retrieval/
claim SUT that needs the web can't seal, so it must block benchmark-mirror domains + track provenance.
**Boundary:** DeepSWE's realism rests on a FREE EXECUTABLE ORACLE (tests); claim-verification has none
→ that is *why* this rig needs judges + isomorphic trace-checks, not behavioral verifiers. Don't
cargo-cult "write behavioral verifiers" into a domain with no oracle.

**Confirmed by LifeSciBench** (OpenAI, 2026-06; full teardown `evals/research/2026-06-18-lifescibench-rating.md`):
stronger *gold authorship* than any prior provider bio-eval (disjoint author/validator pools, 19,020 atomic
weighted rubric criteria) and STILL only ADAPT-DESIGN-ONLY — a strong construct does not buy a transferable
ranking when the grader is same-family + the grader-validation numbers are unprinted. Durability is **unestablished
(not a standing per-release instrument)**: a static held-out set with no temporal/canary/post-cutoff controls is a
vendor-tuning target, and unrestricted eval-time browsing breaks reproducibility + is a per-model-interface confound
— note this is NOT answer-retrieval (the set is held-out), so don't call open browsing "contamination by
construction." Borrow FROM the DURABLE designs it is NOT: **LiveMedBench** (`arXiv:2602.10367`) — WEEKLY post-cutoff
clinical-case harvest (contamination-free by construction) + a decomposed rubric grader that beats LLM-as-judge on
physician alignment (84% of models degrade post-cutoff = the contamination a static set hides); **GeneBench** (Li &
Ho 2026) — synthetic single-defensible-path + ablations = a DETERMINISTIC verifiable-answer oracle, no model judge
(LatchBio scBench family). Code-shipping debiaser: **ProfBench** (NVlabs, MIT) Bias-Index, **built + self-tested as
`evalcore.stats.judge_bias_index`** — the SPREAD of a judge's per-model signed bias vs human labels (panel-relative;
LOW = even-handed, NOT accurate, so pair with Macro-F1; it does NOT itself detect same-family self-enhancement —
the caller must supply which model shares the judge's family). No production caller yet; the live-dispatch wiring is
the consumer-shaped part, deferred to the first judge-validation eval that needs it.

**Guards (the frontier also tells you what NOT to adopt at our N):** PPI/CLT-PPI label-saving is
statistically invalid below 50 labels/stratum (GLIDE `arXiv:2605.31278`) — at ~20/stratum, hand-label
all + bootstrap; `just power` refuses PPI/R² sizing below the threshold. Fitted IRT, CapBencher,
CAT/LEGO-IRT, noise-injection sandbagging: deferred — see `evals/docs/decisions/deferred-and-open.md`.
