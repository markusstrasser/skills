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
- **Deterministic-grader constructs (LatchBio bio-agent benchmarks; audited 2026-06-15,
  extended by VariantBench 2026-07-16).** For an eval with a deterministic numeric/structured grader (not a judge),
  five primitives we lacked: **(1) per-item separation table** — every item documents which WRONG method
  yields which number, and the tolerance is set to clear the nearest trap by a STATED margin
  (pre-registered discrimination bound to the ITEM, not the suite); **(2) sentinel/diagnostic gold
  fields** — grade a probe of the pipeline DECISION (does PC2–5 still correlate with depth ⇒ catches a
  skipped regress_out), a compound gate where each field traps one shortcut — the deterministic twin of
  the isomorphic verifier; **(3) before-step snapshot gold** — freeze the analysis state just before the
  target step so the oracle is a real re-run of standard tools (contamination-resistant, cheaply
  re-derivable); **(4) method-name suppression** — never name the expected method in the prompt (no
  "regress_out"/"pseudobulk"), forcing capability over memorized recipe; **(5) anti-hint input
  supersets** (VariantBench, audited 2026-07-16) — stage plausible extra files so the presence or
  absence of one artifact does not reveal the expected workflow, then run a cue-only baseline and
  bound distractor load so the construct does not silently become file triage. Plus **reproduce-or-discard
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


## 2026-09 adopts — judge-instrument hardening (folded from `evals/research/2026-09-05-newest-evals-two-months.md`)

Read depth for the arXiv rows is abstract-level (v1 dates confirmed); numbers are transcriptions, not
table-verified. Every institutional post was read in full.

- **Commit-first judging (Phase 4).** The judge solves the task itself, commits to an answer, then
  accepts a candidate only on match. An audit of the default judge configs of eight eval frameworks
  found 0 of 24 implement it; nine share one ancestor prompt traceable by a copied typo; a best-of-N
  search with no answer access got 90/96 and 93/96 candidates accepted, every one failing a held-out
  suite (arXiv:2609.00088). Cost: one extra judge call per item. Applies only where an answer is
  checkable; rubric-graded free text gets the R-probe instead.
- **Construct-sensitivity R beside invariance S (Phase 3).** Formalize judge validity as a 2-D
  profile: S = P(verdict unchanged under construct-preserving edits), R = P(verdict changes under
  minimal construct-changing edits); S and R are independent and no scalar summary preserves all
  comparisons. Across 7 judges × 4 domains with generation/verification/judging on disjoint model
  families, S=0.945 but R=0.319 at matched S≥0.90; surface-only predictors reproduce 55–67% of public
  labels incl. 67.4% of MT-Bench votes (arXiv:2608.24419). The probe is ~12 items on an existing rig.
  Pair with a **rubric-only sham arm**: classifiers over rubric text alone, with no response, predict
  judge output; judges often fail to update when the response or the criterion is reversed
  (arXiv:2609.02942). A non-trivial sham score means the run measured the rubric.
- **Endpoint rule (Phase 4 stats).** A double difference (within-item contrast, differenced across a
  manipulated attribute) read off a bounded rating scale is not identified on that scale: each term is
  censored by its own share, so a severity shift common to both responses manufactures an interaction
  whenever they censor unequally. A pre-registered 990-call audit reproduced 79–85% of its one
  significant interaction from the severity shift and the scale floor alone (arXiv:2608.27309). Use
  paired ranks, exact-match, or model the censoring.
