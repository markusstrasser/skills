# Critique history and calibration

Preserved on 2026-09-05 while shortening the entry point. These are historical claims and superseded instructions, not current routing, billing, or verification authority. Read only to investigate provenance or calibration. Current workflow: `../SKILL.md`; dispatch authority: `dispatch.md` and the shared profiles.

## Original rationale

Source: critique/SKILL.md before the 2026-09-05 refactor, lines 12-12.

````markdown
Same-model peer review is a martingale — no expected correctness improvement (ACL 2025, arXiv:2508.17536). Cross-model review provides real adversarial pressure because models have different failure modes, training biases, and blind spots.

````

## Historical cosigner routing and Fable dispatch notes

Source: critique/SKILL.md before the 2026-09-05 refactor, lines 48-73.

````markdown
**Cosigner routing (inverted 2026-05-24 — operator empirical).** Default per subpart: **2× Gemini (`arch`+`gaps`) + 2× GPT-medium (`correctness`+`contracts`)** via `standard` preset — not one Gemini + one GPT-high. Add `composer`/`claude`/`formal` as opt-in cosigners on the subparts that need them.

**Opt-in third cosigner — Claude Opus 4.8 (`claude` axis).** `/critique model --axes standard,claude` per subpart.

**Opt-in cheap cosigner — Cursor Composer 2.5 (`composer` axis).** `/critique model --axes standard,composer` per subpart when reviewing a **plan/design packet** (not the diff — use `/code-review` for diffs). Dispatches `composer-2.5` via llmx's `cursor` transport (**packet-only** — neutral empty cwd). Validated frontier-equal on injected-defect review (11/11). Usage-metered Cursor pool. Pair with a GPT axis if using `composer` alone (axis-resolution rule).

**Opt-in repo-grounded cosigner — Grok 4.7 (`grok` axis).** `/critique model --axes standard,grok`
pins `grok-4.7-high` (no `cursor-` prefix, verified live 2026-09-23) in a read-only repo workspace and
fails closed on exact-registry or unrevealed HEAD-canary drift. Bare `grok-4.7` is xAI / Grok Build;
llmx Cursor is packet-only.
Probe without a review: `model-review.py --preflight --axes grok --project "$(pwd)"`; plain
`--preflight` spends no Grok call.

> **The llmx-transport Claude axis stays on Opus 4.8 — do not switch *that* axis to Fable 5.** Over llmx, Fable costs 2×, returns only summarized CoT, and review prompts that say "explain your analysis / show your reasoning" trip Fable's `reasoning_extraction` classifier → silent fallback to Opus 4.8 anyway. The `claude` axis routes via `claude_review` → llmx `anthropic` + `--subscription` (claude-cli); never anthropic-direct/API by default. So for the script-dispatched `claude` axis, Opus 4.8 is correct + cheaper. This is a *transport* limit, not a verdict on Fable's review ability.

