---
name: eval
description: "Use when: /eval, new benchmark/grader/judge, model bakeoff, auditing eval design. Pre-reg decision rule + power preflight. Modes: design, review. NOT spot-checks (/verify-before) or code diffs (/code-review)."
user-invocable: true
argument-hint: "[design|review] [question or eval path]"
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: medium
---

# Eval — design and scaffold benchmarks that can't fool you

Home base: `~/Projects/evals` (MACVB + standing bakeoffs + `evalcore` + scaffold).

## Why we run our own (operator framing, 2026-06-13)

Evals here exist to **speed up, parallelize, and buy confidence that tokens
aren't wasted — not to be stingy**. Two corollaries:

- **Materiality threshold:** a routing/config difference is worth measuring —
  or even thinking about — at **≥1.5–2×** (tokens, wall, or quality). Below
  that, take the default and move; optimizing sub-1.5× deltas costs more in
  attention than it returns. (Matches the measured landscape: gated-execution
  effort tiers differ 0.3–0.65×, i.e. 1.5–3× — material; same-tier rewordings
  ~1.0–1.04× — noise.)
- **Own-benchmark rule:** where literature exists, ADOPT its design (Phase 0);
  where it can't exist — frontier-local, per-release, per-rig properties like
  dispatch routing, effort knobs, harness/permission behavior, protocol
  compliance under failure — **your own eval is the only instrument there is**.
  Papers will always be a generation behind your rig.
- **Ride real work:** the cheapest substrate is work that must happen anyway —
  dispatch the licensed-lane pieces as preregistered arms and the tokens pay
  twice (evals/dispatch_deletion_edges is the pattern: 3 production deletion
  edges shipped AND extended the routing table).