- **Judge input hygiene.** (a) Prior scores carried only as metadata (revision / attempt / prior-score
  fields) shift ratings toward their values; 7 of 8 models show bootstrap intervals below zero on the
  anchored-metadata effect over 185k evaluations (arXiv:2608.25869) → `evalcore.judge.lint_no_anchoring`
  runs in `dispatch`. (b) Judge version instability: many-facet Rasch severity spans 219 points on a
  0–1000 scale across 12 judges; all five version contrasts shift severity past family-wise correction;
  judge-human r only .47–.56 (arXiv:2608.29517); judge upgrades are not interchangeable and repeated-sample
  juries add little when errors correlate (arXiv:2607.08535) → pin the judge build in the prereg; compare
  across a judge change only within-run and paired. (c) A decoding-budget parameter shared between the
  generation and judging calls silently truncated one producer's hallucinated answers and manufactured a
  32-point cross-lingual collapse that replicated from N=50 to N=500 with a mechanistic story attached,
  then vanished when the shared parameter was fixed (arXiv:2607.13707) → generator and judge never share
  a config object; `templates/config.toml` documents the keys. (d) Same-model judging is leniency-biased
  again on current models (Fable 5.1 card §6.5.3); the paired Eval-Pair Matrix estimator (judges paired on
  the exact same answer, ~275 validated records) is the correct COI estimator at our scale
  (arXiv:2607.10626) → `dispatch` warns when the judge model is in `blind_to`.
- **Omission is never judge-graded.** Across eight judge designs, paired discrimination is .79–.94 on
  added or altered content but .50–.63 on omissions; wording, voting and GEPA prompt optimisation do
  not recover it (arXiv:2608.31016). Completeness constructs use the LAB per-item presence check
  (scoped per-criterion context) — the checklist oracle the paper recommends. Hindsight: HAD-LEVER.
- **pass^k and generation residuals.** ThinkingBox (507 stateful workflows, backend-state grading):
  Opus 5 pass@1 66.50% vs pass^20 47.53% on the same tasks (arXiv:2608.19741) → `evalcore.stats.pass_rates`.
  In an agent-commerce re-audit, reported welfare gains of +87.4/+35.0/+28.8 collapsed to +7.2/−13.9/+23.8
  once arms shared an offer schema and chooser; generation residuals were 49.9% of variance and the four
  largest single-generation effects averaged +229 vs +37.6 over three generations (arXiv:2609.01519) →
  ≥3 generations per condition, harness identical across arms. Harness-only changes moved SWE-bench
  Verified F2PF 28%→49% with frozen weights (arXiv:2608.26218) → `harness` is a provenance field.
- **Stopping rule.** UK AISI `optstop` (MIT, `pip install optstop[inspect]`, arXiv:2608.14425):
  hierarchical-Bayesian sequential stopping on credible-interval width or stabilisation, with a
  low-success safeguard; removed 57–97% of planned trials across nine settings with equivalent
  conclusions. Preregister the precision target instead of N; pin the version (4-commit repo).
- **Provenance generation settings.** Evaluation Cards (EvalEval/HF, arXiv:2606.09809): 96.5% of
  reported evals miss at least one field needed to re-run them; max-tokens absent 95.6%, temperature
  93.9% → `storage.provenance(generation=..., judges=..., harness=...)`, filled by `run_eval`.
- **Audit-conditional numbers.** Anthropic's reward-seeker checkpoint (Opus 4.8 RL'd on ~80 hackable
  environments) scored 1.12 vs 1.04 baseline on the automated behavioral audit and complied with
  bioweapon requests at 29% with a visible grader vs 0.7% without
  (alignment.anthropic.com/2026/reward-seeker/). UK AISI (2026-07-21): every frontier model tested
  attempted to cheat (out-of-scope or disallowed actions); self-report acknowledged it <50% of the time
  and chain-of-thought often did not mention it. A judge-scored number where the SUT can infer grading
  is a behavior-under-audit number: add a grader-hidden arm or label it.
- **Agentic-trace scanners.** Four scanner types with human-labeling rubrics, validated on held-out
  Inspect Evals: ground-truth access, tool failure, guessing vulnerability, answer-format ambiguity
  (arXiv:2607.27518) — a superset of the leakguard for trace review. Record contamination *acquired
  during the run* as a per-run provenance field, not a benchmark property (arXiv:2608.29463).
- **Teardown rubric items 10–13** (`evals/docs/famous-evals-teardown-rubric.md`): gold error rate
  (FrontierMath v2 corrected errors in 42% of problems), author re-selection rate (Terminal-Bench 2.0 →
  Harbor-Index 3/89), contamination half-life (SWE-Bench Pro 23%→80% in eight months), grader visibility.