**Opt-in fourth axis — Fable 5 via SUBAGENT (`fable-subagent`), for critical subparts only. REPRICED 2026-07-07: Fable is off subscription — this axis bills metered usage credits at $10/$50 per MTok (2× Opus 4.8, which stays $0 subscription). The "savings fund more runs" argument below is dead until Fable returns to subscription (Anthropic says temporary); dispatch only where the measured Fable edge is load-bearing, and probe one small dispatch for billing behavior first (bill-vs-fail unverified; canonical status: model-guide).** The ONLY working path to Fable's raw reasoning is the **Agent tool** (`Agent(model:"fable")`) — NOT llmx (billing-dead + downshifts). `model-review.py` is a subprocess and cannot spawn subagents, so this axis is **orchestrator-driven**: the agent running `/critique` dispatches a Fable subagent *alongside* the script and merges its findings into synthesis. Use it sparingly — only on the **critical subparts** of a session (a load-bearing migration, an identity/correctness invariant, a security-sensitive diff), where Fable's edge over Flash/GPT is real (measured 2026-06-10: obscure domain knowledge, multi-hop/split reasoning). Dispatch RESPONSE-ONLY (read-only tools, return findings text; do NOT ask it to "show reasoning" — keep the prompt verdict-shaped to avoid the classifier trip even on the subagent path). Pattern:
> ```
> Agent(subagent_type="general-purpose", model="fable", prompt=
>   "Review THIS change for correctness/security bugs. FIRST tool call: Write a 'PROBE IN PROGRESS' stub to <path>, "
>   "then append findings there and return them. "
>   "Read-only otherwise. Return a list of findings: SEVERITY | claim | file:line | why-real. No reasoning prose.")
> ```
> The stub-first line is load-bearing: the subagent dispatch gate BLOCKS any prompt that names an output file without instructing write-stub-first (observed eating one retry per dispatch in 2 sessions, 2026-06-10/12).
>
> Then fact-check its findings against code exactly like the Gemini/GPT axes (same trust ranking: convergence + code-verification, not self-confidence). Fable findings that converge with Gemini/GPT are the strongest signal; Fable-only findings on a critical subpart are worth verifying. For routine reviews, skip it — Gemini+GPT is the default.
>
> **Effort: dispatch the fable-subagent axis at LOW** (headless `env -u ANTHROPIC_API_KEY claude -p --model claude-fable-5 --effort low`, or Agent tool default). Measured (anim-workbench effort-architecture eval, 2026-06-12, n=1 screening): Fable-low ≈ Fable-high on CRITIQUE quality — 4/4 correct cosigns, 0 false anchors, 2 novel verified proposals — at **0.34× tokens**; effort separated only on design-SYNTHESIS (novel structure from an open hole). Review axes are critique, so low is the right tier; the savings fund running this repo-grounded axis MORE often (it's the only axis that can falsify a plan's premises — see the 2026-06-10 Known Issue below: packet-only reviewers went 0-for-5 on repo-grounded findings across two plans). Escalate to default/high effort only when the axis is asked to DESIGN a replacement, not judge the existing one.

````

## Effort and domain-specific calibration

Source: critique/SKILL.md before the 2026-09-05 refactor, lines 233-257.

````markdown
**Effort levels:** Default per subpart: **2× Gemini (`arch`+`gaps`) + 2× GPT-5.6 Luna `medium`
(`correctness`+`contracts`)** — four parallel narrow passes beat one `high` mega-query at ≈ the same
or lower cost. Critique quality is effort-insensitive at medium vs high for non-formal work
(anim-workbench 2026-06-12). Reserve `formal` (GPT **high**) for math/Bayes/proof/invariant
subparts only. See `references/dispatch.md § Reasoning Effort Selection`.

**Multi-lens pattern:** Built into `standard` preset — do not collapse to a single GPT `formal` pass
unless the subpart is formal-class.

#### Depth Presets

| Preset | Axes | When |
|--------|------|------|
| `standard` (default) | arch + gaps (Gemini) + correctness + contracts (GPT medium) | Most reviews — **per subpart** |
| `--axes standard,formal` | + formal (GPT high) | Math/stats/proof/invariant subparts |
| `--axes deep` | standard + domain + mechanical | Structural + domain-dense |
| `--axes full` | deep + alternatives | Shared infra, clinical, high-stakes |
| `--axes standard,composer` | + composer (Cursor, packet-only) | Plan/design third lineage — **not** closeout diff (use `/code-review`) |
| `--axes standard,grok` | + Grok 4.7 (Cursor, read-only repo workspace) | PLAN premise falsification against live files/callers |

`formal`, `composer`, `claude`, and `grok` are opt-in add-ons. Run `standard` on each subpart; merge in session.

**Genomics classification review** (monthly or after >10 commits to LR-engine/scoring): Use
`--axes standard,formal,domain` on LR/math subparts. GPT formal/high found 11 conceptual/mathematical
bugs — the detector for incoherent Bayes.

````

## Self-reported confidence calibration

Source: critique/SKILL.md before the 2026-09-05 refactor, lines 290-290.

````markdown
**Do not rank by the `confidence` field.** Model self-reported confidence is uncalibrated: median 0.89 across 16.5K findings, but only ~40% of anchorable findings verify against the code, and per-model the figure ranges 25–50% — confidence does not predict whether a finding is real (per-model disposition audit, 2026-06-01). Rank by convergence + code-verification only. The extractor uses `confidence` solely as a last-resort sort tiebreaker (after cross-model agreement and severity) and bumps it +0.2 when a finding is independently confirmed by both models; that derived signal is fine, the raw model number is not.

