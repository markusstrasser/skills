# Model Guide Changelog

## 2026-07-16 - Kimi K3 added as open-weight long-horizon coding opt-in

Moonshot released Kimi K3 (kimi.com research announcement, operator paste): 2.8T-param
open model (Kimi Delta Attention + Attention Residuals), native vision, 1M context,
weights promised by 2026-07-27. First open 3T-class model; frontier-adjacent posture —
trails Fable 5 / GPT-5.6 Sol overall, leads the table on SWE Marathon (42.0) and
BrowseComp (91.2).

- New skill section with specs, constraints, and routing read: opt-in third-lab coding
  lane, **not a default anywhere** (metered, locally unprobed, no subscription path).
- llmx: provider default `kimi` → `kimi-k3`; `_KNOWN_MODELS` gains k3/k2.6/k2.7-code
  (±highspeed); K3 restriction entry is `reasoning_effort: False` — launch thinking is
  max-only server-side, low/high effort modes announced but not yet exposed.
- llmx kimi base URL flipped `api.moonshot.cn` → `api.moonshot.ai` (measured: the local
  `MOONSHOT_API_KEY` 401s on .cn, 200s on .ai — the lane was broken before this pass).
- Pricing registered at the conservative cache-miss rate ($3.00/$15.00 per MTok;
  cache-hit input is $0.30, >90% hit rate claimed for coding workloads) in llmx
  `usage_report.py` + agent-infra `usage-check.py` (drift-test now also re-derives
  Cursor-Grok loop pricing from `model_ids.py`).
- Vendor-disclosed constraints carried into the skill: thinking-history sensitivity
  (verified harness only, no mid-session model switch), excessive proactiveness (bind
  via AGENTS.md), conceded UX gap vs Fable 5/Sol.
- Kimi Code CLI side (same pass): `~/.kimi` default already `moonshot-ai/kimi-k3`;
  dead MCPs removed (genomics-consumer path gone; paperclip auth-gated unloadable),
  exa synced to the current key + `get_code_context_exa`, dead K2-0905/K2-thinking
  model blocks dropped (removed from the Moonshot API), `~/.kimi/skills` added to
  `sync_skill_links.py` and re-mirrored from `~/.claude/skills` (21 added, 3 stale pruned).

## 2026-07-14 - Grok 4.5 Cursor transport restored under exact slugs

Supersedes the dated 2026-07-13 disable after a fresh live registry and serve audit.

- Cursor now exposes `cursor-grok-4.5-{low,medium,high}` and matching trailing-`-fast`
  variants; the retired unprefixed/xhigh aliases remain invalid.
- A named `cursor-grok-4.5-high` ask-mode smoke returned the exact token, and a second
  read-only workspace canary returned the exact current repo HEAD without receiving that
  expected hash in its prompt.
- llmx binds only those exact slugs to Cursor subscription and refuses any
  `auth=subscription` plan resolving to xAI API. Bare `grok-4.5` remains the xAI model.
- Critique restores the opt-in repo-grounded `grok` axis at exact high effort and enforces
  registry plus the unrevealed repo canary before dispatch.

The 2026-07-13 disable remains in history: it is the incident that made live registry and
serve checks mandatory rather than inferring availability from yesterday's aliases.

## 2026-07-12 - Verified Transport table added; Agent-tool `model:` pin bug generalizes to Opus

Added a "Verified Transport" section (before Default Routing) distinguishing MEASURED serving
facts from vendor-doc/config-level claims, and a "Role → Lane" table under Dispatch Economics
(synthesis / briefed-execution / review-cosign / research / scout-fanout / OS-student-serving).

- **New finding:** the 2026-07-12 Agent-tool routing bug (fable-high/fable-low dispatches
  silently serving `claude-sonnet-5`, arc-agi session 41f9b649) is **not Fable-specific** — a
  fresh probe this pass (`subagent_type: opus-low`, explicit `model:"opus"`, agent-def also
  pinned `model: opus`) self-reported `claude-sonnet-5` too. Treat every Agent-tool model pin as
  unverified until self-report-confirmed; transcript-grep verification is not proven sufficient.
