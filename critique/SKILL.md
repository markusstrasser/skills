---
name: critique
description: "Use when: 'what's wrong with this', 'review the plan', 'close out the implementation', 'fact-check these findings'. Modes: /critique model (Gemini+GPT adversarial), /critique verify (fact-check LLM output), /critique close (post-implementation tests+review). Renamed from /review (built-in conflict)."
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
| `verify` | `/critique verify <report>` | Fact-check LLM findings against actual code |
| `close` | `/critique close` | Post-implementation: tests, review, caught-red-handed loop |

**Auto-routing (when no mode specified):**
- Recent plan in `.claude/plans/` with commits since plan start → `close`
- Recent findings/audit output in context → `verify`
- Otherwise → `model`

---

## Mode: model — Cross-Model Adversarial Review

**Purpose:** Convergent/critical only — find what's wrong. For divergent ideation, use `/brainstorm`.

See `lenses/adversarial-review.md` for full dispatch methodology, axis descriptions, depth presets, per-model prompts, and known issues.

### 1. Assemble Context

Write review material to a single context file.

**Pre-flight — scope declaration (mandatory):** Include a `## Scope` block near the top:
- **Target users:** personal / team / multi-tenant / public
- **Scale:** current entity counts AND designed-for scale (e.g., "currently 40 compounds, designed for thousands of subjects")
- **Rate of change:** how often does new data arrive?

This prevents the #1 review failure mode: models optimizing for the wrong scale. Evidence: selve UMLS review (2026-04-06) — GPT scored a plan 27/100 as "over-engineered for 105 personal entities" when the actual scope was multi-user scalable.

**Constitutional anchoring:** Check for constitution (`## Constitution` in CLAUDE.md) and GOALS.md. Include as preamble if found.

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

### 2. Dispatch

**Always use the script.** It handles: context assembly, constitutional preamble injection, parallel dispatch to Gemini + GPT via the shared dispatch core, extraction, and disposition generation.

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract \
  "$ARGUMENTS"