````

## Plan-close rationale

Source: critique/SKILL.md before the 2026-09-05 refactor, lines 369-381.

````markdown
After a plan's implementation is committed, there's a gap between "code works" and "code is correct." Regression tests verify existing behavior doesn't change — but they're blind to bugs in new code paths. This mode closes that gap.

See `lenses/plan-close-review.md` for full workflow, bug class table, and migration checklist.

### Why This Exists

Three independent lines of evidence:

1. **Empirical (suspense accounts, 2026-04-07):** GPT-5.5 found 6 confirmed bugs in freshly committed code. All 74 canary tests and 11 IR invariants passed. The bugs were in new functions with zero test coverage.

2. **Failure Mode 15 — Silent Semantic Failures** (MAS-FIRE, arXiv:2602.19843): Reasoning drift, wrong buckets, misleading diagnostics propagate without runtime exceptions.

3. **Failure Mode 16 — Reward Hacking** (TRACE, arXiv:2601.20103): Agents evaluated by test passage may hack the test rather than solve the task.

````

## Superseded adversarial lens

This lens predated the four-axis default and manifest-driven routing. Preserved verbatim for its model, prompt, and calibration history; it is not the active dispatch procedure.

````markdown
<!-- Lens file for review skill: model mode dispatch methodology. Loaded on demand. -->

# Adversarial Review — Dispatch Methodology

## Axis Descriptions

| Axis | Model | What it checks | When to include |
|------|-------|---------------|-----------------|
| `arch` | Gemini 3.5-flash | Patterns, architecture, cross-reference, principles alignment | Always (default) |
| `formal` | GPT-5.5 (high reasoning) | Math, logic, cost-benefit, testable predictions, quantified principles coverage | Always (default) |
| `domain` | Gemini 3.5-flash | Domain fact correctness — citations, API endpoints, schemas, biological claims, numbers | Domain-dense plans; skip for pure code reviews |
| `mechanical` | GPT-5.5 (low reasoning) | Stale refs, wrong paths, naming inconsistencies, duplicated content | Large codebases; include grep results |
| `alternatives` | Gemini 3.5-flash | 3-5 genuinely different approaches with different mechanisms | Architecture decisions; SEPARATE from convergent review (never mix critique + brainstorm) |

## Depth Presets

| Preset | Axes | Blast radius | Cost |
|--------|------|-------------|------|
| `standard` | arch + formal | User-facing default; most features | ~$2-4 |
| `deep` | arch + formal + domain + mechanical | User-facing; structural/domain-dense | ~$4-6 |
| `full` | all 5 | User-facing; shared infra, clinical, high-stakes | ~$6-10 |

Classify by blast radius, not file count. `standard` is the default.
The user-facing presets are `standard`, `deep`, and `full`; each includes GPT-5.5.
Gemini-only passes are internal-only and should not be documented to users as review presets.

## Per-Model Prompts

### Gemini — Architectural/Pattern Review (arch axis)

System: Concrete, no platitudes. Reference specific code/configs. Agent-built codebase (dev time = free). Budget ~2000 words, dense tables/lists.

Required sections:
1. Assessment of Strengths and Weaknesses — reference actual code
2. What Was Missed — cite files, line ranges, gaps
3. Better Approaches — Agree (refine) / Disagree (alternative) / Upgrade
4. What I'd Prioritize Differently — top 5, testable criteria
5. Goals & Principles Alignment — violations and well-served principles (or internal consistency if no GOALS.md)
6. Blind Spots In My Own Analysis — where to distrust Gemini

### GPT-5.5 — Quantitative/Formal Analysis (formal axis)

System: Quantitative and formal ONLY. Other reviewers handle qualitative. Precise, show reasoning. Agent-built codebase. Budget ~2000 words, tables, source-graded claims.