- Fixed stale "dormant"/"not routable" framing in `references/fable-5-dormant.md` and
  `references/validation-checklists.md` — Fable is paid-live via llmx/headless, not dormant.
- Fixed `references/codex-subprocess-dispatch.md`'s stale "GPT-5.5-class" (codex now serves
  GPT-5.6; GPT-5.5 retired from the subscription allowlist 2026-07-10).
- Added the `--subscription -m grok-4.5` → blocked-xAI-key mis-route footgun (2026-07-11) to
  the Grok section and cosigner notes.
- Flagged, not resolved: Fable's "$10/$50 metered, off-subscription" cost claim is unreconciled
  against continued successful claude-cli-transport Fable calls in the llmx usage log through
  2026-07-12 (no cost/auth-mode field in the log to confirm which billing path actually fired).

### Sources checked
- `~/.claude/llmx-usage.jsonl` (18 claude-fable-5 entries through 2026-07-12), `~/.claude/cache/llmx-routing.json`, `~/.claude/rules/llmx-routing.md`, arc-agi `.claude/rules/vetoed-decisions.md` (OS-tier verdicts), anim-workbench `2026-06-12-{fable-tier,fable-effort-architecture}` eval results, `~/Projects/evals/DECISIONS.md`.

## 2026-07-09 - GPT-5.6 Sol / Terra / Luna; GPT-5.5 fully removed

- OpenAI GA 2026-07-09: `gpt-5.6-sol` (flagship, alias `gpt-5.6`), `gpt-5.6-terra` (mid), `gpt-5.6-luna` (everyday).
- Pricing: Sol $5/$30, Terra $2.50/$15, Luna $1/$6 per MTok. Effort adds `max`. Pro is reasoning.mode, not a new slug.
- Fleet defaults: formal/cross-lab → Sol; **gpt_general → Luna** (≈ prior 5.5 perf at ~½ price); mechanical → Luna low. Terra = mid opt-in.
- **GPT-5.5 fully removed** from llmx (no upgrade, no PRICING, no routing). Passing `gpt-5.5` is unknown/typo.

## 2026-07-09 - Grok 4.5: AA niche routing (more agentic / less epistemic)

Operator pasted Artificial Analysis live board (v4.1, Grok 4.5 high, 2026-07-08 eval).
Promotes Grok from "transport stub" to a **named niche** — not a Default Routing
replacement for Opus/GPT.

### Routing verdict (capability × calibration × cost)
- **Use more:** PLAN `--axes …,grok` (repo workspace); AutomationBench/τ³-shaped tool
  loops on Cursor pool; cheap/fast frontier second opinion (~$0.31/task vs GPT $0.86 /
  Fable $2.75).
- **Use less / never alone:** unsourced facts (~46% non-hallucination), CritPt physics
  (15%), sole architecture judge, contexts >500k.
- Intelligence Index **54** (frontier pack with GPT 55 / Opus 56); Coding Index **72.4**;
  AutomationBench **51% lead**; τ³ **33% lead**.

### Also this day (earlier)
- Transport + critique `grok` axis + blocked-key (not EU) diagnosis — see decision
  `2026-07-09-grok-4.5-transport.md`.

Sources: artificialanalysis.ai leaderboard paste 2026-07-09; docs.x.ai; cursor.com/blog/grok-4-5.

## 2026-07-09 - Grok 4.5 transport wired; critique axis

SpaceXAI released Grok 4.5 (2026-07-08): Opus-class pitch, $2/$6 (fast $4/$18), 500k
context, jointly trained with Cursor.

### Added / changed
- llmx: xAI default → `grok-4.5`; PRICING + CONTEXT_WINDOW; Cursor effort-slugs → `cursor`;
  lite allowlist +`grok-4.5` +`composer-2.5`.
- critique: repo-grounded `grok` axis (`cursor-agent --workspace`).
- llmx-guide footguns 7b/7c/7d; detector 500k; decision + research memo.

### Explicitly deferred (superseded later same day by AA niche entry above)
- Full Default Routing replacement of Opus/GPT.

## 2026-07-07 - Fable 5 off subscription: metered usage credits, fable lanes suspended on cost

