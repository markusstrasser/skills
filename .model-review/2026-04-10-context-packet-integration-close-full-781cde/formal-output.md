## 1. Logical Inconsistencies

| ID | Severity | Finding | Evidence | Why it is formally inconsistent |
|---|---|---|---|---|
| F1 | high | **Plan-close manifest budget does not describe the actual packet budget** | `build_plan_close_context.py` sets `BudgetPolicy(metric="chars", limit=max_diff_chars)`, default `40_000`. But the same packet also includes up to `max_files * max_file_chars` of excerpts: default `12 * 8_000 = 96_000` chars, plus status/stat metadata. | The manifest reports a 40k-char budget while the builder can legally emit ~136k+ chars. Reported limit is only ~29% of the plausible packet ceiling. That makes downstream budget metadata false as a bound. |
| F2 | high | **Overview trigger default threshold is inconsistent across consumers** | `shared/overview_config.py` default `OVERVIEW_LOC_THRESHOLD = 200`; `hooks/sessionend-overview-trigger.sh` defaults to `50`. | Same config key has two different defaults. This is a 4x divergence in trigger sensitivity. For projects without an explicit setting, automation behavior depends on which consumer reads the config. |
| F3 | high | **Live overview default prompt location changed without compatibility proof** | Old live shell default: `.claude/overview-prompts`; new `shared/overview_config.py` default: `~/Projects/skills/hooks/overview-prompts`. | This is contract drift, not just refactoring. Repos that relied on implicit project-local prompts now either get different prompts or failover behavior, while the migration is described as shared-mechanics unification. |
| F4 | medium-high | **Dispatch is still not packet-manifest canonical** | `scripts/llm-dispatch.py` still accepts `--context` without `--context-manifest`; tests call `dispatch(... context_text="ctx" ...)`; `shared/llm_dispatch.py` still emits both `context_sha256` and `context_payload_hash`. | The plan says dispatch should stop owning a parallel context-hash contract and prefer packet manifests. Current code still supports raw context transport as a first-class path, so canonical provenance is optional, not enforced. |
| F5 | medium | **Constitution discovery semantics narrowed relative to the reference contract** | `review/references/context-assembly.md` describes searching for `CONSTITUTION.md` broadly; `shared/context_preamble.py` checks `.claude/rules/constitution.md` or inline `CLAUDE.md`, not general standalone `CONSTITUTION.md`. | This is a semantic regression: the shared helper is not equivalent to the documented/manual search policy. Some projects will silently lose constitutional grounding after migration. |
| F6 | medium | **“Implemented” status overstates test-backed closure** | Plan file is marked `Status: implemented`, and docs say overview live/batch share one packet spine; but tests do **not** check live-vs-batch payload hash equivalence, plan-close golden output, or non-text source cases named in the plan risk section. | The migration claims stronger closure than the evidence supports. This is a reviewable “migration lie”: code may be improved, but the promised invariants are not verified. |

### Additional observations

1. **Leftover ad hoc contract parsing remains in hooks.**  
   `sessionend-overview-trigger.sh` and `overview-staleness-cron.sh` still parse `overview.conf` manually instead of using `shared.overview_config`. Even if packet assembly moved, contract interpretation did not fully centralize.

2. **Missing tests are concentrated exactly where drift risk is highest.**  
   Present tests cover:
   - packet artifact emission,
   - some git porcelain parsing,
   - basic overview packet creation,
   - dispatch metadata propagation.

   Missing tests cover:
   - overview config parity,
   - prompt default compatibility,
   - live/batch equivalence,
   - constitution discovery parity,
   - binary/symlink/submodule omission behavior,
   - plan-close manifest semantics.

3. **The largest quantitative defect is F1.**  
   The plan-close manifest can understate effective packet size by at least **96,000 chars** before counting git status and diff-stat. That is the strongest correctness issue in the provided code.

## 2. Cost-Benefit Analysis

| Rank | Change | Expected impact | Maintenance burden | Composability | Risk if unchanged | Value-adjusted rank |
|---|---|---|---|---|---|---|
| 1 | **Unify all overview.conf parsing through `shared.overview_config`** | Eliminates explicit 4x threshold drift and future field drift | low | high | repeated silent behavior skew across hooks | highest |
| 2 | **Make packet manifest provenance canonical in `shared.llm_dispatch`** | Removes parallel raw-context contract; makes hashes and budgets trustworthy | medium | very high | future callers bypass manifests and recreate drift | very high |
| 3 | **Fix plan-close budget semantics** | Prevents misleading manifests and bad downstream budgeting | low | high | budget-based tooling will make wrong truncation/admission decisions | high |
| 4 | **Codify overview prompt default behavior** | Prevents silent prompt changes across repos | low-medium | medium | overview output quality changes without config changes | high |
| 5 | **Add regression tests for equivalence and non-text policy** | Converts migration claims into enforceable invariants | medium | very high | silent regressions recur | high |