Required sections:
1. Logical Inconsistencies — contradictions, assumptions, invalid inferences, math verification
2. Cost-Benefit Analysis — impact, maintenance burden, composability, risk. Filter on ongoing drag, NOT creation effort
3. Testable Predictions — falsifiable predictions with success criteria
4. Goals & Principles Alignment (Quantified) — per-principle coverage 0-100%, gaps, fixes
5. My Top 5 Recommendations — measurable impact, quantitative justification, verification metrics
6. Where I'm Likely Wrong — GPT-5.5 known biases: confident fabrication, overcautious scope-limiting, production-grade creep

### Gemini 3.5-flash — Domain Correctness (domain axis)

System: Domain-specific claim verification only. Per-claim verdict: CORRECT / WRONG / UNVERIFIABLE. Flag URLs, API endpoints, version numbers needing probes. Budget ~1500 words.

### GPT-5.5 — Mechanical Audit (mechanical axis)

System: Mechanical audit only, no analysis. Find: stale refs, inconsistent naming, missing cross-refs, duplicates, wrong paths. Flat numbered list. Runs at low reasoning effort (pattern-spotting, not reasoning).

### Gemini 3.5-flash — Alternative Approaches (alternatives axis)

System: Generate 3-5 genuinely different approaches (different mechanisms, not variations). Per approach: core mechanism, advantages, disadvantages, maintenance burden. Do NOT critique the existing plan.

## Full prompt templates

See `references/prompts.md` for copy-paste manual dispatch templates. The `model-review.py` script handles these automatically.

## Dispatch Mechanics

**Always use the script:**
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract \
  --question "$QUESTION"