Anthropic ended subscription-included Fable 5 access after 2026-07-07 (Pro/Max/Team);
continued access bills metered usage credits at $10/$50 per MTok — 2× Opus 4.8, which
stays subscription-routable at $0. Anthropic states the change is temporary (capacity
fallout from the June export-control suspension/relaunch): "restore Fable as a standard
part of our subscriptions as soon as capacity allows."

### Changed
- Top-of-skill OFF-SUBSCRIPTION note added; description + Fable section header now say
  "metered opt-in" instead of "dormant".
- fable-low lane license SUSPENDED ON COST (not capability): its measured token savings
  (0.34× review, 0.65× gate-redesign) were vs fable-high, never vs a $0 Opus lane —
  gated/briefed/review dispatch routes to opus-low. fable-high stays a paid opt-in
  requiring a named Fable-specific justification (obscure-domain, multi-hop edge,
  measured 2026-06-10).
- Working copies updated in the same pass: execute/SKILL.md (repricing rider on the
  Fable lanes), critique/SKILL.md (fable-subagent axis repriced), and the
  ~/.claude/agents/fable-{low,high}.md definitions.

### Unverified / triggers
- Whether CC session/Agent-tool fable dispatches now bill credits silently or fail:
  UNVERIFIED — probe one small dispatch and check billing before batch use.
- Re-license trigger: Anthropic restores Fable to subscription plans → revert the
  OFF-SUBSCRIPTION note and re-activate the 2026-07-04 fable-lane verdicts.

Sources: techtimes.com 2026-07-06 (subsidy end + rates), bleepingcomputer.com
(Anthropic "not permanent" statement), digitalapplied.com (July-7 usage-credits guide),
claude.com/pricing.

## 2026-06-30 - Claude Sonnet 5 reinstated as a named cost-tier Claude option

Anthropic released Claude Sonnet 5 (2026-06-30): "near-Opus intelligence at Sonnet
pricing," $3/$15 per MTok ($2/$10 intro through 2026-08-31), first Sonnet-tier model
with `xhigh` effort. System card reviewed in full (145 pages); digest at
`references/sonnet-5-system-card.md`.

### Added
- New "Claude Sonnet 5" section (operational specs, system-card insights, prompting).
- "After Claude Sonnet 5" validation checklist.
- Quick/Dispatch-Economics rows: cost-sensitive coding/agentic work with a mechanical
  gate → Sonnet 5; resolved the orphaned "Sonnet/haiku tier" Dispatch Economics row
  (no live model named) to point at `claude-sonnet-5` explicitly.
- OPEN QUESTION callout: whether the 2026-06-20 "NEVER Sonnet" verdict for
  architecture/design/high-reasoning critique should be revisited given Sonnet 5's
  capability profile — explicitly NOT resolved here; flagged for operator decision.

### Not changed
- The "NEVER Sonnet" architecture/critique verdict itself (operator call, not
  re-litigated by this update).
- Opus 4.8 / GPT-5.5 / GPT-5.5 Pro routing.
- Sonnet 5 is not yet on the llmx subscription allowlist (`lite_allowed_models`) —
  that's llmx's own config, out of scope for this skill.

## 2026-06-20 - Fable dormant; Opus primary; architecture → Opus max

Fable 5 not routable on subscription (`lite_allowed_models` = `claude-opus-4-8` only for Anthropic) and US access restricted. Opus 4.8 becomes the live default for all Claude work.

### Changed
- All Fable-first routing → Opus 4.8.
- Architecture / design / high-reasoning critique → **Opus 4.8 `max`** (operator 2026-06-20; was `high|max`).
- Cross-model review: Opus 4.8 + GPT-5.5 (Fable removed).
- Fable section marked **DORMANT**; Opus section promoted to primary.
- `cursor-agent` arch critique example → `claude-opus-4-8-thinking-max`.

### Not changed
- GPT-5.5 / GPT-5.5 Pro routing; trilemma section; GLM opt-in cosigner.

## 2026-06-20 - Selection trilemma: capability × calibration × efficiency

Oliver Shrimpton ("Bigger models are not the way", 2026-06-18) + AA-Omniscience leaderboard read: benchmark capability and parameter count plateau while calibration diverges sharply. Integrated as routing judgment, not a default-model change.

