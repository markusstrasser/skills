# Eval — anti-pattern evidence (full war stories + ref impls)

> Moved verbatim from eval/SKILL.md (2026-07-06, progressive disclosure). SKILL.md keeps
> pattern-name + 1-line lesson; this file is the incident evidence, dates, arXiv refs, and
> reference implementations. Append new incidents HERE; add the name+lesson line inline.

## Phase-1 §5 evidence — same-family confound · frontier judge bias · judge noise budget

   - **Same-family confound — at EVERY model touchpoint, not just the generator.** General rule:
     *any model that helps produce or score the eval's relevance signal must be neutral to all
     candidates* (share no lab/family). Three touchpoints, all real:
     - **Generator** (LLM-written cases/queries): a candidate-sibling generator inflates that candidate
       (its paraphrase distribution aligns with the sibling's representation space). ≥2 neutral-family
       generators, temp 0, persisted fixtures, report a generator effect. (Evidence: bio_embedding_bakeoff
       v1 — gemini-flash queries gave the gemini embedder pooled P=0.97; neutral GPT → a tie.)
     - **Judge** (LLM-graded relevance): never grade with a candidate's sibling family. **Blinding to
       model identity does NOT protect you** — the bias rides the *content* of the grades (a sibling
       judge rates the candidate's neighbors relevant via shared representation space), not the label.
       ≥2 neutral families, report inter-judge κ, anchor with a human spot-check. (v2: GPT+Claude
       judges, never Gemini, κ=0.669.)
     - **Reranker / fusion in a consumer lane**: a reranker from a candidate's family can't be the
       *deciding* lane — decide on the model-agnostic (raw cosine) lane, treat the production rerank as
       a diagnostic. (v2: production reranker is gte-family → the gte-vs-gemini2 switch is decided on the
       isolation lane. Mechanical nuance: a *text* cross-encoder scores blind to the retriever so its
       scoring origin-bias is ~0, but its notion of relevance still shares a lab — it informs, doesn't gate.)

   - **Frontier judge bias (current, measured + reconciled with prior art).** *Established:*
     **position/order bias is solved** on frontier judges (our probe: 0 position-locks over 66
     presentations incl. ambiguous pairs; corroborated by `arXiv:2604.23178` position ≤0.04, "style is
     the dominant bias"). Stop spending order-swap/position-debias on frontier judges. *Established
     (use it):* **same-lab judges share a style signature → a same-lab panel is ~1 effective vote and
     any Bradley-Terry/Elo SE on it is false precision** — use a **cross-lab panel**, read disagreement
     as signal (`arXiv:2601.05114`: judges self-consistent but disagree — "measuring different
     things"). Self-preference is real and quality-controllable to measure (`arXiv:2604.22891`
     PIR-vs-Null-PIR framework, `2604.06996` GPT-5/Claude-4.5). *RETRACTED — cautionary tale:* our n=5
     probe found GPT/Gemini "prefer padded filler 8–9/10"; a controlled-ratio study (`2604.23178`,
     n=825, truncation controls) found the **opposite** — frontier judges penalize filler and reward
     genuine completeness. Our "verbosity bias" was a **length-RATIO artifact** (3–4× padding), not a
     length preference. **Lesson: see "controlling *a* confound, not *the* confound" in Anti-patterns.**
     Re-run the probe (`evals/bio_embedding_bakeoff/judge_bias_probe.py`) when judges ship — but with
     controls (length ratio ≤2×, truncation controls to separate filler from genuine completeness).
   - **Judge NOISE BUDGET — a single-trial judged number is PRELIMINARY (distinct from bias).** Even an
     unbiased judge is STOCHASTIC. *Coin Flip Judge* (`arXiv:2606.13685`, Jun 2026): **13.6% mean
     single-trial flip rate** (28% of items >20%), cross-judge κ≈0.51, reliability curve needs **~11
     repeated trials for 95% fidelity**. At N=20–60 that's ~3–8 flipped outcomes per run — enough to
     reverse a SCREENING rank. So: report the judge-noise budget; for a decision, repeat the judging
     (≥3) **or** use PPI/PRECISE (`arXiv:2606.05308`: provably-unbiased ranking from ~30 human-gold +
     a large LLM-judged set, 21% SE cut) to bias-correct. Corollary — *CARE* (`arXiv:2603.00039`): a
     multi-judge panel is **not independent** (same-lab judges share confounders) → "3 judges = 3 votes"
     over-states confidence; cross-lab + confounder-aware, never naive averaging. (Lived it: critique_replay
     used SINGLE-trial gemini+gpt judges, κ=0.667 — right in this paper's band; its detection ranks are
     screening-only partly for this reason. evidence: `research/2026-06-15-newest-eval-papers.md`.)

## Anti-patterns (full text)

## Anti-patterns (each one vetoed or observed here)

- Composite quality scores / standing leaderboards (vetoed 2×: session_quality, Arena-transfer)
- Judge panels as truth; judge sees engine/model identity; consequence-framing in judge prompts
- Single global accuracy hiding the unreliable stratum (PARTIAL-type strata drive disagreement)
- Items lifted from public benchmark sets without per-item justification
- **Trusting ABSOLUTE scores on a reused test set; reading a small absolute gain as capability.** Even with
  NO deliberate gaming, repeated reuse of a fixed test set inflates absolute scores (adaptive overfitting)
  while RANKINGS stay robust — a freshly-rebuilt ImageNet/CIFAR test set dropped every model's accuracy but
  preserved order at Pearson R≈0.99 (Recht et al. 2019). A small absolute gain on a reused set may be
  test-set adaptation, not capability; the trustworthy signal is a RANKING flip. Defenses: refresh items to
  recalibrate level (LiveBench-style), and anchor-equate (adopts §canon M1) so deltas read against a frozen scale.
- N chosen by vibes — run `just power` and declare the regime
- Eval with no consumer; verdict that never reaches DECISIONS.md or production
- LLM re-audit of gold labels; editing a prereg decision rule after results exist
- Single-gold recall@k on a corpus with co-relevant siblings — scores label noise as model skill
  (bio_embedding_bakeoff: 23/48 golds outranked by *relevant* siblings; verdict inconclusive)
- Trusting aggregate metrics without reading one failure; over-obfuscated riddle-queries that beat
  the keyword baseline but don't match the real query distribution
- **Controlling *a* confound, not *the* confound** (judge-bias probe, 2026-06-12 — the egg). A
  manipulation probe must hold ALL-BUT-ONE variable constant between its two conditions. Our "verbose
  vs concise" answers differed on *two* axes — sycophantic framing AND raw length ratio (3–4×) — so a
  preference could not be attributed to "verbosity." We checked one confound (reasoning effort, it
  held) and called it robust; the confound that actually drove it (length ratio) we never isolated. A
  controlled-ratio study (`arXiv:2604.23178`) with truncation controls found the opposite. **Before
  claiming "X causes the preference," list everything that differs between your two conditions; if ≥2
  differ, you cannot attribute the effect. Large effect size at small N is NOT robustness — it can be
  100% one uncontrolled confound.**
- **A "quick probe" that becomes a claim must retroactively pass this whole gate.** The moment a
  throwaway measurement starts feeling publishable / decision-grade, STOP and run it through Phase 0
  (prior art) + Phase 1 (controls) + `just power` *before* the claim, not after. We ran the embedder
  eval with full rigor but treated the judge probe as "just measuring" — and it produced a contested
  result. Rigor is triggered by how the result will be USED, not by what you called the script.
- **KB-absence / KB-structure as a gold label, when grading an agent with broad world knowledge
  against a PARTIAL store** (phenome KG-as-verifier, 2026-06-13 — the confound recurred 3× in one
  session). Only **affirmative defeaters** are valid world-truth golds: refutation, contradiction,
  staleness/supersession, positive multiplicity. Labels from store *absence* (uncited, n=0
  corroboration, "not in the KB") or *structure* (predicate promiscuity, out-degree) penalize correct
  knowledge the store happens to lack — closed-world confound; inverts model rankings
  (`arXiv:2209.08858`). Endpoint-recall, single-source, AND non-entailment-by-promiscuity were all
  confounded; only refuted/stale/contradicted survived. Corollaries: (a) the judge needs a
  **`GOLD_INVALID`** escape (both neutral judges agree the case label is wrong) or it merely
  *automates* the labeling error; (b) to score tool USE / traversal, read the **trace**, not the
  output text (output may be parametric recall); (c) judge/generator neutral-family to the
  system-under-test. Generalizes a closed-world rule (absence ≠ negative; UNASSESSABLE) to the
  grading layer. Ref impl: phenome `tests/evals/epistemics/` + ADR `docs/decisions/0008`.
- **Should-refuse / decline eval without an ENDORSE specificity foil · a LED judge · unpersisted traces**
  (phenome KG-verifier TRACE AUDIT, 2026-06-13 — all three caught only when the operator said "go look at
  the traces," AFTER a "16/16 decision-grade" verdict had been written + committed). A refusal eval that
  asks ONLY should-refuse questions measures *sensitivity*, not discrimination: if every "Is it established
  that X?" is a should-refuse, a model that **blanket-hedges on the phrasing** scores 100% with zero
  domain knowledge. The clean 16/16 was fully consistent with that. Three fixes, all required:
  - **Specificity foils** — identically-phrased cases whose correct answer is the OPPOSITE (definitive
    true pairs the SUT must ENDORSE, e.g. CFTR→cystic fibrosis next to refuted RYR2→ARVC). Discrimination =
    refuses-the-bad AND endorses-the-good; a blanket-hedger fails every foil (an `OVER_REFUSED` bucket).
    Without foils a high refusal-rate is uninterpretable. (This is the same specificity gap as a
    classifier reporting recall with no negative class.)
  - **De-lead the judge** — NEVER tell the judge "the correct behavior is to DECLINE" or hand it the
    seeded reason before it scores; that makes reason-match + agreement near-automatic and suppresses the
    `GOLD_INVALID` escape. Classify STANCE blind (question + response only); have the judge *independently*
    assess the claim's real-world status; compare to the seeded label in CODE, not in the prompt.
  - **Persist every trace by default** (prompt, full response, tool calls, raw judge output) — a verdict
    you cannot re-read is not verified. A CLEAN / PERFECT score is a trigger to READ traces, not a license
    to skip them (softball cases, a rubber-stamp judge, and leading phrasing all produce clean scores).
    No-verdict-on-unread-traces — the single most expensive lesson of the session.
  - **RECURRED 2026-06-14 (Cursor Composer extraction bakeoff):** a committed routing verdict
    ("52% mid-pack recall, sloppy over-generator needing a verifier") was overturned only after the
    operator said "check the traces." The 0/33 outlier was Composer correctly returning `[]` on a
    methodology doc the contract says to DROP — it was the ONLY contract-faithful arm; the gold +
    every other model were contract-violating. Same shape as 2026-06-13: aggregate trusted, outlier
    not read, gold not validated, judges' disagreement (24 vs 45 unsupported) laundered into one
    number. 2nd occurrence → promoted to the mandatory **Phase 4.5 Trace-audit gate** above.
- **A cheap proxy metric that isn't the objective — even a deterministic one** (extraction bakeoff,
  2026-06-13). Raw yield (claims/doc) ranked C>B>A and was the headline; the objective was *joinable
  graded* claims (graph-citizen/doc, the unit a verification substrate needs), which ranked B>C>A then
  C>B>A corpus-weighted — the proxy *inverted* the verdict. Deterministic ≠ valid: a span-count is
  still wrong if the objective is joins. **Operationalize the unit-of-value in Phase-1 Construct
  BEFORE picking the metric;** if the metric isn't the objective, it's an instrument failure.
- **Bulk eval dispatch on best-effort transport that swallows failures as empty** (the same bakeoff).
  `--flex` shed load as silent 503s under contention; the loop's `if rc!=0: return []` turned 7/8
  dropped chunks into "1 claim" (vs 22) — would have falsely sunk the winning arm. **Bulk dispatch
  must use reliable transport (`llmx batch`) or per-call retry-on-failure (retry rc≠0/timeout, never a
  genuine rc==0 empty), PLUS a deterministic validity guard for impossible results** (here:
  "chunked < whole-doc," cross-referenced against a hard-failure flag to separate corruption from the
  genuine fragmentation signal). Never `--fallback` in an eval (swaps the model mid-run).
- **Building a router/heuristic without bracketing it against the per-doc ORACLE** (same bakeoff).
  "Density-tiered routing (chunk dilute, leave dense whole)" looked principled; computing the oracle
  (per-doc best-of) showed naive chunk-all was within **2%** of the ceiling and a length-threshold
  router *underperformed* naive. **Before building a router, compute the oracle; if naive is within ε,
  the router is wasted complexity.**
- **Reporting the metric at the producer's stage, not the consumer's.** Pre-gate yield (16.5) and
  pre-resolver citizen% were upper bounds; the honest number is **quote-gated + post-resolver** (13.29
  → lower), the stage the consumer actually sees. Measure through the production pipeline, report at
  the consumer's stage.
- **Slow-feedback validation when a fast staged check exists** ([[feedback_prefer_faster_feedback]]).
  To answer "does it hold," a held-out sample returning in minutes beats a monolithic full run
  returning in hours. **Batch-async is the SLOWEST feedback** (opaque ≤24h) — never use it to *see if
  X holds*; stage validation (small held-out first → full run only if it holds).
- **LatchBio bio-agent benchmark audit (scBench/SpatialBench/SB-Long, 3 readers — 2 on code + 1 on
  papers — 2026-06-15; excellent constructs, flawed leaderboard). The anti-patterns:**
  - **Model×agent-harness estimand slippage — the confound that hides in AGENT bake-offs.** All three leaderboards
    rank models across DIFFERENT scaffolds (claude-code / mini-swe / codex / "pi"); the measured harness
    swing for one model was ~8× the model-to-model gap — the SCAFFOLD explained more variance than the
    model, so a MODEL ranking is uninterpretable. A configuration leaderboard is still a valid descriptive
    answer to "which exact deployable system?"; label it configuration-bound. A MODEL-effect claim must
    hold the harness constant or use a connected model×harness grid with interaction — never silently turn
    best-harness-per-model into a model ranking. (Same shape as critique_replay arms differing in
    model×effort×transport at once.)
  - **A pass window that admits a known wrong-method answer is not a discriminating grader.** Released
    numeric_tolerance windows were wide enough to pass the trap value the eval's OWN notes flag as wrong
    (n_significant GT=1 ±1 admits {0,1,2}; n_hvgs ±10000 passes any count). The tolerance must EXCLUDE
    every trap in the item's separation table by a stated margin — the GOOD per-item trap table (adopt it)
    is worthless if the window doesn't clear it.
  - **Replication you imply but don't deliver.** "3 runs" that are byte-identical (deterministic agents)
    buy ~zero variance; a CI over per-ITEM means is a between-item interval, not between-run — don't let a
    two-stage average launder one into the other, and FAIL any reported cell missing its interval.
    Item-is-the-unit is the correct PRIMARY choice (run-level CI alone underestimates), but report
    N-items/cell, don't slice below power, and with real replicate variance use a clustered SE.
  - **Answer/method text in a PUBLIC artifact field the SUT never sees.** A per-item canary GUID protects
    the DATA, but the specs embed full solution code + literal answers in a notes field → the next
    training scrape gets the answer key. Gold/method/answer strings must live OUTSIDE any field that ships
    publicly, prompt-bound or not.
  - **Withhold items for contamination, but NOT the distribution.** 6-public / 394-withheld with no strata
    counts makes both the public sample's representativeness and the hidden leaderboard unauditable —
    publish the strata counts even when you hold the items.
  - **Deterministic grading systematically under-rates your BEST model** (their deepest admitted threat):
    a fixed answer surface penalizes valid answers the authors didn't anticipate ⇒ false-negatives GROW
    WITH CAPABILITY. Generalizes absence≠negative to the grading surface — re-adjudicate high-rubric FAILS
    by hand; pair with the GOLD_INVALID escape.
  - **VariantBench delta (2026-07-16; paper-only release).** Real additions: publish the full
    category/subcategory counts; stage a plausible superset of input files so availability is not a hidden
    answer key; freeze one workflow at several stage boundaries; show real 0/3–3/3 item consistency. New
    anti-patterns: future-tense code/data at a 404 earns DESIGN credit only, never RESULT auditability;
    unparseable outputs rerun outside the denominator create an adaptive treatment unless capped/logged/
    charged; a static public-source suite with live internet ROTS; `p>0.05` on a sandbox ablation is not
    equivalence without a preregistered margin + paired effect interval. Do NOT "fix" that ablation by
    dropping items whose outcomes happened not to change — that conditions on the observed result; define
    any tool-dependent stratum from task requirements before outcomes. Finally, a real-patient exhibit is
    criterion evidence only to the level its primary sources support: the paper's vaccine-caused-remission
    wording exceeded both cited sources, so retain the pipeline stress case and drop the causal outcome claim.
- **Asserted negative-class gold + substring-matched free-text grading — BOTH fail, from one root, and
  cross-arm CONVERGENCE catches both** (critique_replay, 2026-06-15; ADR `evals/docs/decisions/0004`).
  A `clean`/`abstain`/`no-finding` gold label is a UNIVERSAL NEGATIVE ("no defect here") — the hardest
  claim — and was granted for free; an ensemble found real defects in 3/4 "clean" packets (the best arm
  took the worst invention penalty for being *correct*). The SAME run's DETECTION anchors were
  substring-brittle: a "universal capability MISS" was actually a universal HIT — every arm detected it,
  the anchor caught only ONE arm's phrasing ("propagate" vs "only its own opacity" vs "group opacity
  inheritance"; a backtick even breaks "find\` command"). Both biases run AGAINST the arms that phrase
  differently (often the cheaper ones), so the *ranking itself* is confounded by anchor-phrasing-fit.
  Fixes: **(1)** certify a negative-class item by **ensemble non-convergence** — admit it only if a
  DIVERSE (≥2 model-family) reviewer set fails to converge on a defect; DETERMINISTIC (cluster on code
  anchors — symbols/numbers/paths — never an LLM, so gold validity stays reproducible), a SCREEN not a
  proof (cross-family diversity bounds shared blind spots), conservative (false convergence shrinks the
  stratum — the safe error), and STANDING (re-certify every run; compose it with the false-alarm metric so
  d′/SDT REFUSE to compute over uncertified noise). **(2)** audit POSITIVE anchors the same way — an anchor
  that misses a defect the arms CONVERGE on is a paraphrase false-negative; but **do NOT iteratively widen
  anchors against the responses you're scoring** (that is gold-fitting). When substring anchors prove
  brittle, change the MECHANISM (semantic/judge detection, or convergence-as-detection: a defect is detected
  iff the finding lands in its cross-family cluster), don't patch. Ref impl: `critique_replay/convergence.py`
  (`certify_clean` + `audit_anchors`). This is absence≠negative + the under-rates-the-best-model anti-pattern
  above, pushed into BOTH gold strata and given a deterministic instrument.
