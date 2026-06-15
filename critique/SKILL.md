---
name: critique
description: "Use when: /critique, 'review plan', 'what's wrong', fact-check plans/findings/closeout. Modes: model, verify, close. NOT code diffs (/code-review) — critique owns design/plan layer."
user-invocable: true
argument-hint: <mode> [target]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: high
---

# Cross-Model Review Workflow

Same-model peer review is a martingale — no expected correctness improvement (ACL 2025, arXiv:2508.17536). Cross-model review provides real adversarial pressure because models have different failure modes, training biases, and blind spots.

## Default Migration Stance

Unless the user explicitly says compatibility matters, treat the target change as a breaking refactor with full migration.

- Challenge wrappers, adapters, dual-read/dual-write paths, fallback reads, and "temporary" bridges as liabilities, not prudent defaults.
- Prefer direct caller migration and old-path deletion over coexistence plans.
- If compatibility is genuinely required, name the live boundary, why it must remain, and the removal condition. Unnamed future-proofing is design noise.

## Modes

| Mode | Trigger | What it does |
|------|---------|-------------|
| `model` | Default, or explicit `/critique model [topic]` | Adversarial cross-model review via Gemini + GPT |
| `audit-plan` | `/critique audit-plan [topic]` or large repo audit + remediation plan in context | Lean critique after multi-lane inventory — see `lenses/repo-audit-plan-review.md` |
| `verify` | `/critique verify <report>` | Fact-check LLM findings against actual code |
| `close` | `/critique close` | Post-implementation: tests, review, caught-red-handed loop |

**Auto-routing (when no mode specified):**
- Recent plan in `.claude/plans/` with commits since plan start → `close`
- Audit backlog (≥15 open items) + remediation plan in context, with or without fresh lane outputs → `audit-plan`
- Recent findings/audit output in context (no plan) → `verify`
- Git diff / PR / "review this diff" in context → `/code-review` (Composer default) OR `model` with `--axes standard,composer` when not using the scout
- Otherwise → `model`

**Mode: audit-plan** — see `lenses/repo-audit-plan-review.md`. Repo-scale audits: parallel readonly lanes first (orchestrator omits clusters); lean 2-critic pass after verify; commit synthesis to `docs/audit/`.

---

## Mode: model — Cross-Model Adversarial Review

**Purpose:** Convergent/critical only — find what's wrong. For divergent ideation, use `/brainstorm`.

See `lenses/adversarial-review.md` for full dispatch methodology, axis descriptions, depth presets, per-model prompts, and known issues.

**Cosigner routing (inverted 2026-05-24 — operator empirical).** Default per subpart: **2× Gemini (`arch`+`gaps`) + 2× GPT-medium (`correctness`+`contracts`)** via `standard` preset — not one Gemini + one GPT-high. Add `composer`/`claude`/`formal` as opt-in cosigners on the subparts that need them.

**Opt-in third cosigner — Claude Opus 4.8 (`claude` axis).** `/critique model --axes standard,claude` per subpart.

**Opt-in cheap cosigner — Cursor Composer 2.5 (`composer` axis).** `/critique model --axes standard,composer` per subpart when reviewing a **plan/design packet** (not the diff — use `/code-review` for diffs). Dispatches `composer-2.5` via llmx's `cursor` transport. Validated frontier-equal on injected-defect review (11/11). Usage-metered Cursor pool. Pair with a GPT axis if using `composer` alone (axis-resolution rule).

> **The llmx-transport Claude axis stays on Opus 4.8 — do not switch *that* axis to Fable 5.** Over llmx, Fable costs 2×, returns only summarized CoT, and review prompts that say "explain your analysis / show your reasoning" trip Fable's `reasoning_extraction` classifier → silent fallback to Opus 4.8 anyway. The `claude` axis routes via `claude_review` → llmx `anthropic` + `--subscription` (claude-cli); never anthropic-direct/API by default. So for the script-dispatched `claude` axis, Opus 4.8 is correct + cheaper. This is a *transport* limit, not a verdict on Fable's review ability.