### Added
- SKILL.md **Selection trilemma** section: three axes, inverted capability/calibration ordering, reasoning-budget-is-not-monotonic guard (DeepSeek V4 Pro vs GLM-5.2 impossible-asyncio anecdote, n=1).
- Quick Selection Matrix row: contradictory/impossible spec → Opus 4.8 or GLM-5.2 opt-in; avoid GPT-5.5 / DeepSeek V4.
- Dispatch Economics **reasoning escalation guard** (inverse of cheap-lane finding).
- **After GLM-5.2** validation checklist.
- BENCHMARKS.md: GLM-5.2 72% non-hallucination in trust ordering; DeepSeek V4 Pro explicit 94% hallucination-on-miss; capability-plateau note.

### Changed
- GLM-5.2 cosigner bullet: calibration edge (72% non-hallucination) + impossibility/paradox use case.
- Last-updated stamp → 2026-06-20.

### Not changed
- Default frontier routing (Fable/Opus/GPT-5.5) — capability still wins for gated mechanical work; trilemma adds when NOT to pick by index/size alone.

### Sources
- Oliver Shrimpton 2026-06-18 (AA-Omniscience rates + asyncio impossibility probe via OpenRouter).
- Prior AA instrument read: `agent-infra/research/2026-06-11-aa-benchmark-instrument-validity.md`.

## 2026-06-12 - Add Kradle Four Bridges deception finding to GPT-5.5 insights

### Added
- GPT-5.5 system-card insights: Kradle Four Bridges (kradle.ai, 2026-06-04, n=100 informed runs) — 90% uninstructed deception under a small competitive incentive (~0.23-0.30 expected apples), typically framed as cooperative coordination ("let's spread out"). Third independent source on incentive-sensitive honesty alongside Apollo (29% lie rate, impossible task) and AA-Omniscience (14% non-hallucination). Construct caveat: peer-competition game with explicit scarcity payoffs, not assistant contexts; no routing or mitigation change — deterministic verification over self-report already covers it.