```

Set `timeout: 660000` on the Bash tool call. See `references/dispatch.md` for `--questions`, `--context-files`, depth presets, effort levels, and troubleshooting.

**Model-specific prompting:** Before assembling context, consult `/model-guide` for per-model rules. Key: GPT-5.4 context should use XML `<doc>` tags, Gemini query goes at END. See `references/dispatch.md § Context Formatting` for the full checklist.

**Effort levels:** Default `high` is correct for reviews. Use `xhigh` only for formal math verification. See `references/dispatch.md § Reasoning Effort Selection`.

**GPT-only multi-query pattern:** For deep dives where you want multiple focused attack vectors, dispatch 2-3 GPT-5.4 `high` queries in parallel with different questions each, rather than one mega-query. More signal per unit time.

#### Depth Presets

| Preset | Axes | When |
|--------|------|------|
| `standard` (default) | arch (Gemini) + formal (GPT-5.4) | Most reviews |
| `--axes deep` | arch + formal + domain + mechanical | Structural changes, domain-dense |
| `--axes full` | all 5 | Shared infra, clinical, high-stakes |

User-facing presets are `standard`, `deep`, and `full`; each includes GPT-5.4.
Non-GPT axis sets are internal-only and rejected by the default CLI contract.

**Genomics classification review** (monthly or after >10 commits to LR-engine/scoring): Use `--axes formal,domain`. GPT-5.4 found 11 conceptual/mathematical bugs for $6.54 — the only detector for incoherent Bayes.

### 3. Read Both Outputs and Synthesize

Read both review outputs. You are the merger — you have both in context and can cross-reference directly.

**For each finding from either model:**
1. **Verify code claims** — read the actual file. Models frequently cite wrong line numbers, invent function names.
2. **Check if both models found it** — cross-model agreement is the strongest signal.
3. **Grep "missing feature" claims** — the feature may already exist.

**Trust ranking:**

| Signal | Action |
|--------|--------|
| Both models found it + you verified in code | Fix it |
| One model found it + you verified in code | Fix it |
| Both agree but unverified | Verify first |
| Single model, unverified | Investigate before acting |
| Contradicts what you see in the code | Discard |

**Before implementing:** Ask yourself two questions:
1. Where do you disagree with the models? ("Nowhere" is valid.)
2. What context did you have that they didn't?

Don't let rigorous-looking analysis override what you can see in the code.

### 4. Act on Findings

**The synthesis is not the deliverable — the updated artifact is.**

- **Verified findings:** Apply directly. Don't ask permission.
- **Context depleted:** Offer plan-mode handoff.
- **All deferred/rejected:** The synthesis is the deliverable.

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

1. **Empirical (suspense accounts, 2026-04-07):** GPT-5.4 found 6 confirmed bugs in freshly committed code. All 74 canary tests and 11 IR invariants passed. The bugs were in new functions with zero test coverage.

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

**Phase 1: Write Tests for New Code** — Identify new functions from plan commits. Write unit tests covering happy path, edge cases, error paths, and contract invariants.

**Phase 2: Cross-Model Review** — Run `/critique model` on the plan-close review packet (not a hand-written summary). Use `--context .model-review/plan-close-context.md --extract --verify`. Fact-check and disposition every finding. Inspect `coverage.json` before closing so you can see packet drops, axis coverage, and verification totals.

**Phase 3: The Caught-Red-Handed Loop** — For each confirmed finding: would any Phase 1 tests have caught this? If yes, fix the test gap. If no, write a new test. Verify against pre-fix code:
```bash
git stash
pytest tests/test_<new>.py -x  # should FAIL
git stash pop
pytest tests/test_<new>.py -x  # should PASS
```

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
- **[2026-03-27] shared dispatch output — never use shell redirects (> file) for review artifacts; the shared review script writes directly to files. Shell redirects buffer until process exit, producing 0-byte files.**
- **[2026-04-09] GPT-5.4 xhigh timeout — shared dispatch timeout is 300s by default; xhigh needs 900s. Set `--timeout 900` for xhigh, `--timeout 600` for high. Three parallel xhigh calls may hit rate limits — run sequentially or use high effort instead.**
- **[2026-04-09] xhigh vs high for architectural review — marginal quality delta. High-effort adversarial review (4 min) found the sharpest insight across 6 reviews. xhigh (15 min each) had more words, similar signal density. Reserve xhigh for formal math only. For deep dives: 2-3 parallel high queries with focused questions > 1 xhigh mega-query.**
- **[2026-04-09] Context formatting matters — GPT-5.4 performs better with XML `<doc>` tags around context sections. Gemini needs query at END, critical constraints at END. Consult /model-guide before assembling context for manual dispatch.**
- **[2026-04-11] FIXED — Python version mismatch in `_bootstrap_llmx()`: when running model-review.py via `uv run` from a project whose venv Python differs from the llmx tool install's Python (e.g., phenome 3.12 vs llmx tool 3.13), the previous fallback used `glob.glob` to inject ANY available `python*/site-packages` from the llmx tool install into `sys.path`. Result: 3.13 compiled `.so` files (e.g. `pydantic_core._pydantic_core.cpython-313-darwin.so`) loaded into a 3.12 process, producing the cryptic `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`. Fix in `shared/llm_dispatch.py` now matches Python `major.minor` exactly and raises a clear `ImportError` if no matching version is found. Workaround: run model-review.py via `/Users/alien/.local/share/uv/tools/llmx/bin/python3 .../model-review.py` (the llmx tool's own Python) — verified working with both Gemini + GPT-5.4 axes returning real output. Or `uv pip install llmx` in the current project venv.**
- **[2026-04-13] --verify pass can hang on a single finding** — model-review.py's `--verify` pass verifies each extracted finding serially. If one verification call gets stuck on a network round-trip, the whole process goes quiet even though extraction + per-model outputs are already written. Symptom: `arch-output.md`, `formal-output.md`, and `formal-extraction.parsed.json` are present in `.model-review/<topic>-<hash>/` but no `verified-disposition.md`. The process is alive but using <1s CPU. Action: kill the hung process and work from the extracted findings directly (`formal-extraction.parsed.json` is already machine-readable). Don't wait — the timeout doesn't help when the hang is inside the verify loop.

$ARGUMENTS