**Sanity-check tier (below a full eval):** a ≤10-call probe with a written
1-line prediction, no scaffold, no DECISIONS row — for "does this lane even
work / does this knob even move" questions. Keep the artifact (script + outputs)
in the relevant eval dir or /tmp. The moment its result starts steering a
default, it must retroactively pass the full gate (see Anti-patterns: "a quick
probe that becomes a claim").
Methodology grounding: agent-infra `research/2026-06-11-eval-skill-and-evals-repo-improvements.md`,
`research/benchmarking-science-2026.md`, `research/2026-05-31-eval-benchmark-methodology-delta.md`.

**An eval is an instrument, not a script.** Most eval failures are instrument failures:
softball cases that can't discriminate, judges that see candidate names, N too small for
the claimed conclusion, golds nobody verified, results with no consumer. Every phase below
exists because one of those happened here.

## Where does this benchmark live? (phenome / genomics / intel agents read this first)

Two regimes — route by **cadence + entanglement + publishability**, the same rule
BENCHMARKS.md already states. Both already exist in the wild; don't collapse them.

| | Decision-grade bakeoff | Repo-coupled regression eval |
|---|---|---|
| **Question** | which model/engine/config? settle once | does my pipeline still produce correct output? |
| **Cadence** | run once, record verdict | run every dev loop / in CI |
| **Coupling** | low — reads prompts/data, owns no internals | high — tied to repo hooks/schema/pipeline |
| **Home** | `~/Projects/evals` via `just new-eval` | the repo's own eval home (below) |
| **Verdict** | DECISIONS.md row + production change | pass/fail gate in the suite |

**Each repo already has its own eval home — use it; do NOT funnel everything to evals/.**
The evals repo is specifically for *cross-cutting* model/engine/tooling-selection that spans
repos or is about generic agent infra. Domain and strategy benchmarks stay home:

| Repo | In-repo eval home | What goes there |
|---|---|---|
| **intel** | `~/Projects/intel-harness/` (backtest substrate; `bin/eval_proposed_rule.py`, walk-forward) | strategy/rule/thesis validation — has its own ruler-validity gate (`benchmark_validity()`). **NOT** evals/. |
| **genomics** | `benchmarks/` + `benchmark_catalog.py` + GIAB baseline + QA-gate AUPRC/AUROC thresholds | variant-calling accuracy, scoring-tool gates, latency |
| **phenome** | `eval/` (researcher-eval) + `tests/evals/epistemics/*.yaml` + `hook_mutation.py` | search/RAG quality, epistemic behavioral/calibration cases |
| **any** | `~/Projects/evals` via `just new-eval` | "which extraction model / search engine / retrieval backend" — cross-repo, settle-once |

So: `evals/extraction_bakeoff` benchmarks intel's *and* phenome's extract prompts from inside
evals/ (cross-cutting model choice), but an intel strategy backtest goes to intel-harness and a
genomics variant-accuracy check stays in `genomics/benchmarks`. The `/eval` **discipline**
(pre-registration, power, blind judges, invariant-claim split) applies in all of these homes
regardless of location.

**Tooling — NO symlinks for code.** The house pattern for shared Python is a package
in `substrate/packages/<pkg>` consumed via `path = "../substrate/packages/<pkg>",
editable = true` (how corpus-core / corpus-testing reach phenome+genomics). Symlinks
are only for data dirs and the AGENTS.md/GEMINI.md→CLAUDE.md doc mirrors.

- **evals-repo bakeoffs** get `evalcore` + scaffold + prereg guard for free (`evalcore` is an editable
  dep of evals/ — `import evalcore.stats` / `.judge` / `.leakguard` just works).
- **`evalcore` lives in `substrate/packages/evalcore`** (promoted 2026-06-13, ADR 0001 — phenome became
  the proven 2nd consumer). Pure-stdlib, zero-dep. To use it from ANY repo's in-repo eval, add to that
  repo's `pyproject.toml`: `"evalcore"` in `dependencies` + under `[tool.uv.sources]`
  `evalcore = { path = "../substrate/packages/evalcore", editable = true }`, then `uv sync`. Then import:
    - `from evalcore.judge import dispatch, assert_blind, lint_not_leading, lint_stakes_neutral, cyclic_assignment`
    - `from evalcore.leakguard import assert_no_gold_leak`  — call before EVERY system-under-test dispatch
    - `from evalcore.stats import wilson_ci, mcnemar_exact, cohen_kappa, holm_correction, point_biserial, benjamini_hochberg`
  Worked example: `phenome/tests/evals/epistemics/judge_refusal.py` runs `lint_not_leading` on its own
  judge prompt as a standing tripwire (the regression guard for its 2026-06-13 led-judge incident).
- **Add it WHEN an eval genuinely needs a primitive, not speculatively** — the proven-common bar still
  holds (vetoed-decisions): a repo whose evals consume none of it should NOT carry the dep. evals/ +
  phenome consume it today; genomics/intel add the line if/when an in-repo eval needs blind-judge /
  leak-guard / Wilson-κ / power. Still: NO symlinks, NO copying evalcore's code into a repo.

## Phase 0 — Dedup (before designing anything)

```bash
cat ~/Projects/evals/BENCHMARKS.md ~/Projects/evals/DECISIONS.md   # settled questions
grep -il "<topic>" ~/Projects/agent-infra/.claude/rules/vetoed-decisions.md
```
If the question is settled (extraction models, SaC routing, retrieval backend, judge
panels...), the answer is the DECISIONS.md row — don't re-run it. New evidence that a
verdict is stale → re-open via a new run, never by editing the old verdict.

**Also check the external prior art — for the DESIGN, even when the rates are stale.** A 2-minute
search (Exa/Perplexity for the named bias/benchmark + arXiv) tells you (a) whether a benchmark
already exists (don't reinvent — `JudgeBiasBench`, the SPB PIR/Null-PIR framework, etc. existed and
we nearly rebuilt them) and (b) **the controls the field already knows you need**. "Measure the live
model, papers lag the frontier" (frontier-timeliness rule) licenses re-measuring the *rate* on
current models — it does NOT license skipping the literature's *method*. Papers lag on rates but
LEAD on confounds: the controlled design (length-ratio control, truncation control, quality-matched
neighborhoods) is scale-independent and transfers. Skipping it is how you repeat a confound the field
solved two years ago (see the verbosity egg in Anti-patterns).

**For a structured fitness verdict on a candidate external benchmark, dispatch the `benchmark-rater`
agent** (global; preloads this skill + `model-guide`). It grounds the rate-vs-method call in real
sources (the paper, the scoring code, training-set membership) and returns **USE-AS-IS /
ADAPT-DESIGN-ONLY / REJECT** plus a **contamination–durability** sub-verdict (DURABLE / ROTS / NEVER
— does it rot as a standing instrument re-run per model release?). Use it before adopting a
third-party benchmark *and* before greenlighting a from-scratch build — its most common output,
ADAPT-DESIGN-ONLY with a precise BORROW list, is what stops both a needless rebuild and a naive
adoption of a rotting benchmark.

## Phase 1 — Design (the questions that decide if the eval should exist)

Answer in writing (they become PREREGISTRATION.md fields):

1. **Construct** — what ability/property, operationalized how? One sentence.
2. **Decision + consumer** — which production default / routing rule does the verdict
   change, and where is that recorded (DECISIONS.md row)? **No consumer → don't build.**
   *Criterion validity (the NASA-recruiter test):* name the real-world outcome the score is a
   proxy for — the way a selection test is only worth running if it predicts *job performance*,
   not test-taking skill (Schmidt-Hunter selection-validity literature). "Extraction F1" matters
   only insofar as it predicts pipeline usefulness; a benchmark you never check against the
   downstream outcome is a vanity metric, however internally clean. Where the criterion is
   measurable, validate against it; where it isn't yet (partial-verifier regime), say so and treat
   the score as a *bounded* proxy, not the target. (This is consumption-over-autonomy with a name.)
3. **Verifier regime** — deterministic ground truth (substring, recall@k, exact answer)
   or judged? Deterministic PRIMARY decides; judges corroborate. A model-as-judge proxy
   does not make taste work verifiable (constitution: bad eval is worse than none).
   *For retrieval/ranking:* is there exactly ONE relevant item per query, or can the corpus
   hold co-relevant siblings? One-gold recall@k is valid only in the former; topically-dense
   corpora need graded multi-doc relevance, or recall@k scores label noise (see Phase 3).
   *For free-text "did they identify X?" grading:* substring/anchor matching is paraphrase-brittle
   and biased against the arm that words it differently (critique_replay: a scored "universal MISS"
   was a universal HIT — the anchor caught one arm's phrasing). INVERT the default there — a blind
   dual-family judge (**cite-required**: a DETECTED with no quotable span is NOT_FOUND) is PRIMARY;
   substring + cross-arm convergence run as deterministic BACKSTOPS that FLAG (never silently override)
   disagreements for human resolution (evals ADR 0005). Three judge-transport gotchas that contaminated
   a real run *before* its verdict — all caught by reading traces, not buckets:
   - **INLINE the payload into the judge prompt; do NOT `-f`-attach it.** Under grading framing the judge
     silently mis-reads an attached file ("no reviewer findings were provided") though it IS delivered —
     reproduced deterministically. (Fix belongs in `evalcore.judge.dispatch`.)
   - **A "no findings" / JUDGE_ERROR verdict is TRANSPORT, not a miss** — read the rationale; SMOKE one
     packet before the batch (it caught two transport bugs before any spend; separate transport from capability).
   - **Judge competence is ASYMMETRIC — validate each judge against ground truth before trusting a panel.**
     Cross-family-PRIMARY routing assumes equal competence; a weaker judge (gemini-3.5-flash, forced temp=1.0)
     under-counts the arms it is primary for. κ + human-resolve-disagreements is load-bearing, not optional.
4. **Criterion over pipeline** — rubric/criterion design explains ~9× more judge-reliability
   variance than scoring architecture. Spend the hour on the rubric, not on a fancier panel.
5. **Contamination plan** — per-item provenance: `authored-fresh | post-cutoff |
   public-lifted`. Public items contaminate candidates AND judge memory. `authored-fresh`
   means the *exact text* is novel — NOT that the topic is; general-science/medical content is
   in every model's training data even when your composition isn't, so don't over-claim
   contamination-freeness.
   - **Valid gold for a claim/verification eval is AFFIRMATIVE, never absence.** A refuse/abstain/HOLD
     gold must come from a confirmed contradicting source, retraction, or supersession — NOT from
     "not in the store / NEI / no evidence found" (closed-world; inverts rankings). Every external
     claim-verification benchmark's NEI label is absence — do NOT lift it. (Canonical: phenome
     `reference_kb_grounded_eval_defeater_invariant` + ADR 0008; the SciFact/JudgeBench/COVID-Fact
     audits.)
   - **The strongest uncontaminated gold is a POST-CUTOFF VERDICT FLIP — harvestable, not just a tag.**
     A claim whose authoritative verdict flipped *after* the model's cutoff T is contamination-free
     *by construction* (the model can only have memorised the pre-flip verdict → it regurgitates the
     now-wrong belief) AND an affirmative defeater (anchored to a dated authority). That combination
     is the one thing no borrowed benchmark supplies. Harvest LIVE (recall forbidden — past your
     cutoff too) from dated-authority feeds filtered to `change_date > T`: Retraction Watch, the FDA
     DSC table, ClinVar delta, the CPIC `cpic-data` git log. Cite the primary dated record, not a
     blog's crawl date (mirrors re-surface old posts with fresh dates). This is intel-harness
     point-in-time with **T = the training cutoff**. Method + first harvest: `~/Projects/evals/docs/post-cutoff-flips/`.
   - **Enforce the flip-gold with the SEAL, not trust — and split judgment from retrieval.** Flip-gold
     is clean only if the SUT can't search its way to the post-T answer mid-eval, so pair it with
     `allow_internet=false` (the DeepSWE seal below): the airgap turns "we assume it didn't cheat"
     into "it provably couldn't." This also dissolves the "but it doesn't test web-browsing" objection
     by SCOPE: a *judgment*-over-a-staged-claim eval (adjudicate promote/hold/reject given an evidence
     **packet**) is packetizable + airgappable; *retrieval* ("find the right materials") is a SEPARATE
     capability where PIT-constraining a LIVE search is unsolved (URLs mutate in place at stable
     addresses, date metadata lies, engines have no as-of-T mode — intel-harness's unsolved web-PIT
     problem). Claim-verification ESCAPES that trap precisely because a claim+evidence bundle is a
     static object you curate as-of-T once; trading can't, its task is integrating an unbounded
     flowing stream. **Curating the packet enforces the PIT boundary by construction — don't try to
     PIT a live search.** If you must test retrieval, do it against a FROZEN snapshot (Wayback/Common
     Crawl at T) and state the coverage ceiling; don't pretend live fetch is as-of-T.
   - **Same-family confound — at EVERY model touchpoint** (generator / judge / reranker-fusion):
     any model that helps produce or score the eval's relevance signal must share no lab/family with
     any candidate. ≥2 neutral-family generators and judges (blinding does NOT protect — the bias
     rides the content of the grades); a candidate-family reranker informs, never gates. Measured
     incidents + mechanics: [references/anti-pattern-evidence.md](references/anti-pattern-evidence.md) §Phase-1.
   - **Cheap pre-screen before building an embedder bakeoff at all:** embed the corpus with both
     candidates, run a handful of queries through the *production* stack, measure top-10 overlap. **>~0.85
     ⇒ the swap is immaterial — don't build the full graded eval.** (v2 measured 0.89: through hybrid+rerank
     the two embedders returned ~9 of the same 10 docs. The full eval confirmed HOLD, but the overlap screen
     predicts "switching changes ~1 in 10" in minutes — run it at the §0 gate.)
   - **Frontier judge bias (measured 2026-06):** position/order bias is SOLVED on frontier judges —
     stop spending order-swaps/position-debias there. Same-lab judges share a style signature (a
     same-lab panel ≈ 1 effective vote; Bradley-Terry SE on it is false precision) → use cross-lab
     panels, read disagreement as signal. Our "verbosity bias" probe was RETRACTED (length-ratio
     artifact). Rates, arXiv refs, re-run controls: references/anti-pattern-evidence.md §Phase-1.
   - **Judge NOISE BUDGET — a single-trial judged number is PRELIMINARY** (distinct from bias):
     ~13.6% mean single-trial flip rate at frontier; for a decision repeat the judging (≥3) or
     PPI/PRECISE-correct; a same-lab multi-judge panel is NOT independent votes. Numbers + refs:
     references/anti-pattern-evidence.md §Phase-1.
