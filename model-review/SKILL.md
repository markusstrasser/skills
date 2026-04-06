---
name: model-review
description: Cross-model adversarial review via llmx. Dispatches to Gemini 3.1 Pro and GPT-5.4 for independent critique, then fact-checks and synthesizes surviving insights. Convergent/critical mode only — for divergent ideation, use /brainstorm.
argument-hint: [topic or decision to review — e.g., "selve search architecture", "authentication redesign"]
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
effort: high
---

# Cross-Model Adversarial Review

Same-model peer review is a martingale — no expected correctness improvement (ACL 2025, arXiv:2508.17536). Cross-model review provides real adversarial pressure because models have different failure modes, training biases, and blind spots.

**Mode:** Convergent/critical only — find what's wrong. For divergent ideation, use `/brainstorm`.

## Session Awareness

`!cat ~/.claude/active-agents.json 2>/dev/null | python3 -c "import sys,json,time; entries=json.load(sys.stdin); active=[e for e in entries if time.time()-e.get('started_at',0)<7200]; print(f'{len(active)} active sessions') if len(active)>=3 else None" 2>/dev/null`

If 3+ sessions active: prefix questions with project name + review topic. Batch decisions.

**Memory pressure gate:** Before dispatching subagents, count active Claude/Codex processes. On macOS/BSD, `pgrep` does NOT support `-c`; use `pgrep -lf claude | wc -l` or `~/.claude/active-agents.json`. If count >= 4, skip subagent delegation and work directly with llmx CLI calls. 50% of sessions hit memory pressure on dispatch.

## Dispatch Models

| Role | Model | Use |
|------|-------|-----|
| **Gemini** (pattern/arch) | `gemini-3.1-pro-preview` | Deep review — cross-referencing, pattern detection |
| **GPT** (quantitative) | `gpt-5.4 --reasoning-effort high --stream --timeout 600 --max-tokens 32768` | Deep review — logical inconsistencies, cost-benefit. **Must use --max-tokens 32768** (reasoning tokens count against limit; 16384 = empty output). |
| **Gemini Fast** | `gemini-3-flash-preview` | Extraction in Step 5, mechanical audits |
| **GPT Fast** | `gpt-5.3-chat-latest --stream` | Extraction in Step 5, fact-checking |

**Why these:** Adversarial needs deep reasoning from both sides. Pro for large-context cross-referencing; GPT-5.4 high-reasoning for formal fault-finding. **Fast models for extraction only** — Step 5 is mechanical, fast models do it equally well at 10x lower cost.

**Reasoning model caveat:** Research on LLM-as-judge biases (position, self-preference, sycophancy) was measured on pre-reasoning models. Reasoning models show measurably lower sycophancy (SYCON Bench, arXiv:2505.23840). Correlated error rates (60% shared wrong answers, Kim et al. ICML 2025) were on pre-reasoning Helm models — actual for current reasoning models is likely lower but unmeasured. Treat as upper bounds.

## CLI-First Prompting

`llmx -p google` and `llmx -p openai` fall back to API transport with `-s`. To keep CLI transport, inline system instructions with `<system>...</system>` and omit `-s`. That `<system>` block is prompt text (not a true system role) — it preserves CLI transport, which is cheaper and more reliable. Use `-s` only when you need true system channel or structured API features.

## The Process

### Step 1: Define Review Target

State clearly: `$ARGUMENTS`. Identify the decision/recommendation/code under review, who made it, what evidence exists.

### Step 2: Assemble Context

Write material to a single context file. The dispatch script adds constitutional preamble automatically.

**Do NOT manually create `.model-review/` directories, write constitutional preambles, or assemble per-model files.** The script handles all of this.

**Token budgets:** Gemini Pro sweet spot 80-150K (max ~800K). GPT-5.4 sweet spot 40-100K (max ~400K). Compact aggressively — 50K context = 5-10 min; 2K summary = ~1 min. Summarize rather than concatenate full files.

**Pre-flight — constitutional check:** Before building context, check for constitution (standalone CONSTITUTION.md or `## Constitution` section in CLAUDE.md) and GOALS.md. If found, inject as preamble. If neither exists, warn user: *"No constitution or GOALS.md found. Reviews will lack project-specific anchoring."* Proceed anyway.

See `references/context-assembly.md` for detailed context gathering (narrow, broad, auto-assembled).