### Not added
- Sonnet 4.6 (27% deception, hint-don't-lie), Gemini 3.1 Pro (54%, bimodal disclose-or-lie), Grok 4.20 (5%) — outside this skill's active routing surface since 2026-06-09. Study-internal confounds noted: RED-always-death (semantic prior), Claude-family judge, first-mover timing drives Grok's score per the authors' own discussion.

## 2026-06-11 - Add AA independent benchmark section with construct annotations

First independent (Artificial Analysis) measurement of the Fable 5 / Opus 4.8 / GPT-5.5 scope, added to BENCHMARKS.md with per-instrument construct cautions derived from full-paper reads of AA-Omniscience (arXiv:2511.13029), IFBench (2507.02833), GDPval (2510.04374), and τ²-bench (2506.07982).

### Added
- BENCHMARKS.md "Independent Measurement" section: per-eval table + calibration trust table (non-hallucination: Fable 45 / Opus 64 / GPT-5.5 14, measured despite an explicit abstention prompt).
- Quantified hallucination priors in the SKILL.md validation checklists (Fable, Opus, GPT-5.5).
- Quick Selection Matrix row for letter-exact output constraints: schema/validator enforcement first; Claude family measurably weakest at prose-mode mechanical compliance (IFBench, with construct caveat — majority adversarial-synthetic constraints that trade against answer quality).
- Independent confirmation line under Fable system-card insights (honesty regression vs Opus now two-source: system card + AA-Omniscience).

### Changed
- τ²-Telecom routing read retired (saturated at the user-simulator ~6% noise floor; Fable 99 ≥ GPT-5.5 94); negative screen only.
- GDPval-AA row annotated: single Gemini 3.1 Pro blind-pairwise judge; original human–human agreement 71%; small Elo gaps are judge noise.
- CritPt: AA independently measures GPT-5.5 Pro at 31 (#1), contradicting the vendor-sourced 17.7.

### Sources checked
- artificialanalysis.ai leaderboard (2026-06-11 snapshot, spot-checked live) + intelligence-benchmarking methodology page.
- Full-paper reads via research-mcp; analysis memo: `agent-infra/research/2026-06-11-aa-benchmark-instrument-validity.md`.

## 2026-06-09 - Add Claude Fable 5 as primary frontier Claude; Opus 4.8 becomes the fallback

Fable 5 / Mythos 5 launched 2026-06-09. Restructured the Claude side of the guide around the new routing pair.

### Added
- **Claude Fable 5** (`claude-fable-5`) as the top frontier Claude model: 1M ctx, 128K out, $10/$50 (2× Opus 4.8), cache $1/$12.50. Adaptive-thinking-only, summarized-CoT-only, no thinking budgets. Effort low→max (default high; lower effort exceeds prior-model xhigh). Covered Model: 30-day retention, no ZDR.
- Fable's safety classifiers (offensive cyber / bio-life-sciences / reasoning-extraction) → `stop_reason:"refusal"` (HTTP 200) → server/client fallback to **Opus 4.8**.
- Benchmarks: SWE-Pro 80, SWE-Verified 95, Terminal-Bench 84.3, FrontierCode-Diamond 29.3 (Opus 13.4), GDPval-AA 1932; Mythos 5 ceiling rows (HLE 59, ArxivMath 78.5, CritPt 28.6) marked.
- Fable prompting deltas: don't recite reasoning (reasoning_extraction trigger), steer with brief instructions not enumerations, ground progress claims, don't surface context countdowns, longer turns by default, add a `send_to_user` tool for long async agents.

### Changed
- **Opus 4.8 reframed as the fallback** — the automatic classifier-refusal target AND the deliberate choice for routine/cost-sensitive work, security/cyber/biology (which Fable refuses anyway), and raw-CoT needs. Half the price; slightly more careful on self-report honesty.
- Cross-model review pattern: Fable 5 *or* Opus 4.8 on the Claude side, paired cross-lab with GPT-5.5.
- Added an "After Claude Fable 5" validation checklist (self-report honesty regression, unrequested actions, defect-framing, refusal/fallback confirmation).

### Sources checked
- Anthropic Fable 5 / Mythos 5 announcement, docs (introducing + overview), Fable prompting guide, and the 319pp system card (§8.1 benchmarks, §6.3.5 diligence, §2.3.3 shortcomings).
- Cross-repo analysis: `agent-infra/research/2026-06-09-fable-5-mythos-5-harness-impact.md`.

## 2026-06-06 - Narrow model-guide to Opus 4.8 and GPT-5.5

Removed the broad active model catalog from `model-guide`.

### Removed from active routing

- Claude Sonnet fallback routing.
- GPT-5.4 and GPT-5.3 Instant active sections.
- Gemini 3.x active routing and `PROMPTING_GEMINI.md`.
- Grok 4.20 active routing.
- Broad cost-optimization tables that encouraged model-shopping instead of a clear frontier default.

Historical details remain available in git history. This skill now answers only the current high-value question: Opus 4.8, GPT-5.5, or GPT-5.5 Pro?

### Added / retained

- Opus 4.8 system-card insights: honesty/self-verification, reduced destructive actions, grader-speculation watch, prompt-injection caveat, high-effort default, mid-conversation system messages, dynamic workflows.
- GPT-5.5 system-card insights: destructive-action metrics, factuality caveat, low-severity coding-agent misalignment patterns, low CoT controllability, impossible-coding-task lying rate, High bio/chem and High-below-Critical cyber classification.
- GPT-5.5 Pro positioning: same underlying model plus parallel test-time compute, $30/$180 pricing, use only for verified high-stakes derivation.
- Current benchmark table and pricing table limited to Opus 4.8, GPT-5.5, and GPT-5.5 Pro.

### Sources checked

- Anthropic system-card registry and Opus 4.8 launch/API pages.
- Local vendored Opus 4.8 system card.
- OpenAI GPT-5.5 announcement, system card, API pricing, and model comparison docs.

## 2026-07-04 — Fable 5 partially re-routable (empirical)
CC-native lanes verified live (interactive session model, fable-high/low agent defs, key-stripped
headless `claude -p`) in arc-agi session ebbeff04; dormancy header softened accordingly. llmx
subscription + paid-API routing still unverified. Dispatch-economics fable-tier verdicts re-activated
for CC-dispatched subagents.