6. **Invariant ambition** — what mechanism-level claim could this eval produce that
   survives a config swap? If only a local verdict is possible, fine — say so up front.

## Phase 2 — Scaffold

```bash
cd ~/Projects/evals && just new-eval <slug>
just power <N>            # paste output into PREREGISTRATION.md; declare SCREENING|CONFIRMATORY
git add <slug>/PREREGISTRATION.md && git commit   # prereg FIRST — the guard enforces this
```
Golds are **platinum**: mechanically checkable or human-verified. Never audit golds by
asking an LLM to re-check them (auditors re-solve and trust themselves: wrong-reference
detection 68%→9% at scale).

## Phase 3 — Discrimination probe (before budget)

`uv run python3 <slug>/run.py --probe` on ≤10 items. Required: a trivial-pass baseline
score AND one case that separates candidates. Both flat → fix cases, not N. (Evidence:
File-Search-vs-emb "parity" was title-matching softballs; discriminating rerun: 8/10 vs 4/10.)

**The probe is NECESSARY, NOT SUFFICIENT — eyeball misses + check gold validity.** A low
trivial-baseline rules out lexical leakage; it does not rule out label noise or
over-obfuscation. Before trusting ANY recall/nDCG/accuracy number:
- **Eyeball ≥10 actual misses** — read the query, the gold, and *what scored above the gold*.
  If the higher-ranked items are plausibly co-relevant/correct, your label is wrong: you are
  scoring **label noise as model failure** (and can penalize the BETTER system, which clusters
  co-relevant items). Cheapest validity check there is; the most-skipped. Watching aggregate
  ranks is NOT this — look at *what beat the gold*.