#### Context Assembly Anti-Patterns (Critical — Shared Context = Shared Wrong Answers)

When both models converge on the same wrong recommendation, the cause is almost always shared context bias. Check for these before dispatching:

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
| **Constitutional principles without exception clauses** | Models apply principles rigidly without carve-outs | Co-locate exceptions with principles |

### Step 2.5: Review Depth

Classify by blast radius, not file count:

| Preset | Axes | Queries | When |
|--------|------|---------|------|
| `simple` | combined Gemini Pro | 1 | Config tweaks, refreshes |
| `standard` | arch + formal | 2 | Most new features (default) |
| `deep` | arch + formal + domain + mechanical | 4 | Structural changes, domain-dense |
| `full` | all 5 | 5 | Shared infra, clinical, high-stakes |

| Axis | Model | What it checks |
|------|-------|---------------|
| `arch` | Gemini Pro | Patterns, architecture, cross-reference |
| `formal` | GPT-5.4 (high reasoning) | Math, logic, cost-benefit, testable predictions |
| `domain` | Gemini Pro | Domain fact correctness. Skip for pure code reviews. |
| `mechanical` | Gemini Flash | Stale refs, wrong paths, naming. Include grep results — Flash hallucinates about fixed state (~13%). |
| `alternatives` | Kimi K2.5 | 3-5 genuinely different approaches |

**Genomics classification review** (monthly or after >10 commits to LR-engine/scoring): Use `--axes formal,domain`. GPT-5.4 found 11 conceptual/mathematical bugs for $6.54 — the only detector for incoherent Bayes, wrong concordance, excluded FDR families, surrogate endpoint fallacy.

### Step 3: Dispatch

Always use the script. See `references/dispatch.md` for full dispatch mechanics, CLI flags, timeout values, and manual dispatch instructions.

**Quick reference:**
```bash
uv run python3 ~/Projects/meta/scripts/model-review.py \
  --context context.md --topic "$TOPIC" --project "$(pwd)" --extract \
  "What's wrong with this [thing being reviewed]"
```

Set `timeout: 660000` on the Bash tool call. Add `--extract` to all standard/deep reviews.

**NEVER downgrade models on failure.** If Pro or GPT-5.4 fails, the problem is dispatch (timeout, redirect, context size, rate limit) — not the model. Diagnose via stderr/exit code/`llmx --debug`. Never swap to Flash or GPT-5.3 as a "fix."

### Step 4: Fact-Check (Mandatory)

**Both models hallucinate. Never adopt without verification.**

1. **Code claims** — Read the actual file. Models frequently cite wrong line numbers, invent function names.
2. **Research claims** — Check if the cited finding actually says what the model claims.
3. **"Missing feature" claims** — Grep the codebase. The feature may already exist.

Use a **different model family** than the claim's author. Cross-family verification: +31pp accuracy vs same-family (FINCH-ZK, Amazon 2025). For code claims, always verify by reading the actual file first.

### Step 5: Extract & Enumerate

**STOP — did the script run with `--extract`?** If yes, read `disposition.md` and skip to Step 6. If not, see `references/extraction.md` for manual extraction workflow.

The core rule: **never go from raw model outputs directly to synthesis.** Extract mechanically first (cross-family fast models), then disposition every item, then synthesize. Extraction before synthesis: +24% recall, +29% precision (EVE, arXiv:2602.06103).

### Step 6: Synthesize

Build synthesis from the disposition table. Every INCLUDE item must appear. Reference IDs for auditability.

**Trust ranking:**

| Level | Criterion | Action |
|-------|-----------|--------|
| Very high | Both agree + code-verified | Adopt |
| High | One found + code-verified | Adopt |
| Medium | Both agree, unverified | Verify first |
| Low | Single model, unverified | Flag for investigation |
| Reject | Self-recommendation or contradicts verified code | Discard |

**Output header:**
```
## Cross-Model Review: [topic]
Models: [actual], Date: YYYY-MM-DD, Constitutional anchoring: Yes/No
Extraction: N items, M included, D deferred, R rejected
```

Sections: Verified Findings | Deferred | Rejected | Where I Was Wrong | Gemini Errors | GPT Errors | Revised Priority List

### Step 6.5: Auto-Verify File-Specific Findings

If synthesis has INCLUDE items with file:line citations, invoke `/verify-findings` on the synthesis before Step 7. Only implement CONFIRMED or CORRECTED findings. Drop HALLUCINATED. Skip if all findings are architectural or fewer than 3 code citations.

