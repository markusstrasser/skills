---
name: eval
description: "Design, scaffold, and run decision-grade evals/benchmarks/bakeoffs the careful way: construct + consumer named, pre-registered decision rule, power preflight, discrimination probe, blind judges, invariant-claims extraction. Use when creating ANY eval/benchmark/grader/judge, comparing models/engines/configs, or reviewing an eval design. Modes: design (default), review (audit an existing eval against the checklist)."
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

## Phase 1 — Design (the questions that decide if the eval should exist)

Answer in writing (they become PREREGISTRATION.md fields):

1. **Construct** — what ability/property, operationalized how? One sentence.
2. **Decision + consumer** — which production default / routing rule does the verdict
   change, and where is that recorded (DECISIONS.md row)? **No consumer → don't build.**
3. **Verifier regime** — deterministic ground truth (substring, recall@k, exact answer)
   or judged? Deterministic PRIMARY decides; judges corroborate. A model-as-judge proxy
   does not make taste work verifiable (constitution: bad eval is worse than none).
   *For retrieval/ranking:* is there exactly ONE relevant item per query, or can the corpus
   hold co-relevant siblings? One-gold recall@k is valid only in the former; topically-dense
   corpora need graded multi-doc relevance, or recall@k scores label noise (see Phase 3).
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
   - **Cheap pre-screen before building an embedder bakeoff at all:** embed the corpus with both
     candidates, run a handful of queries through the *production* stack, measure top-10 overlap. **>~0.85
     ⇒ the swap is immaterial — don't build the full graded eval.** (v2 measured 0.89: through hybrid+rerank
     the two embedders returned ~9 of the same 10 docs. The full eval confirmed HOLD, but the overlap screen
     predicts "switching changes ~1 in 10" in minutes — run it at the §0 gate.)
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
> **Hook-enforced (evals project, piloted 2026-06-14):** `pretool-eval-preflight.sh` BLOCKS any
> eval-runner (`run*/judge*/dispatch-arm` in a dir with `EXPERIMENT.md`) until the agent records
> a `<evaldir>/.preflight-ack` confirming the design checklist + these trace-audit pre-commitments.
> One confirm per eval. Propagation to phenome/genomics/intel = pending (3+ projects → approval).

Run these five checks; record the result in EXPERIMENT.md §5 (or a `*_RESULTS.md § Spot-check`):

1. **Outliers first.** For each arm, list per-item scores, not just the mean. Any item far from
   the arm's others (e.g. recall 96/82/**0**) → READ THAT TRACE before averaging it in. A mean
   over a bimodal/outlier distribution is a lie ("52% mid-pack" was really 96%/82% + a correct `[]`).
   Tiny/near-empty outputs (a 1KB output among 30KB ones) are red flags, not data points.
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
   invariant rows is still useful, just not publishable.
3. Deviations from prereg → §7 Limitations, explained, never silently absorbed.

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

**Guards (the frontier also tells you what NOT to adopt at our N):** PPI/CLT-PPI label-saving is
statistically invalid below 50 labels/stratum (GLIDE `arXiv:2605.31278`) — at ~20/stratum, hand-label
all + bootstrap; `just power` refuses PPI/R² sizing below the threshold. Fitted IRT, CapBencher,
CAT/LEGO-IRT, noise-injection sandbagging: deferred — see `evals/docs/decisions/deferred-and-open.md`.

## Review mode

Given an existing eval dir: check each phase artifact exists and bites — prereg committed
before results (`git log --follow`), power declaration matches N, probe evidence present,
**misses eyeballed** (what outranks the gold, not just aggregate ranks) + **single-gold
validity** on dense corpora, judge payloads blind (grep for candidate names in judge
prompts/payload builders), per-stratum tables, DECISIONS.md row, §6b filled or explicitly
empty. Report gaps as a table; fix all confirmed gaps, not top-N.

## Anti-patterns (each one vetoed or observed here)

- Composite quality scores / standing leaderboards (vetoed 2×: session_quality, Arena-transfer)
- Judge panels as truth; judge sees engine/model identity; consequence-framing in judge prompts
- Single global accuracy hiding the unreliable stratum (PARTIAL-type strata drive disagreement)
- Items lifted from public benchmark sets without per-item justification
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