- **Single-gold → graded relevance on topically-dense corpora.** One-gold recall@k is valid only
  if exactly one item is relevant per query. If the corpus has sibling/overlapping items
  (multiple docs on a topic, near-dupes), collect a relevance *set* (LLM-judge the top-k union +
  human spot-check), score graded nDCG/MAP. A verdict that flips across analyst choices
  (generator, pool, window) is the tell that label noise ≫ signal.
- **Don't over-obfuscate to beat the baseline.** Aggressive keyword-stripping can push queries
  into unrealistic riddles that test abstraction, not retrieval — match the real query distribution.
(Evidence: bio_embedding_bakeoff 2026-06-11 — kw-baseline 0/12 looked rigorous, but **23/48
queries had the gold outranked by co-relevant sibling memos**; the single-gold recall@5 verdict
was *inconclusive*, surfaced only by eyeballing misses post-hoc — `audit_label_noise.py`.)

**This generalizes beyond retrieval — read the TRACES, not the buckets, for ANY eval, and ESPECIALLY
on a clean/perfect score.** Aggregate buckets are a proxy; a verdict on unread traces verifies the
arithmetic, not the construct. Persist traces by default (a harness that discards them is unauditable).
For judged refusal/decline/classification evals: read what the judge actually wrote (is its prompt
leading?), and read what the *opposite-label control* did (a refusal eval with no ENDORSE foil cannot
tell "refuses the bad" from "hedges on everything"). A perfect score INCREASES the obligation to read.
(Evidence: phenome KG-verifier 2026-06-13 — a committed "16/16 decision-grade" verdict had unread,
in fact *unpersisted*, traces; the trace audit found a led judge + no specificity control.)