**Opt-in fourth axis — Fable 5 via SUBAGENT (`fable-subagent`), for critical subparts only.** The ONLY working path to Fable's raw reasoning is the **Agent tool** (`Agent(model:"fable")`, subscription auth) — NOT llmx (billing-dead + downshifts). `model-review.py` is a subprocess and cannot spawn subagents, so this axis is **orchestrator-driven**: the agent running `/critique` dispatches a Fable subagent *alongside* the script and merges its findings into synthesis. Use it sparingly — only on the **critical subparts** of a session (a load-bearing migration, an identity/correctness invariant, a security-sensitive diff), where Fable's edge over Flash/GPT is real (measured 2026-06-10: obscure domain knowledge, multi-hop/split reasoning). Dispatch RESPONSE-ONLY (read-only tools, return findings text; do NOT ask it to "show reasoning" — keep the prompt verdict-shaped to avoid the classifier trip even on the subagent path). Pattern:
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

### 1. Assemble Context

Write review material to a single context file.

**Pre-flight — scope declaration (mandatory):** Include a `## Scope` block near the top:
- **Target users:** personal / team / multi-tenant / public
- **Scale:** current entity counts AND designed-for scale (e.g., "currently 40 compounds, designed for thousands of subjects")
- **Rate of change:** how often does new data arrive?

This prevents the #1 review failure mode: models optimizing for the wrong scale. Evidence: selve UMLS review (2026-04-06) — GPT scored a plan 27/100 as "over-engineered for 105 personal entities" when the actual scope was multi-user scalable.

**Goals & governance anchoring:** Check for `docs/GOALS.md`. Include as preamble if found.

See `references/context-assembly.md` for detailed context gathering (narrow, broad, auto-assembled).

#### Context Anti-Patterns

Common review biases — check your context for these before analysis:

| Anti-pattern | How it biases | Fix |
|-------------|--------------|-----|
| **Scale ambiguity** — large number without clarifying which ops touch it | Models optimize for the large number even when the change affects a small boundary | Include concrete volumes at the decision boundary |
| **Priming alternatives** — listing tools/packages in the prompt | Models evaluate named alternatives favorably instead of finding flaws | For convergent: "find what's wrong" only. For alternatives: use `/brainstorm` or the `alternatives` axis |
| **Framing incumbents as limited** — describing existing tools by narrow current use | Models treat incumbent as constrained | Frame by capability: "Pydantic v2 is established (13 models, 100% typed). Question: extend to output schemas?" |
| **Missing boundary volumes** — not stating how many objects schemas will process | Models default to optimizing for largest number in context | Always include: "Largest output: N entries." |
| **"Rethink entirely" in convergent** — asking for alternatives alongside finding problems | Models dodge critique by proposing alternatives | Keep convergent and divergent separate |
| **Presupposing new infra should exist** — reviewing NEW system without incident history | Models critique within frame instead of questioning it | Include incident history. Prompt: "cite the specific past incident each component prevents. If none, say SPECULATIVE." |
| **Ambiguous domain terminology** — terms that mean different things in different contexts | Models share the same misread | Define terms precisely. Disambiguate similar-named systems on first use. |
| **Missing project identity** in cross-project reviews | Models apply principles too literally to unfamiliar projects | Include 2-3 line identity per project |
| **Missing scope declaration** — not stating target users and designed-for scale | Models assume personal/small when reviewing shared infra, or assume production when reviewing prototypes | Always include scope block (see above) |

### 1.5 Decompose into subparts (default — do this before dispatch)

**One mega-packet is the expensive failure mode.** Split the review into 2–4 **subparts**
(independent file clusters, plan phases, or concerns), then run the standard 4-axis pass
(**2× Gemini + 2× GPT-medium**) on each subpart separately. Merge findings after.

| Subpart split heuristic | Example |
|-------------------------|---------|
| By plan phase / vertical slice | "Phase 2 gateway" vs "Phase 3 consumer migration" |
| By directory / module cluster | `scripts/knowledge/` vs `migrations/` |
| By concern when diff is huge | "Schema change" vs "call-site updates" |
| By risk tier | Load-bearing invariant subpart first |