### Per-change analysis

#### 1. Unify overview config parsing
- **Benefit:** fixes a concrete contradiction already present (`50` vs `200`).
- **Maintenance drag reduced:** one parser, one set of defaults, one normalization policy.
- **Risk of not doing it:** each hook remains a shadow spec.

#### 2. Canonicalize manifest-based dispatch
- **Benefit:** packet hash, budget metadata, and provenance become single-source-of-truth.
- **Maintenance drag reduced:** fewer code paths to reason about when outputs are disputed.
- **Risk of not doing it:** “shared packet engine” remains advisory rather than architectural.

#### 3. Fix plan-close budget metadata
- **Benefit:** makes manifests truthful and usable for future routing/truncation.
- **Maintenance drag reduced:** avoids debugging “why did a 40k-budget packet contain 130k chars?”
- **Risk of not doing it:** any future budget-aware automation inherits false assumptions.

#### 4. Codify prompt default compatibility
- **Benefit:** stops silent semantic changes in overview generation.
- **Maintenance drag reduced:** fewer repo-specific mysteries caused by implicit defaults.
- **Risk of not doing it:** behavior depends on historical assumptions not encoded anywhere.

#### 5. Add regression tests
- **Benefit:** strongest defense against migration drift.
- **Maintenance drag reduced:** lower supervision cost on future refactors.
- **Risk of not doing it:** “implemented” remains mostly narrative.

## 3. Testable Predictions

| Prediction | How to test | Success criterion | Failure criterion |
|---|---|---|---|
| P1 | In a repo with no `OVERVIEW_LOC_THRESHOLD`, a change of 60–199 LOC will trigger session-end generation more often than the shared config default implies | Create temp repo, omit threshold, modify 100 LOC, run trigger logic and generator config load | Both consumers resolve the same effective threshold | Trigger logic fires at 100 LOC while shared config resolves threshold 200 |
| P2 | A repo relying on implicit local `.claude/overview-prompts/source.md` will produce a different payload after migration | Build payload once with old live default semantics and once with new Python defaults | Payload hashes match, or the script fails loudly with explicit compatibility error | Payload hashes differ silently or new path ignores local prompt |
| P3 | `shared.llm_dispatch` still allows non-manifest context provenance | Call `dispatch()` with `context_text` only and inspect meta output | Dispatch rejects raw context or marks it as deprecated/non-canonical | Dispatch succeeds normally and writes meta with `context_sha256` sans manifest |
| P4 | Plan-close manifests can materially understate actual packet size | Build a packet with default caps and large excerpts; compare `budget_limit` to rendered bytes/chars | `budget_limit` reflects total packet cap or is absent when not meaningful | Rendered content substantially exceeds the advertised limit |
| P5 | Constitution discovery is narrower than the documented/manual behavior | Put `CONSTITUTION.md` at repo root or `docs/CONSTITUTION.md`; run shared preamble builder | Constitution is detected in all documented/manual cases | Shared helper fails to include constitution in those cases |
| P6 | Live and batch overview modes are not yet proven equivalent | Generate payload for same repo/type through both paths and compare payload hashes | Hashes are equal for identical inputs | Hashes differ or no test exists to enforce equality |

### Claims that cannot yet be made testable from the provided excerpt
- Whether `model-review.py` truly reuses one shared context file across all axes. The excerpt does not show `build_context()`.

## 4. Constitutional Alignment (Quantified)

No constitution provided, so this is an internal-consistency audit.

| Objective implied by the plan | Observed state | Score (/10) |
|---|---|---:|
| One canonical context/provenance path | Not achieved; raw context path still first-class in dispatch | 4 |
| Overview contract unification | Not achieved; threshold defaults and prompt defaults diverge | 3 |
| Provenance inspectability | Improved via manifests, but not canonicalized | 7 |
| Migration honesty | Mixed; code improved, but “implemented” exceeds test evidence | 5 |
| Regression resistance | Weak in the highest-risk areas | 3 |