## Phase 4 — Run + stats (evalcore does the discipline)

- Judges via `evalcore.judge.dispatch(..., blind_to=[all candidate names])` — blinding is
  enforced (raises), stakes-framing linted, temperature pinned. One strong judge + one
  diverse-family κ instrument; majority-of-panel is NOT truth (~2 effective votes).
  `cyclic_assignment` when judges × scenarios ≥ 2×2. Schema includes `confidence`.
- Rows via `evalcore.results.row/append_rows`; provenance via `provenance()` (prompt hashes).
- Report per-stratum, never only global. Paired comparisons: `paired_bootstrap_diff`,
  `mcnemar_exact` + `holm_correction`; `prob_superiority_beta` is the small-N primary readout.
- SCREENING declaration → lead with ranks + effect sizes + CIs; p-values secondary.

**Statistical canon** (Miller "Error Bars to Evals" + Biderman "Lessons from the Trenches", full-text in `agent-infra research/2026-06-14-eval-methodology-canon.md`) — the parts not already enforced above:
- **SE + n on every decision-grade number.** CLT `sqrt(Var/n)`; Bernoulli `sqrt(p(1-p)/n)` ONLY for strict 0/1 scores — it's WRONG (too wide) on F1/partial-credit/judge scores (the Llama-3 report shipped this error). A comparison without an SE is not decision-grade.
- **Cluster the SE when items are grouped** (shared passage, one prompt × N langs/paraphrases, multi-turn on one scenario) — up to **3.05× wider** on real data; an unclustered grouped CI lies about precision.
- **≥2 seeds/temps; report mean + variance; NO single-run headline** (Miller + Biderman + BetterBench: 14/24 benchmarks fail this). Cut variance by resample K=4–10 or next-token-probs — **never by lowering temperature** (that changes what you measure).
- **Separate format-compliance from correctness**: log RAW and extracted output; a regex extractor can 0-score a correct answer. Pin the harness (exact prompts + extraction code + model-version + commit) — a score without it isn't reproducible.

**Don't trust vendor leaderboards as rankings** (`research/2026-06-14-benchmark-leaderboard-methodology-critique.md`): LMArena's Bradley-Terry is sound but the board is structurally captured (Leaderboard Illusion — Meta tested 27 private variants; data-access = +112%); Artificial Analysis is a SOLID screen but 33% of weight flows through LLM judges (use per-axis, not the composite); CursorBench/OpenRouter measure cherry-pick/spend, not capability; SWE-bench **Verified ≫ original**. Steal the contamination-resistant DESIGNS (temporal holdout > canary > fuzzy-dedup), not the leaderboards.

## Phase 4.5 — Trace audit BEFORE the verdict (mandatory gate)

> Recurred 2× operator-forced (phenome KG-verifier 2026-06-13; Cursor Composer 2026-06-14 —
> both times a committed verdict was overturned only after "go look at the traces"). This is
> now a GATE, not advice: **no DECISIONS row, no committed verdict, until this audit is written.**
> A verdict from aggregates you didn't trace-check is a draft, not a result.
>
> **Hook-enforced (evals + phenome + genomics + intel, deployed 2026-06-14):**
> `pretool-eval-preflight.sh` BLOCKS any eval-runner (`run*/judge*/score/dispatch-arm`) that sits in
> an eval-design dir (an `EXPERIMENT.md`/`PREREGISTRATION.md` marker in its dir/parent, OR a path under
> an `evals?/`/`benchmarks?/`/`tests/evals/` segment) until the agent records a `<evaldir>/.preflight-ack`
> confirming the design checklist + these trace-audit pre-commitments. One confirm per eval; fails open.