### Step 6.8: Over-Adoption Check

The review models had less context than you. Before rewriting the artifact, answer:

1. **Where do you disagree with the disposition, if anywhere?** "Nowhere — I agree with all of it" is a valid answer. Don't invent disagreements.
2. **Did you have context the models didn't?** If yes, name it. If the context file was comprehensive, say so and move on.

Valid outcomes:
- **"No changes."** Proceed to Step 7 with disposition as-is.
- **"Revising N items."** State which and why, update synthesis, then Step 7.

**Why this exists:** Models produce rigorous-looking analysis that can override your judgment through sheer detail. The check is a pause, not a filter — most times you'll agree and continue.

### Step 7: Close the Loop (Mandatory if INCLUDE items exist)

**The synthesis is not the deliverable — the updated artifact is.**

- **Case A (existing plan/doc):** Apply verified INCLUDEs directly. Tag changes with finding IDs. Don't ask permission.
- **Case B (decision/code, no plan):** Offer plan-mode handoff if context is depleted.
- **Case C (all DEFER/REJECT):** Synthesis is the deliverable.

## Known Model Biases

| Bias | Effect | Countermeasure |
|------|--------|----------------|
| **Correlated errors** | ~60% shared wrong answers when both err (Kim ICML 2025, pre-reasoning) | Never same-family reviewer + synthesizer |
| **Self-preference** | 74.9% demographic parity bias (Wataoka NeurIPS 2024) | Different-family synthesis; weight cross-family disagreements |
| **Judge inflation** | Same-provider accuracy inflation (Kim ICML 2025) | Cross-family only (this skill already does this) |
| **Debate = martingale** | Sequential discussion: no correctness improvement (Choi 2025, formal proof) | Independent parallel reviews, never let models respond to each other |

**Per-model:**
- **Gemini Pro:** Production-pattern bias (enterprise for personal projects), self-recommendation (Google services), instruction dropping in long context
- **GPT-5.4:** Confident fabrication (invents numbers/paths), overcautious scope, production-grade creep
- **Flash/GPT-5.3:** Shallow analysis (extraction only), recency bias. Never use for architectural judgment.

**Gemini Pro specifics:** CLI transport (free), temp locked 1.0, bare mode ~40% faster, no `--fallback`. **GPT-5.4 specifics:** `--reasoning-effort high` essential, `--stream` required, `--timeout 600` minimum, `--max-tokens 32768`. See `references/prompts.md` for full templates.

## Anti-Patterns

- **Synthesizing without extracting.** #1 information loss. Always extract + disposition before prose.
- **Synthesizing a synthesis.** Each compression drops ideas. Merge raw extractions, not prior syntheses.
- **Adopting without code verification.** Both models hallucinated "missing" features that already existed.
- **Model agreement = proof.** Agreement is evidence, not proof — verify against source code.
- **Debate workflow.** Martingale. Independent parallel + voting beats sequential discussion.
- **Same-family reviewers.** Same-model correction: 59.1%. Cross-family: 90.4% (FINCH-ZK).
- **"Top N" triage.** If INCLUDE, implement. DEFER needs explicit reason per item.
- **Skipping self-doubt section.** Most valuable part of each review.
- **Same prompt to both models.** Gemini = patterns, GPT = quantitative/formal. Different strengths need different prompts.
- **Writing to /tmp.** Persist to `.model-review/YYYY-MM-DD-topic/`.
- **Bare date directories.** Always append topic slug to avoid same-day collisions.
- **Skipping constitutional check.** Unanchored reviews drift into generic advice.
- **Mixing review and brainstorming.** Convergent only. Use `/brainstorm` for divergent.
- **Priming tool names in review prompt.** Turns critique into evaluation. Use `alternatives` axis separately.
- **Scale-ambiguous context.** Both models converge on the same wrong answer from shared misleading context.

## Artifact Handoff

Write summary JSON to `~/.claude/artifacts/$(basename $PWD)/model-review-$(date +%Y-%m-%d).json` with: skill, project, date, topic, include/defer/reject counts, key_findings[]. Used by project-upgrade as a cache gate.

$ARGUMENTS

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] llmx output flag — never use shell redirects (> file) with llmx; use --output/-o flag instead. Shell redirects buffer until process exit, producing 0-byte files. Fixed in llmx v0.5.0 (2026-03-06).**