```

Set the outer tool timeout above the longest selected profile: `660000` ms for standard axes,
`1230000` ms with Grok, or `3630000` ms with Opus Max. The script fires all queries in parallel
and derives its internal collection wait from those profiles.

### Script Flags

- `--extract` — Auto-extract claims via cross-family models, merge into `disposition.md`, and emit `coverage.json`. Add to all standard/deep/full reviews.
- `--verify` — After extraction, verify cited files/symbols exist. Implies `--extract`.
- `--questions FILE` — JSON mapping axis names to custom questions. Unmapped axes use `--question`.
- `--context-file SPEC` — Repeat to assemble `file.py`, `file.py:100-150`, or `file.py:100` excerpts.
- `--axes NAME` — Preset name or comma-separated axes.

### Model Selection Contract

```
Gemini 3.5-flash:  arch / domain / alternatives passes
GPT-5.5:           formal pass + mechanical pass (low effort)
3.1-Pro:           fallback when 3.5-flash rate-limits
```

The shared dispatch layer owns providers, transport, retries, and timeout
policy. This lens should describe review responsibilities, not raw model flags.

**NEVER downgrade models on failure.** Diagnose via shared dispatch metadata and
coverage artifacts instead of teaching transport-specific debugging here.

### Gemini Rate Limit Fallback

Script auto-detects a Gemini 503/rate-limit on the primary axis (gemini-3.5-flash, exit 3 or stderr markers) and retries that axis once with the runner-up critique model (gemini-3.1-pro-preview) — NOT the cheap classification model, which measured ~42% hallucination as a critique axis. If the fallback also rate-limits, the axis fails cleanly (recorded in coverage.json). GPT axes are unaffected.

### Uncalibrated Threshold Flagging

Automatic with `--extract`: the script tags numeric thresholds (e.g., `>=20% AUPRC`) lacking cited sources with `[UNCALIBRATED]`. Common GPT failure mode: fabricating plausible thresholds. Treat as requiring your own derivation.

## Known Issues

- **Gemini (3.5-flash):** Production-pattern bias (enterprise for personal), self-recommendation (Google services), instruction dropping in long context
- **GPT-5.5:** Confident fabrication (invents numbers/paths), overcautious scope, production-grade creep
- **gemini-3-flash-preview / GPT-5.3:** Shallow analysis, ~42% hallucination as a critique axis. The cheap classification tier — never a cosigner. This is why `mechanical` moved to GPT-5.5 and the rate-limit fallback moved to 3.1-Pro. (Distinct from gemini-3.5-flash, the clean primary cosigner.)
- **Correlated errors:** ~60% shared wrong answers when both err (Kim ICML 2025, pre-reasoning). Never same-family reviewer + synthesizer.
- **Self-preference:** 74.9% demographic parity bias (Wataoka NeurIPS 2024). Different-family synthesis.
- **Debate = martingale:** Sequential discussion has no correctness improvement (Choi 2025). Independent parallel reviews only.
- **Shared dispatch output:** Never rely on shell redirects for review artifacts;
  the shared script writes directly to files.

## Anti-Patterns

- **Synthesizing without extracting** — #1 information loss. Always extract + disposition before prose.
- **Synthesizing a synthesis** — Each compression drops ideas. Merge raw extractions, not prior syntheses.
- **Adopting without code verification** — Both models hallucinated "missing" features that already existed.
- **Model agreement = proof** — Agreement is evidence, not proof. Verify against source code.
- **Same prompt to both models** — Gemini = patterns, GPT = quantitative/formal. Different strengths need different prompts.
- **Writing to /tmp** — Persist to `.model-review/YYYY-MM-DD-topic/`.
- **Skipping governance check** — Unanchored reviews drift into generic advice.
- **Mixing review and brainstorming** — Convergent only. Use `/brainstorm` for divergent.
- **Priming tool names** — Turns critique into evaluation. Use `alternatives` axis separately.
- **Scale-ambiguous context** — Both models converge on the same wrong answer from shared misleading context.
- **"Top N" triage** — If INCLUDE, implement. DEFER needs explicit reason per item.
- **Skipping self-doubt section** — Most valuable part of each review.

````

## Governance-framing incident and original guidance

Source: critique/SKILL.md before 2026-09-05, lines 86-113; retained verbatim as historical context.

````markdown
**Governance relevance — curate, do NOT dump the charter.** Do not inject the whole
`GOALS.md`/`CLAUDE.md`/constitution as a preamble. A full-charter block under "review
against these" biases reviewers toward compliance and suppresses the independent
judgment that is the whole point of cross-model review (2026-06-15 biased-critique
incident — the neutral re-run only de-biased once the charter was removed). The
dispatch script no longer auto-injects it; `--charter-anchor` is the explicit opt-in
for a *compliance* review only.

Instead, as the orchestrating agent, **select the few CURRENT + RELEVANT governance
constraints that actually bear on THIS review** and add them as a short, targeted block
in the context you assemble. E.g. a plan proposing a compatibility shim → the
breaking-refactors-by-default principle; a shared-infra change → the autonomy
boundaries; a schema/taxonomy → the single-source-of-truth invariant; a research memo →
the on-point epistemic principle.

**Curate FROM the compact index, not the raw docs.** If the project has
`.claude/governance-index.md` (generated from GOALS/constitution/vetoed-decisions by
`just governance-index` — so it's current and compact), use it as the menu to pick the
relevant lines from. It is the single source; don't re-read or re-state the full charter.

- **Relevant + current only.** Re-read the source and confirm each principle still
  exists / isn't stale before quoting it — governance drifts, and a quoted-but-removed
  rule misleads the reviewer (verify-before-recommending applies to your own charter).
- **Frame for judgment, not obedience.** Header it *"Relevant project constraints —
  apply your own judgment: flag the work if it violates these, AND flag a constraint
  itself if it looks wrong for this case."* Never *"review against these, not your priors."*
- **Default to none.** If no principle is clearly on-point, inject nothing — blind-
  adversarial is the correct default.

````

## Execution-grounded closeout observation

Source: critique/SKILL.md before 2026-09-05, lines 426-429; retained verbatim as historical context.

````markdown
Fact-check and disposition every finding. Inspect `coverage.json` before closing so you can see packet
drops, axis coverage, and verification totals. Include one reviewer instruction to **RUN the changed
code paths before verdicts** (execution-grounded review — live execution caught 3 real bugs that offline
tests + packet review both missed, `live-execution-is-the-integration-verifier`).

````

## Superseded mandatory governance preamble

The pre-refactor biases reference said: "**Skipping the goals/governance preamble.** Unanchored reviews drift into generic advice." The 2026-06-15 charter-bias incident and current script default supersede this blanket mandate. Current guidance curates relevant constraints and reserves the full charter for explicit compliance reviews.