**Mechanize checks 1–2 — run the item analyzer (don't eyeball the matrix).** Psychometric
item analysis catches the outlier/mis-keyed item that a human scanning a table misses. Emit your
response matrix as long-format JSONL (`{"model","item","score","scale_max"}`, one row per cell) and:

```bash
# evalcore evals: ZERO hand-emit — trials.jsonl IS the matrix (variant=model, item_id=item, scores)
uv run python3 ~/Projects/skills/eval/scripts/item_analysis.py --adapter evalcore <run_id>.trials.jsonl
# non-evalcore: emit long-format yourself  (or --adapter phenome|intel)
uv run python3 ~/Projects/skills/eval/scripts/item_analysis.py matrix.jsonl
```

It computes per-item **difficulty** + **discrimination** (corrected item-total r) + **top-model
dispersion** and prints a ranked **INSPECT** list. **Every flagged item must be trace-audited
before the verdict** — they are leads, not conclusions (at small N it says so). What the flags mean:
- `INSPECT-GOLD` (negative discrimination — the best models score *worst*) → the gold is likely
  mis-keyed/contaminated. This is the `diekstra` signature: composer's 0/33 was *correct*, the gold
  was wrong. The analyzer flags it #1 mechanically (validated 2026-06-14); you no longer have to be
  told "go look at the traces."
- `CEILING`/`FLOOR` (difficulty →1 / →0) → ~zero information; prune or replace (a saturated item
  carries no signal — the "injected-defect benchmark" failure mode).
- `TOP-DISPERSION` (high-ability models disagree) → ambiguous gold or a real capability split.

Normalize per `scale_max` (a 0–3 faithfulness scale is NOT a 0–1 recall scale — the analyzer's own
first bug). The analyzer is the front-end; the five checks below are the judgment it can't make:

**Adversarial cross-model complement (the spirit-audit).** item_analysis is mechanical on the
*matrix*; for the *traces*, run the integrity lens via a different-lineage model — it independently
catches contaminated gold, broken-arm-scored-as-result, confounds, and saturation (validated
2026-06-14: Composer, fed the traces blind, caught diekstra + corroborated the saturation finding).
`~/Projects/skills/analyze/scripts/spirit_audit.sh <PREREGISTRATION.md|EXPERIMENT.md> <trace_files>…`
fans Composer over the artifacts; or `/critique` with the `composer` axis. Lens: `analyze/lenses/spirit-audit.md`.

Run these five checks; record the result in EXPERIMENT.md §5 (or a `*_RESULTS.md § Spot-check`):

1. **Outliers first.** For each arm, list per-item scores, not just the mean. Any item far from
   the arm's others (e.g. recall 96/82/**0**) → READ THAT TRACE before averaging it in. A mean
   over a bimodal/outlier distribution is a lie ("52% mid-pack" was really 96%/82% + a correct `[]`).
   Tiny/near-empty outputs (a 1KB output among 30KB ones) are red flags, not data points.
   *(The item analyzer above ranks these for you; this check is reading the traces it points at.)*
2. **Is the GOLD/grader valid on contested items?** A model scoring 0 may be doing the RIGHT
   thing against a gold that violates its own contract. Verify: does the gold honor the task's
   own drop/keep rules? (Composer scored 0/33 by correctly dropping methodology claims the contract
   excludes — the gold + every other model extracted them = contract violation. The 0 was correct.)
   If the gold is wrong for a case, the metric is INVALID there — say so; don't rank on it. Pair with
   the judge's `GOLD_INVALID` escape (Anti-patterns).
3. **Inter-judge / inter-rater agreement.** Before reporting any judged number as ground truth,
   check whether judges agree on it. If they split materially (opus said 24 unsupported, gpt said
   45), report the RANGE and flag the arm as hard-to-judge — don't launder one judge's count into a
   verdict.
4. **Every arm appears in the OUTPUT.** Hardcoded model/candidate lists silently drop a newly-added
   arm even when its raw files parse fine. Confirm the new arm is in every summary table/row, not
   just on disk.
5. **Attribution honesty.** If the conditions you're contrasting differ in ≥2 ways (contract ×
   domain × prompt-length), you CANNOT attribute the effect to one of them — name the confounds
   (cross-ref the confound anti-pattern). State the mechanism evidence you DO have, separately from
   the correlation.

Cheap rule of thumb: **read ≥1 trace per arm and every outlier trace.** The cost is minutes; the
cost of a committed wrong verdict is a re-audit + a correction commit + lost trust (measured twice).

## Phase 5 — Verdict + invariant extraction

1. EXPERIMENT.md §6a **local verdict** (config-bound) → DECISIONS.md row + the production
   change (or explicit no-change). The eval is done only when that row lands.
2. EXPERIMENT.md §6b **invariant claims** — mechanism, invariant-to, transfer evidence or
   `UNTESTED-TRANSFER`. These rows are the publishable residue; a bakeoff with zero
   invariant rows is still useful, just not publishable. (Metrology precedent: in 2019 the
   kilogram was redefined from a drifting physical artifact — Le Grand K — to a fixed Planck
   constant, because a standard must be a durable INVARIANT not a perishable artifact. §6a
   local verdicts ARE the artifact that drifts; §6b mechanism claims are the invariant you keep.)