**Per subpart dispatch** (standard = 2× Gemini + 2× GPT @ medium, **overlapping full-review
mandate** — each pass covers architecture AND bugs; lenses differ, territories don't):

```bash
# Build a tight packet for ONE subpart only (<80KB context ideal)
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/build_plan_close_context.py \
  --repo "$(pwd)" --file path/a.py --file path/b.py \
  --output .model-review/subpart-1-context.md

uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context .model-review/subpart-1-context.md \
  --topic "$TOPIC — subpart 1: gateway outbox" \
  --project "$(pwd)" \
  --axes standard \
  --extract \
  "Adversarial review of THIS subpart only. Do not speculate about files not in context."
```

Repeat for subpart 2…N. **Synthesize across subparts** in the orchestrating session (you merge;
the script does not auto-merge multi-subpart runs).

**When to add axes beyond standard:**
- `formal` — math, Bayes/stats, proofs, formal invariants (`--axes standard,formal`)
- `composer` — cheap third lineage on diffs (`--axes standard,composer`)
- `claude` — Opus third family on high-stakes only

**Effort policy:** GPT **medium** on `correctness` + `contracts` (standard). GPT **high** only on
`formal` (opt-in). Gemini stays on `deep_review` for `arch` + `gaps`. Do not escalate effort
because the topic "feels important" — escalate because the **subpart class** is formal/math-dense.

### 1.5 VOI premise scout (default on — disable for packet-only)

`model-review.py` runs a **repo-grounded premise scout** by default before packet-only axes.

**Disable repo context** when the packet is self-contained:

```bash
# Default: scout greps repo to falsify premises
model-review.py --context plan.md --project $(pwd) --axes standard ...

# Packet-only: single file, clear req/res, no repo needed
model-review.py --context-scope packet --context one-file.md ...
# or: --no-scout
```

| Flag | Meaning |
|------|---------|
| `--scout` / `--no-scout` | Default **on**. `--no-scout` = skip repo scout |
| `--context-scope repo` | Default — scout may use workspace |
| `--context-scope packet` | No repo scout (context-free / single-file) |
| `--irreversible` | Block axes if executed scout returns `conviction=low` |
| `--force-scout` | Bypass that gate |

ADR: `agent-infra/decisions/2026-06-15-voi-sequenced-review.md`

### 2. Dispatch

**Always use the script.** It handles: context assembly, goals/governance preamble injection, parallel dispatch to Gemini + GPT via the shared dispatch core, extraction, and disposition generation.

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py triage \
  --repo . --packet .model-review/packet.md --budget-seconds 480

uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --dispatch-manifest .model-review/dispatch.json \
  --context context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract \
  "$ARGUMENTS"
```

Set `timeout: 660000` on the Bash tool call. See `references/dispatch.md` for `--questions`, `--context-files`, depth presets, effort levels, and troubleshooting.

**Dispatch policy (manifest-first):** `review_gate triage` writes `dispatch_policy` into `dispatch.json` (scout, context_scope, budget). Pass `--dispatch-manifest` to `model-review.py`; explicit CLI flags still win.

**Model-specific prompting:** Before assembling context, consult `/model-guide` for per-model rules. Key: GPT-5.5 context should use XML `<doc>` tags, Gemini query goes at END. See `references/dispatch.md § Context Formatting` for the full checklist.

**Effort levels:** Default per subpart: **2× Gemini (`arch`+`gaps`) + 2× GPT-5.5 `medium`
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
| `--axes standard,composer` | + composer (Cursor) | Plan/design third lineage — **not** closeout diff (use `/code-review`) |

`formal`, `composer`, and `claude` are opt-in add-ons. Run `standard` on each subpart; merge in session.

**Genomics classification review** (monthly or after >10 commits to LR-engine/scoring): Use
`--axes standard,formal,domain` on LR/math subparts. GPT formal/high found 11 conceptual/mathematical
bugs — the detector for incoherent Bayes.

### 3. Read All Axis Outputs and Synthesize

Read all axis outputs (4 on standard, more if deep/full). You are the merger — cross-reference directly.

**For each finding from either model:**
1. **Verify code claims** — read the actual file. Models frequently cite wrong line numbers, invent function names.
2. **Check if both models found it** — cross-model agreement is the strongest signal.
3. **Grep "missing feature" claims** — the feature may already exist.

**Bucket findings into three categories before recommending action:**

| Bucket | Definition | Action |
|--------|-----------|--------|
| **Convergent** | Both models flagged the same issue (`cross_model: true` in `findings.json`) | Verify in code, then fix. Strongest signal. |
| **Single-source** | One model flagged it, the other was silent on this point | Verify in code. If real, fix it. Coverage gap, not disagreement. |
| **Divergent** | Both models addressed the same question but recommended **different answers** (e.g., A says "use X", B says "use Y"; A says "delete the wrapper", B says "keep it for boundary Z") | Do **not** auto-resolve. Surface to user as a taste/judgment call with both positions stated. |

The first two are convergence on whether something is a problem — verifiable, act. The third is genuine disagreement on the right answer — taste, escalate. Synthesizing divergent recommendations into a single "balanced" position discards the most actionable signal: that there's a real choice the user should make.

**Detecting divergence:** scan both reviewer outputs for the same target (file, function, decision point) and check whether the recommendations are compatible (same direction, different depth) or incompatible (different directions). Same problem + conflicting fixes = divergent.

**Trust ranking for verified findings:**

| Signal | Action |
|--------|--------|
| Convergent + verified in code | Fix it |
| Single-source + verified in code | Fix it |
| Convergent but unverified | Verify first |
| Single-source, unverified | Investigate before acting |
| Contradicts what you see in the code | Discard |

**Do not rank by the `confidence` field.** Model self-reported confidence is uncalibrated: median 0.89 across 16.5K findings, but only ~40% of anchorable findings verify against the code, and per-model the figure ranges 25–50% — confidence does not predict whether a finding is real (per-model disposition audit, 2026-06-01). Rank by convergence + code-verification only. The extractor uses `confidence` solely as a last-resort sort tiebreaker (after cross-model agreement and severity) and bumps it +0.2 when a finding is independently confirmed by both models; that derived signal is fine, the raw model number is not.

**Before implementing:** Ask yourself two questions:
1. Where do you disagree with the models? ("Nowhere" is valid.)
2. What context did you have that they didn't?

Don't let rigorous-looking analysis override what you can see in the code.

### 4. Act on Findings

**The synthesis is not the deliverable — the updated artifact is.**

Structure your response to the user with the three buckets explicit:

- **Convergent (acting):** what both models agreed on, what you verified, what you're fixing.
- **Single-source (acting / investigating):** what one model caught, verified status, action.
- **Divergent (your call):** the questions where models disagreed. State both positions, what each implies, and ask the user to pick. Do not pre-resolve.

Then:

- **Verified convergent + single-source findings:** apply directly. Don't ask permission.
- **Divergent findings:** wait for user direction before implementing either side.
- **Context depleted:** offer plan-mode handoff.
- **All deferred/rejected:** the synthesis is the deliverable.

### Artifact Handoff

The shared review script writes the audit trail under `.model-review/...`:

- `shared-context.md` and `shared-context.manifest.json`
- `findings.json`
- `disposition.md`
- `coverage.json`
- `verified-disposition.md` when `--verify` runs

Treat `coverage.json` as the machine-readable contract. It records packet
provenance, dispatch axes/models, extraction totals, and verification totals.
Treat `verified-disposition.md` as grounded anchor checking, not semantic proof:
it verifies structured findings against repo paths, line anchors, and file-local
corroboration when available.

---

## Mode: verify — Fact-Check LLM Findings

Standalone verification of LLM-generated audit findings. Use after `model` mode, `/dispatch-research`, `/project-upgrade`, or any automated audit that produces file-specific claims.

See `lenses/verification.md` for the full procedure.

### When to Use

- After `model` mode produces codebase critique
- After `/dispatch-research` generates audit findings
- After `/project-upgrade` suggests changes
- After receiving external audit output (Codex, Gemini, GPT)
- When someone pastes a list of "bugs found" from any LLM
- Before implementing ANY fix list from an LLM source

### When NOT to Use

- For verifying scientific/factual claims (use `/researcher` or `/epistemics`)
- For verifying a single specific bug (just read the code directly)
- When findings are already human-verified

### Procedure

1. **Extract Claims** — Parse the report. Extract every file-specific, verifiable claim. Number each for tracking.
2. **Ground Truth Verification** — For each claim, verify against actual code using the checklist in `lenses/verification.md`.
3. **Synthesis Table** — Produce verification summary with CONFIRMED / CORRECTED / HALLUCINATED / INCONCLUSIVE verdicts.
4. **Action** — Fix ALL CONFIRMED and CORRECTED findings. Never fix HALLUCINATED. Never self-select "top N" from confirmed. If hallucination rate exceeds 40%, warn user the source is unreliable.

### Output Convention

If total findings > 10, write the synthesis table to a file and return the path. Don't dump 30-row tables inline.

---

## Mode: close — Post-Implementation Plan Close

After a plan's implementation is committed, there's a gap between "code works" and "code is correct." Regression tests verify existing behavior doesn't change — but they're blind to bugs in new code paths. This mode closes that gap.

See `lenses/plan-close-review.md` for full workflow, bug class table, and migration checklist.

### Why This Exists

Three independent lines of evidence:

1. **Empirical (suspense accounts, 2026-04-07):** GPT-5.5 found 6 confirmed bugs in freshly committed code. All 74 canary tests and 11 IR invariants passed. The bugs were in new functions with zero test coverage.

2. **Failure Mode 15 — Silent Semantic Failures** (MAS-FIRE, arXiv:2602.19843): Reasoning drift, wrong buckets, misleading diagnostics propagate without runtime exceptions.

3. **Failure Mode 16 — Reward Hacking** (TRACE, arXiv:2601.20103): Agents evaluated by test passage may hack the test rather than solve the task.

### Workflow

**Phase 0: Pre-Close Discipline** — Normalize closeout: separate code/data validation, sync generated docs, prove migration completion. Build review packet:
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/build_plan_close_context.py \
  --repo "$(pwd)" \
  --output .model-review/plan-close-context.md
```

Do not rely on auto-discovered touched-file scope when the worktree is already clean or the relevant changes were committed earlier in the session. In that case, build an explicit review scope packet with the concrete files under review. Otherwise `/critique close` can silently review an empty packet and produce useless output.

**Phase 0b: Deterministic triage (required)** — routing + blockers, no LLM:
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py triage \
  --repo "$(pwd)" \
  --packet .model-review/plan-close-context.md \
  --mode close
```
Read `.model-review/dispatch.json`. **Stop on blockers** (oversize packet, dead refs, missing `verified-disposition.md` at close). Follow `layers.diff` → code-review only; `layers.design` → critique only.

**Phase 1: Write Tests for New Code** — Identify new functions from plan commits. Write unit tests covering happy path, edge cases, error paths, and contract invariants.

**Phase 2: Two-layer review — one pass per layer (partition enforced).**

*Diff layer (once):* run **`/code-review high`** over the plan's commits. Composer is this
skill's default provider (`cursor-agent`) — do **not** also add a `composer` critique axis on
the same diff. Validate scout findings against code; do NOT auto-commit fixes.
For recall mode use `--all-providers` on the diff scope only.

*Design layer (once):* run `/critique model --axes standard` per subpart on the plan-close
review packet (not the raw diff). Use `--context .model-review/plan-close-context.md --extract --verify`.
The packet manifest's `review_targets` names `diff_target` (code-review) vs `design_target`
(critique) — respect it; do not re-review diff content in the design pass.
Fact-check and disposition every finding. Inspect `coverage.json` before closing so you can see packet
drops, axis coverage, and verification totals. Include one reviewer instruction to **RUN the changed
code paths before verdicts** (execution-grounded review — live execution caught 3 real bugs that offline
tests + packet review both missed, `live-execution-is-the-integration-verifier`).

**Phase 2b: Rank + inconclusive (deterministic, after `--extract --verify`)** — shrink orchestrator load:
```bash
REVIEW_DIR=.model-review/<topic-hash>  # from model-review output
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py rank --review-dir "$REVIEW_DIR"
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py inconclusive --review-dir "$REVIEW_DIR" --repo "$(pwd)"
```
Implement from `orchestrator-top.json` (top 8, cross-model first). If `escalation-recommendation.json`
exists → re-run `cross4` on same packet (auto-detected at rank; no manual re-triage).
INCONCLUSIVE rows with `resolved_deterministic: true` are deprioritized.

Optional on cross2 subparts: add `--cross-talk` to `model-review.py` — structure pass first,
mechanism pass gets `structural-assumptions.json` injection.

**Never pass `"close"` (or `"review"`, `"verify"`, bare verbs) as the positional prompt.** The script now detects these as slash-command leakage and substitutes a structured adversarial template (with a stderr warning), but a concrete question tailored to the plan — e.g., `"Find bugs in the new signal-merging logic introduced by $(git log -1 --format=%h); focus on boundary conditions and silent semantic failures"` — produces sharper output than the generic substitute.

**Phase 3: The Caught-Red-Handed Loop** — For each confirmed finding: would any Phase 1 tests have caught this? If yes, fix the test gap. If no, write a new test. Verify against pre-fix code:
```bash
git stash
pytest tests/test_<new>.py -x  # should FAIL
git stash pop
pytest tests/test_<new>.py -x  # should PASS
```

**Phase 3.5: Integration audit (required before closeout commit)** — deterministic gate that the
diff did not implement findings marked HALLUCINATED in `verified-disposition.md`:
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/integration_audit.py \
  --review-dir .model-review/<topic-hash> \
  --repo "$(pwd)" \
  --plan .claude/plans/<plan>.md
```
Exit 1 = stop; do not commit. Warnings = inspect manually. No LLM — joins review artifacts to git diff.

**Phase 3.6: Outcome link (after fix commits)** — tie CONFIRMED findings to git commits:
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/outcome_link.py \
  --repo "$(pwd)" --review-dir "$REVIEW_DIR" --since HEAD~30
```
Writes `outcome-link.json` (`linked_anchor` = evidence-grade; `linked_file` = weak candidate only).

**Phase 4: Close the Plan** — Commit tests, update plan status, run `validate-code`, summarize findings.

### When NOT to Use

- Trivial plans (< 30 lines, single function, obvious correctness)
- Research/analysis plans that don't produce code
- Plans that only modify config/data with no logic changes

---

## References

- `references/context-assembly.md` — detailed context gathering patterns
- `references/dispatch.md` — shared dispatch contract, context formatting, extraction defaults
- `references/extraction.md` — extraction/disposition coverage rules
- `references/prompts.md` — prompt bodies used by the shared review script
- `references/biases-and-antipatterns.md` — known model biases, per-model failure modes, common mistakes

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-04-25] Claude Code verifier auth split** — `claude --bare -p`
  is the documented scripted/API-key path, but bare mode skips OAuth/keychain
  reads and uses `ANTHROPIC_API_KEY` or an explicit `apiKeyHelper`. On this
  machine the inherited API key path can fail with `Credit balance is too low`
  even while the local Claude subscription auth works. For read-only Claude
  Code verification from Codex/agent shells, prefer:
  `uv run python3 ~/Projects/skills/scripts/claude-code-verify.py --repo "$(pwd)" --prompt-file prompt.md --output claude-review.md`.
  The wrapper unsets `ANTHROPIC_API_KEY`, runs from a tiny temp cwd, passes the
  prompt on stdin, and restricts tools to read-only inspection by default. Use
  `--use-api-key` only when explicitly testing the API-key path.
- **[2026-03-27] shared dispatch output — never use shell redirects (> file) for review artifacts; the shared review script writes directly to files. Shell redirects buffer until process exit, producing 0-byte files.**
- **[2026-04-09; updated 2026-06-11] GPT-5.5 xhigh dispatch — set `--timeout 1800`-`3600` explicitly (xhigh runs 30-45 min; the 300s default is the footgun, auto-scaled to 1200s only as a net) and run it via `run_in_background` (foreground Bash caps at 10 min). llmx also treats `--max-tokens` as the visible-output budget with reasoning headroom added on top, so xhigh no longer returns-nothing-from-token-starvation. Parallel xhigh calls may still hit rate limits — run sequentially or use high effort.**
- **[2026-04-09] xhigh vs high for architectural review — marginal quality delta. High-effort adversarial review (4 min) found the sharpest insight across 6 reviews. xhigh (15 min each) had more words, similar signal density. Reserve xhigh for formal math only. For deep dives: 2-3 parallel high queries with focused questions > 1 xhigh mega-query.**
- **[2026-04-09] Context formatting matters — GPT-5.5 performs better with XML `<doc>` tags around context sections. Gemini needs query at END, critical constraints at END. Consult /model-guide before assembling context for manual dispatch.**
- **[2026-04-11] FIXED — Python version mismatch in `_bootstrap_llmx()`: when running model-review.py via `uv run` from a project whose venv Python differs from the llmx tool install's Python (e.g., phenome 3.12 vs llmx tool 3.13), the previous fallback used `glob.glob` to inject ANY available `python*/site-packages` from the llmx tool install into `sys.path`. Result: 3.13 compiled `.so` files (e.g. `pydantic_core._pydantic_core.cpython-313-darwin.so`) loaded into a 3.12 process, producing the cryptic `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`. Fix in `shared/llm_dispatch.py` now matches Python `major.minor` exactly and raises a clear `ImportError` if no matching version is found. Workaround: run model-review.py via `/Users/alien/.local/share/uv/tools/llmx/bin/python3 .../model-review.py` (the llmx tool's own Python) — verified working with both Gemini + GPT-5.5 axes returning real output. Or `uv pip install llmx` in the current project venv.**
- **[2026-04-13] --verify pass can hang on a single finding** — model-review.py's `--verify` pass verifies each extracted finding serially. If one verification call gets stuck on a network round-trip, the whole process goes quiet even though extraction + per-model outputs are already written. Symptom: `arch-output.md`, `formal-output.md`, and `formal-extraction.parsed.json` are present in `.model-review/<topic>-<hash>/` but no `verified-disposition.md`. The process is alive but using <1s CPU. Action: kill the hung process and work from the extracted findings directly (`formal-extraction.parsed.json` is already machine-readable). Don't wait — the timeout doesn't help when the hang is inside the verify loop.
- **[2026-04-16] Never pipe `model-review.py` through `tail`** — stdout is full structured JSON (can be hundreds of lines). `| tail -40` silently drops the artifact paths and findings and keeps only closing braces. Read the artifacts from the review dir directly (`disposition.md`, `coverage.json`) or let the full stdout land in the shell. The script now prints a trailing `=== model-review summary ===` block that DOES survive tail truncation — if you must tail, tail ≥20 lines to catch it.
- **[2026-04-16] HALLUCINATED rate inflated by anchor hallucination on config files** — both Gemini 3.1 Pro and GPT-5.5 will cite JSON config files with `.js` extension (e.g. `config/foo.js` when the real file is `config/foo.json`). The verifier correctly marks these anchors as "not found" and the finding gets HALLUCINATED, but the finding's SEMANTIC content may still be true. Example 2026-04-15: 18-finding review on genomics PRS plan, 10 flagged HALLUCINATED (56%); manual cross-check showed the semantic-hallucination rate was ~10% — the rest were `.js`-instead-of-`.json` anchor mistakes. Action: don't treat HALLUCINATED as "discard this finding" — re-check semantic content against the likely-intended file (swap `.js` → `.json`). **FIXED:** `_resolve_reference` now tries extension-swap aliases (`_FUZZY_EXT_ALIASES`: `.js`→`.json`, `.yml`↔`.yaml`, etc.) before declaring an anchor missing, so format-only mismatches no longer inflate HALLUCINATED.
- **[2026-06-03] Cross-repo reviews — pass `--sibling-roots` or the HALLUCINATED rate lies.** The `--verify` pass resolved anchors only against `--project`. On a cross-repo packet (e.g. a genomics↔phenome bridge review where half the diff lives in phenome), every sibling-repo anchor was marked HALLUCINATED — a 5-axis bridge review hit **50.8% "hallucinated", and 2 of the 3 real bugs were in the sibling repo**, nearly buried. **FIXED:** `_resolve_reference` now also resolves against explicitly-passed `--sibling-roots` (exact + basename, tagged `exact_sibling`/`basename_sibling`); default empty so single-repo reviews are unchanged. When a close/model review spans repos, pass `--sibling-roots ~/Projects/phenome` (repeatable). Until then, treat HALLUCINATED on a cross-repo packet as "verify manually against the sibling," not "discard."
- **[2026-06-09] Code-symbol citations inflated HALLUCINATED — 3rd anchor-inflation class.** Findings citing a SYMBOL as if it were a file (`GenomeObserver.observe()`, `_VcfRecord`, `parse_variant_key()`) miss every file-resolution branch and got marked HALLUCINATED. A genomics close hit ~38% "hallucinated" that was really ~10% (the rest real findings citing real symbols). **FIXED:** `_resolve_reference`, before declaring `missing`, detects a code-symbol reference (dotted identifier, optional `()`, non-source suffix) and greps `def`/`class <leaf>` across `*.py/*.ts/*.tsx/*.js` under project + sibling roots; a definition hit returns `symbol_def`, treated as anchor-confirmed (the def existing IS the grounding; a symbol's "line" is meaningless). Until fully trusted, treat HALLUCINATED on a method/class/function citation as "grep for the def," not "discard."
- **[2026-06-10] PLAN reviews need ≥1 repo-access axis — packet-only reviewers critique the design; tool-having reviewers falsify the premises.** Evo behavior-tables plan: 3 packet-only axes (Gemini 3.5 Flash, GPT-5.5, Opus 4.8) produced solid design-level corrections — and all 3 missed that the plan's Phase-3 conversion target had ZERO production dispatch sites (dead parallel implementation), that a cited scenario-ID join didn't exist in the doc, and that the proposed compression already existed as a helper. The Fable SUBAGENT axis (repo tools, grepped dispatch sites) found all three, verdict REJECT; every claim verified. Rule: when reviewing a PLAN (not a diff — diffs carry their own ground truth), dispatch at least one axis with repo access (fable-subagent pattern, or any Agent-tool reviewer with Read/Grep), and tell it to verify the plan's premises (do the named functions have callers? do the cited join keys exist on BOTH sides?) before critiquing the design. Packets can never disprove "the code this plan converts is alive." *Second confirmation (2026-06-10, emb elevation plan): 24 packet-only findings (Gemini 3.5 Flash + GPT-5.5) missed both falsifiable premises — a "live caller" that was behind a never-passed flag (dormant LateChunker) and an overfetch hack justified by a stale comment (emb filters pre-ranking); the Fable repo-axis caught both plus a dead integration target (intel relevant_methods.py, zero invocations). Two-for-two on the same day.*
- **[2026-06-15] Repo-scale audit plans — lanes before packet-only critics; verify before trust.** Genomics lingering-bugs: orchestrator + 8 parallel lanes found load-bearing seams (`execution_plan` ≠ `freshness_verdict`, wrapper finalize) that packet-only 4-axis missed or drowned in noise (76 findings). Rule: `/critique audit-plan` requires repo-premise evidence before lean critics — parallel readonly lanes on first pass (or fresh lane manifest from same session), lane-partition completeness check, mechanical merge with lane-count manifest, then verify decision-dependent claims, then 2 orthogonal critics (sequencing + premise-soundness). Invariant: **no packet-only critic judges a repo-scale plan whose premises are unverified.** Parallel lanes are mandatory on first audit pass because orchestrator context omits module clusters — not replaceable by `build_plan_close_context.py` on unknown scope. llmx Claude: `llmx chat --subscription -m claude-opus-4-8` (API key in env without `--subscription` → "Credit balance too low"); critics run in background — orchestrator inspects task output and kills manually; no skill-prescribed `--timeout`. Commit convergence to `docs/audit/`; `.model-review/` stays gitignored.

$ARGUMENTS