**Weighted internal-consistency score: 4.4 / 10**

### Quantified rationale
- **+2.0** for real shared modules now existing (`context_packet`, renderers, overview config, repomix helpers).
- **+1.2** for manifests/hashes being emitted at all.
- **+1.2** for shell wrappers being reduced to thin entrypoints.
- **-1.5** for contract drift in overview defaults.
- **-1.2** for dispatch remaining non-canonical.
- **-1.1** for insufficient regression tests relative to explicit plan promises.
- **-0.2** for narrowed constitution detection semantics.

Net: **4.4/10**. This is a meaningful refactor, but not a fully closed migration.

## 5. My Top 5 Recommendations (different from the originals)

### 1. Make `shared.overview_config` the only parser of `overview.conf`
- **What:** Replace manual parsing in `sessionend-overview-trigger.sh` and `overview-staleness-cron.sh` with a Python helper or CLI that returns normalized config.
- **Why:** There is already a concrete 4x default drift (`50` vs `200`). One parser removes an entire class of skew bugs.
- **How to verify:**  
  - Add a golden config matrix test covering blank config, quoted values, comments, and missing keys.  
  - Metric: **0 default-value mismatches** across generator, trigger, and cron consumers.

### 2. Deprecate raw-context dispatch and require manifest-backed context for automation
- **What:** In `shared.llm_dispatch`, require either `context_manifest_path` or an explicit `raw_context=True` escape hatch; stop presenting `context_sha256` as a parallel provenance contract.
- **Why:** Right now canonical packet provenance is optional, which defeats the point of the shared packet spine.
- **How to verify:**  
  - Add tests that automation entrypoints fail or warn when no manifest is supplied.  
  - Metric: **100% of scripted dispatches write `context_payload_hash` sourced from a manifest**.

### 3. Correct plan-close budget metadata to represent total packet limits, not just diff limits
- **What:** Either compute a total-packet budget bound or emit per-section limits (`diff_limit`, `file_excerpt_limit`, `max_files`) instead of a misleading single `budget_limit`.
- **Why:** Current metadata can underreport actual packet size by ~96k chars or more under defaults.
- **How to verify:**  
  - Test generated packet size against manifest semantics.  
  - Metric: **manifest budget claims never understate possible rendered content by >5%**.

### 4. Freeze overview prompt default semantics explicitly
- **What:** Decide between:
  1. preserve old live default (`.claude/overview-prompts`),
  2. require explicit `OVERVIEW_PROMPT_DIR`,
  3. support fallback order: project-local first, shared second.
- **Why:** Prompt text is behavior, not formatting. Silent default changes are semantic regressions.
- **How to verify:**  
  - Add compatibility tests for repos with and without explicit `OVERVIEW_PROMPT_DIR`.  
  - Metric: **payload hash stability across migration for unchanged configs**, or explicit failure with a migration message.

### 5. Add the regression suite the plan explicitly promised
- **What:** Add tests for:
  - live vs batch payload hash equivalence,
  - plan-close golden packet + manifest,
  - constitution discovery matrix,
  - binary/symlink/submodule omission behavior.
- **Why:** These are the exact areas where the plan called out risk, and they remain unguarded.
- **How to verify:**  
  - CI must fail on any payload-hash drift or omission-policy regression.  
  - Metric: **4 new invariant suites passing in CI**.

## 6. Where I'm Likely Wrong

1. **I may be underrating hidden logic in truncated sections.**  
   The excerpt omits part of `scripts/generate_overview.py` and `model-review.py`. There may already be checks for token enforcement, shared-context reuse, or compatibility handling that would soften some conclusions.

2. **I may be treating deliberate standardization as accidental drift.**  
   The prompt-dir default change could be an intentional choice to align live behavior with the old batch behavior. If so, the defect is less “wrong default” and more “uncodified breaking change.”

3. **I am biased toward making provenance contracts stricter than the current repo may need.**  
   Requiring manifests everywhere is architecturally cleaner, but if ad hoc/manual invocation is an important workflow, a softer deprecation may be better than a hard requirement.

4. **I may be over-weighting metadata correctness versus immediate runtime correctness.**  
   The plan-close budget issue is a real formal defect, but it may not break current users until routing/truncation decisions start consuming that manifest.

5. **I cannot prove from the excerpt that model-review still duplicates axis contexts.**  
   I avoided making that a core finding because the visible code does not show `build_context()`. If that function already reuses one shared file, then that specific migration claim may actually be satisfied.