3. Deviations from prereg → §7 Limitations, explained, never silently absorbed.

## 2026-06 frontier adopts (digest)

Cross-axis convergence of 5 frontier memos: **outcome-only scoring is structurally
insufficient — verify the trace/structure.** One line per adopt below; the mechanics, arXiv
evidence, and the DeepSWE / LifeSciBench confirmations live in
[references/frontier-adopts.md](references/frontier-adopts.md) — read it before implementing any of these.

- **Isomorphic verifier** — for agentic/tool-use SUTs, score the trace (the path that *reaches* the verdict), not just the output.
- **Gold-leak guard** — `evalcore.leakguard.assert_no_gold_leak(sut_prompt, gold)` before EVERY SUT dispatch; hold out ≥30% of scoring dimensions.
- **Block mirror domains** — retrieval/web SUTs block `huggingface.co` / `paperswithcode.com` / benchmark mirrors (search-time contamination ~3–4% of queries).
- **Rubric decomposition before grading** — decomposed judges κ≈0.79 vs ≈0.51 holistic; never a holistic LLM judge as primary.
- **Item-quality flag + FDR** — `evalcore.stats.point_biserial` flags suspect items (investigation flag, never auto-gate); `benjamini_hochberg` is EXPLORATORY-only.
- **Read ≥5 traces** — ≥1 pass + ≥1 fail per top arm against the 4 questions (mirror-read / loophole / dangerous action / scaffold limit); cite verifiable trace anchors.
- **Metamorphic vocabulary** — state §6b invariants as `source_relation ⇒ output_relation`; the oracle-free invariance tier is discovery-only.
- **Q-matrix tags** — gold-only 3–5-dim capability ontology per case; do NOT fit IRT at N=10–60.
- **Deterministic-grader constructs** (LatchBio) — per-item separation table, sentinel gold fields, before-step snapshot gold, method-name suppression, reproduce-or-discard gold, cost+trajectory as first-class axes.
- **Measurement-science canon** — anchor-equate a drifting SUT (NEAT), SDT d′-vs-criterion split (`critique_replay/sdt.py`), proper scoring rules for confidence outputs, RoB-2-style graded pre-flight.
- **Peer prediction (gold-free scoring)** — `evalcore.elicit` + anchor jury; validated ρ=1.0 vs gold ordering; FAILS under ≥50% colluding pool (enforced in code, never assumed).
- **Capability is the LAST-RESORT hypothesis** — a score is capability evidence only after contamination/shortcut/memorization are affirmatively excluded (named hard gate).
- **Verdict = machine-checkable gate-ledger** — evals ADR 0007 + `scripts/check_verdict.py`; confidence/call is EARNED by discharged gates; a `pass` must cite a leaf.
- **Guards** — PPI/CLT-PPI invalid below 50 labels/stratum (`just power` refuses); fitted IRT / CapBencher / CAT / noise-injection sandbagging stay deferred (`evals/docs/decisions/deferred-and-open.md`).
- **Process reflex** (extends Pre-Build #1) — before inventing a metric or grading scheme, inventory the measurement sciences for the existing instrument.

**Independently confirmed** by DeepSWE (withheld grader; seal-the-env-or-domain-block; the
free-executable-oracle boundary — don't cargo-cult behavioral verifiers into oracle-free domains)
and LifeSciBench (strong construct ≠ transferable ranking; grader-named-or-fail;
validation-printed-or-unvalidated). Full teardowns in the reference file.

## Review mode

Given an existing eval dir: check each phase artifact exists and bites — prereg committed
before results (`git log --follow`), power declaration matches N, probe evidence present,
**misses eyeballed** (what outranks the gold, not just aggregate ranks) + **single-gold
validity** on dense corpora, judge payloads blind (grep for candidate names in judge
prompts/payload builders), per-stratum tables, DECISIONS.md row, §6b filled or explicitly
empty. Report gaps as a table; fix all confirmed gaps, not top-N.

**Grading an EXTERNAL / vendor benchmark** (the `benchmark-rater` agent inherits these — it loads this
skill; LifeSciBench teardown 2026-06-18, `evals/research/2026-06-18-lifescibench-rating.md`):
- **Grade DESIGN and RESULT separately — they earn different verdicts.** A provider self-eval's construct +
  rubric can be genuinely borrow-worthy while its RANKING is non-transferable (the launch model tops a
  self-graded board). ADAPT-DESIGN-ONLY is the common right answer; never carry a vendor ranking to a
  DECISIONS row until an independent cross-lab grader reproduces it.
- **Grader-named-or-fail.** If a model-graded benchmark does not NAME the grader model in the paper, treat
  judge family-neutrality as FAILED by default — you cannot rule out a same-family judge. (LifeSciBench's
  grader is GPT-5.5, same family as the winning GPT-Rosalind, and surfaces only in a press quote; the paper
  says merely "model-assisted grading, where used.")
- **Validation-printed-or-unvalidated.** A grader-validation study that is DESCRIBED but whose human-agreement
  numbers (κ / correlation / MAE) are not PRINTED counts as unvalidated — don't credit it. (LifeSciBench §5.3
  promises "we report correlation, MAE, pass/fail agreement"; no value appears in the paper.) "Expert-authored"
  via an anonymous/withheld contributor pool (the DRACO pattern) is likewise face validity you cannot audit.

## Anti-patterns (each one vetoed or observed here)

Pattern + lesson inline; the full war stories, incident dates, arXiv refs, and ref-impls live in
[references/anti-pattern-evidence.md](references/anti-pattern-evidence.md) — read the entry before
re-litigating or rebuilding anything named here.

- **Composite quality scores / standing leaderboards** — vetoed 2× (session_quality, Arena-transfer).
- **Judge panels as truth** — judge sees engine/model identity; consequence-framing in judge prompts.
- **Single global accuracy** — hides the unreliable stratum (PARTIAL-type strata drive disagreement).
- **Items lifted from public benchmark sets** without per-item justification.
- **Trusting ABSOLUTE scores on a reused test set** — reuse inflates absolutes while RANKINGS stay robust; trust ranking flips, refresh items, anchor-equate.
- **N chosen by vibes** — run `just power` and declare SCREENING|CONFIRMATORY.
- **Eval with no consumer** — a verdict that never reaches DECISIONS.md or production.
- **LLM re-audit of gold labels; editing a prereg decision rule after results exist.**
- **Single-gold recall@k on a corpus with co-relevant siblings** — scores label noise as model skill.
- **Trusting aggregates without reading one failure; over-obfuscated riddle-queries** that beat the keyword baseline but don't match the real query distribution.
- **Controlling *a* confound, not *the* confound** — if ≥2 variables differ between conditions you cannot attribute the effect; a large effect at small N can be 100% one uncontrolled confound.
- **A "quick probe" that becomes a claim** — must retroactively pass Phase 0 + Phase 1 + `just power` BEFORE the claim; rigor is triggered by how the result is USED, not what you called the script.
- **KB-absence / KB-structure as gold** — only affirmative defeaters (refuted / contradicted / stale / superseded) are valid world-truth golds; absence labels invert rankings; the judge needs a `GOLD_INVALID` escape.
- **Should-refuse eval without an ENDORSE foil · a LED judge · unpersisted traces** — refusal-only measures sensitivity, not discrimination (a blanket-hedger scores 100%); classify stance blind; persist every trace — a CLEAN score raises the obligation to read.
- **A cheap proxy metric that isn't the objective** — deterministic ≠ valid; operationalize the unit-of-value in Phase-1 Construct BEFORE picking the metric.
- **Bulk dispatch on best-effort transport that swallows failures as empty** — reliable transport (`llmx batch`) or per-call retry, plus a deterministic validity guard for impossible results; never `--fallback` in an eval.
- **Router/heuristic without the per-doc ORACLE** — compute the oracle first; if naive is within ε, the router is wasted complexity.
- **Reporting the metric at the producer's stage** — measure through the production pipeline; report at the consumer's stage.
- **Slow-feedback validation when a fast staged check exists** — batch-async (opaque ≤24h) never answers "does it hold"; stage a small held-out first.
- **LatchBio leaderboard class** — model×harness confound (hold the harness constant or report a 2-factor grid); tolerance windows must exclude every trap in the separation table; byte-identical "3 runs" ≠ replication; answer text in public artifact fields leaks to the next scrape; withheld items still need published strata counts; deterministic grading under-rates the BEST model (re-adjudicate high-rubric FAILS).
- **Asserted negative-class gold + substring-matched free-text grading** — certify a negative item by cross-family ensemble NON-convergence; audit positive anchors for paraphrase false-negatives; never widen anchors against the responses you're scoring.

### /eval skill vs evals repo (recurring question — settle it here)
They're different KINDS of thing; keep SEPARATE, neither collapses into the other. **This skill =
portable DISCIPLINE** (phases/gates/anti-patterns; auto-loads in every project; light, project-
agnostic — "how to think"). **`~/Projects/evals` = cross-cutting INFRA + verdicts + data** (`evalcore`
with deps, `just new-eval` scaffold, `DECISIONS.md`/`BENCHMARKS.md`, run JSONs — "where bakeoffs
live"). A skill can't carry a Python package + run data + a live registry (bloats every context load);
and the skill must auto-load in phenome/genomics/intel, which it can't if it lives only in evals/. So
the skill *cites* repo examples as pointers, never embeds. **Lesson-flow boundary:** methodology →
this skill; reusable code → `evalcore` *iff* a 2nd consumer (else the eval dir); verdicts →
DECISIONS/RESULTS.
