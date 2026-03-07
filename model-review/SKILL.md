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
---

# Cross-Model Adversarial Review

You are orchestrating a cross-model review. Same-model peer review is a martingale — no expected correctness improvement (ACL 2025, arXiv:2508.17536). Cross-model review provides real adversarial pressure because models have different failure modes, training biases, and blind spots.

## Prerequisites

- `llmx` CLI installed (`which llmx`)
- API keys configured for Google (Gemini) and OpenAI (GPT)
- Gemini Flash for fact-checking (`llmx -m gemini-3-flash-preview`)

## Dispatch Models

| Role | Model | Use |
|------|-------|-----|
| **Gemini** (pattern/architecture) | Pro (`gemini-3.1-pro-preview`) | Deep review — cross-referencing, pattern detection |
| **GPT** (quantitative/formal) | GPT-5.4 (`gpt-5.4 --reasoning-effort high --stream --timeout 600`) | Deep review — logical inconsistencies, cost-benefit |
| **Gemini Fast** (extraction) | Flash (`gemini-3-flash-preview`) | Structured extraction in Step 5, mechanical audits |
| **GPT Fast** (extraction) | GPT-5.3 Instant (`gpt-5.3-chat-latest --stream`) | Structured extraction in Step 5, fact-checking |

**Why these models:** Adversarial review needs deep reasoning from both sides. Gemini Pro for cross-referencing across large context; GPT-5.4 with `--reasoning-effort high` for formal fault-finding. **Fast models for extraction:** Step 5 (extract + disposition) is mechanical — fast models do it equally well at 10x lower cost and latency. Use Flash or GPT-5.3 Instant for claim extraction, not the deep reviewers.

**Note on reasoning models and bias:** All four review/extraction models are reasoning/thinking models (2026 generation). Research on LLM-as-judge biases (position bias, self-preference, sycophancy) was primarily measured on pre-reasoning models (GPT-4, Llama-2/3). Reasoning models show measurably lower sycophancy (SYCON Bench, arXiv:2505.23840) and thinking models bypass positional bias by reasoning about information location. The correlated error rates (60% shared wrong answers, Kim et al. ICML 2025) were measured on pre-reasoning Helm models — actual correlation for current reasoning models is likely lower but unmeasured.

## CLI-First Prompting Rule

`llmx -p google` and `llmx -p openai` fall back to API transport if you use `-s`. If you want `gemini-cli` / `codex-cli` by default, inline the system instructions at the top of the prompt with a `<system>...</system>` block and omit `-s`.

Treat that `<system>` block honestly:

- It is prompt text, not a true transport-level system role
- It preserves CLI transport, which is often cheaper and more reliable for repeated review work
- If you need a true system channel or structured features that only API transport supports, use `-s` and accept the fallback

## Pre-Flight: Constitutional Check

Before building context, check if the project has constitutional documents:

```bash
# Check for project principles — constitution may be standalone or a section in CLAUDE.md
CONSTITUTION=$(find . -maxdepth 3 -name "CONSTITUTION.md" 2>/dev/null | head -1)
if [ -z "$CONSTITUTION" ]; then
  # Check for ## Constitution section in CLAUDE.md (preferred location since 2026-03)
  CLAUDE_MD=$(find . -maxdepth 1 -name "CLAUDE.md" | head -1)
  if [ -n "$CLAUDE_MD" ] && grep -q "^## Constitution" "$CLAUDE_MD"; then
    CONSTITUTION="$CLAUDE_MD"  # Use CLAUDE.md — constitution is inline
  fi
fi
GOALS=$(find . -maxdepth 3 -name "GOALS.md" 2>/dev/null | head -1)
```

- **If constitution found (standalone or in CLAUDE.md):** Inject as preamble into ALL context bundles. Instruct models to review against project principles, not their own priors.
- **If GOALS.md exists:** Inject into GPT context (quantitative alignment check) and Gemini context (strategic coherence).
- **If neither exists:** Warn the user: *"No constitution (in CLAUDE.md or standalone) or GOALS.md found. Reviews will lack project-specific anchoring. Consider `/constitution` or `/goals` first."* Proceed anyway — cross-model review still has value without constitutional grounding.

## Mode

This skill is **convergent/critical only** — find what's wrong: errors, inconsistencies, missed edge cases, violations of stated principles.

- Lower temperature for Gemini (`-t 0.3`) — more deterministic, stern
- GPT reasoning-effort high — deep fault-finding
- Prompts ask "what's wrong" and "where does this break"
- Output: ranked list of problems with verification criteria

For **divergent ideation** (generate ideas, alternative approaches, novel connections), use `/brainstorm`.

## The Process

### Step 1: Define the Review Target

State clearly what's being reviewed: `$ARGUMENTS`

Identify:
- **The decision/recommendation/code** under review
- **Who made it** (you, a previous Claude session, a human)
- **What evidence exists** (code, configs, research, benchmarks)
- **Mode:** Review (convergent)

### Step 2: Bundle Context

Build context files. Constitutional documents go first (if found).

**Output directory setup:**
```bash
# Persist outputs — NOT /tmp
# Slug from topic prevents collisions when multiple reviews run on the same day
REVIEW_SLUG=$(echo "$TOPIC" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-' | sed 's/^-//;s/-$//' | cut -c1-40)
REVIEW_ID=$(openssl rand -hex 3)
REVIEW_DIR=".model-review/$(date +%Y-%m-%d)-${REVIEW_SLUG}-${REVIEW_ID}"
mkdir -p "$REVIEW_DIR"
```

Where `$TOPIC` is a short label for the review target (e.g., "hook architecture", "search retrieval").
Use the first 2-3 words of the review subject. Examples:
- `.model-review/2026-03-01-hook-architecture/`
- `.model-review/2026-03-01-search-retrieval/`
- `.model-review/2026-02-28-genomics-split/`

**Choose context scope based on review type:**

| Review scope | When | Context method |
|-------------|------|----------------|
| **Broad** (whole codebase, architecture) | "Review our hook architecture", "Audit the pipeline" | `.context/` views — pre-built, deterministic |
| **Narrow** (specific plan, analysis, code) | "Review this data-wiring plan", "Check this scoring formula" | Manual assembly — just the relevant files |

Most reviews are narrow. Don't dump `full.xml` into a review of one plan document.

**Both approaches always start with constitutional anchoring:**
```bash
# Constitutional prefix — always include
if [ -f ".context/constitution.xml" ]; then
  cat .context/constitution.xml > "$REVIEW_DIR/gemini-context.md"
  cat .context/constitution.xml > "$REVIEW_DIR/gpt-context.md"
elif [ -n "$CONSTITUTION" ]; then
  for f in "$REVIEW_DIR/gemini-context.md" "$REVIEW_DIR/gpt-context.md"; do
    echo -e "# PROJECT CONSTITUTION\nReview against these principles, not your own priors.\n" > "$f"
    cat "$CONSTITUTION" >> "$f"
    [ -n "$GOALS" ] && { echo -e "\n# PROJECT GOALS\n" >> "$f"; cat "$GOALS" >> "$f"; }
  done
fi
```

**Broad reviews — use `.context/` views:**
```bash
# Rebuild if stale (Make tracks deps)
make -C .context all 2>/dev/null

# Available views:
#   full.xml        — everything (Gemini: large context)
#   src.xml         — source code only
#   docs.xml        — documentation
#   infra.xml       — scripts/hooks
#   signatures.xml  — compressed function outlines (GPT: smaller context)
#   filetree.xml    — directory structure only
#   diffs.xml       — uncommitted changes
```

| Review type | Gemini gets | GPT gets |
|------------|-------------|----------|
| Architecture | full.xml | signatures.xml |
| Code review | src.xml | src.xml |
| Infra/hooks | infra.xml | infra.xml |
| Delta review | diffs.xml | diffs.xml |

**Narrow reviews — manual assembly:**

Append only the specific files under review. Read them with the Read tool and write to context files. Include enough surrounding context for the models to understand the decision space (e.g., for a plan review, include the plan + the files it references).

**Token budgets:**
| Model | Sweet spot | Max useful | Note |
|-------|-----------|------------|------|
| Gemini 3.1 Pro | 80K-150K | ~800K | Handles large context well; quality doesn't degrade until ~1M |
| GPT-5.4 | 40K-100K | ~400K | 1M context now available — can handle larger reviews than 5.2 |

### Step 3: Dispatch Reviews (Parallel)

**CRITICAL: Fire both Bash calls in a SINGLE message (two parallel tool calls).** Do NOT wait for one model before calling the other. Both models run independently — dispatch them simultaneously to halve wall-clock time.

**Select models** (see Dispatch Models above):
```bash
# Gemini — Pro, no fallback (should just work)
GEMINI_MODEL="gemini-3.1-pro-preview"
# IMPORTANT: Gemini 3.1 Pro defaults to 8K maxOutputTokens server-side.
# Always use --max-tokens 65536 on Gemini dispatches to prevent silent truncation.
GEMINI_MAX_TOKENS="--max-tokens 65536"

# GPT — 5.4 with deep reasoning, no fallback
GPT_MODEL="gpt-5.4"
GPT_EFFORT="--reasoning-effort high --stream"
GPT_TIMEOUT="--timeout 600"
```

**IMPORTANT — Bash timeout:** When dispatching via the Bash tool, always set `timeout: 360000` (6 minutes) on the Bash tool call. The default 120s Bash timeout kills the process before llmx finishes. llmx's own `--timeout` handles the real deadline.

**Output capture:** Use `--output FILE` (or `-o FILE`) to write output to a file. This writes directly via Python (no shell buffering) — the file has content immediately on completion, not 0 bytes until process exit like `> file` redirects. Never use `> file` shell redirects with llmx. Never use `PYTHONUNBUFFERED` — the buffering is in the shell redirect, not Python.

**NEVER downgrade models on failure.** If Gemini Pro or GPT-5.4 fails, the problem is the dispatch (timeout, redirect, context size, rate limit) — not the model. Diagnose: check stderr, check exit code, check `llmx --debug`. Never swap to Flash, GPT-5.2, or GPT-5.3 as a "fix" — you lose the deep reasoning that's the entire point of model-review.

**CRITICAL — Context size:** Compact context before dispatch. 50K context → API calls take 5-10 min (get killed). 2K summary context → 52s Gemini, 218s GPT. Summarize the key points from source files into a compact context bundle rather than concatenating full files.

---

#### Review Mode Prompts

**Gemini — Architectural/Pattern Review:**
```bash
llmx chat -m $GEMINI_MODEL \
  -f "$REVIEW_DIR/gemini-context.md" \
  $GEMINI_MAX_TOKENS --timeout 300 \
  -o "$REVIEW_DIR/gemini-output.md" "
<system>
You are reviewing a codebase. Be concrete. No platitudes. Reference specific code, configs, and findings. It is $(date +%Y-%m-%d).
</system>

[Describe what's being reviewed]

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Assessment of Strengths and Weaknesses
What holds up and what doesn't. Reference actual code/config. Be specific about errors AND what's correct.

## 2. What Was Missed
Patterns, problems, or opportunities not identified. Cite files, line ranges, architectural gaps.

## 3. Better Approaches
For each recommendation, either: Agree (with refinements), Disagree (with alternative), or Upgrade (better version).

## 4. What I'd Prioritize Differently
Your ranked list of the 5 most impactful changes, with testable verification criteria.

## 5. Constitutional Alignment
$([ -n "$CONSTITUTION" ] && echo "Where does the reviewed work violate or neglect stated principles? Which principles are well-served?" || echo "No constitution provided — assess internal consistency only.")

## 6. Blind Spots In My Own Analysis
What am I (Gemini) likely getting wrong? Where should you distrust my assessment?
"
```

**GPT — Quantitative/Formal Analysis:**
```bash
llmx chat -m $GPT_MODEL \
  -f "$REVIEW_DIR/gpt-context.md" \
  $GPT_EFFORT $GPT_TIMEOUT \
  -o "$REVIEW_DIR/gpt-output.md" "
<system>
You are performing QUANTITATIVE and FORMAL analysis. Gemini is handling qualitative pattern review separately. Focus on what Gemini can't do well. Be precise. Show your reasoning. No hand-waving.
</system>

[Describe what's being reviewed]

RESPOND WITH EXACTLY:

## 1. Logical Inconsistencies
Formal contradictions, unstated assumptions, invalid inferences. If math is involved, verify it.

## 2. Cost-Benefit Analysis
For each proposed change: estimated effort, expected impact, risk. Rank by ROI.

## 3. Testable Predictions
Convert vague claims into falsifiable predictions with success criteria. If a claim can't be made testable, flag it.

## 4. Constitutional Alignment (Quantified)
$([ -n "$CONSTITUTION" ] && echo "For each constitutional principle: coverage score (0-100%), specific gaps, suggested fixes." || echo "No constitution provided — assess internal logical consistency.")

## 5. My Top 5 Recommendations (different from the originals)
Ranked by measurable impact. Each must have: (a) what, (b) why with quantitative justification, (c) how to verify with specific metrics.

## 6. Where I'm Likely Wrong
What am I (GPT-5.4) probably getting wrong? Known biases to flag: overconfidence in fabricated specifics, overcautious scope-limiting, production-grade recommendations for personal projects.
"
```

---

**Optional — Flash pattern extraction pass:**
For large codebases, a cheap Flash pass before the main reviews can surface mechanical issues:
```bash
llmx chat -m gemini-3-flash-preview \
  -f /path/to/large-context.md \
  --timeout 120 \
  -o "$REVIEW_DIR/flash-audit.md" "
<system>
Mechanical audit only. No analysis, no recommendations.
</system>

Find:
- Duplicated content across files
- Inconsistent naming (model names, paths, conventions)
- Stale references (wrong versions, deprecated APIs)
- Missing cross-references between related documents
Output as a flat list.
"
```

### Step 4: Fact-Check Outputs (MANDATORY)

**Both models hallucinate. Never adopt a recommendation without verification.**

For each claim in each review:

1. **Code claims** — Read the actual file and verify. Models frequently cite wrong line numbers, invent function names, or misread logic.
2. **Research claims** — Check if the cited paper/finding actually says what the model claims. Models often distort findings to support their argument.
3. **"Missing feature" claims** — Grep the codebase. The feature may already exist. Models frequently recommend adding things that are already implemented.

Use Flash for rapid fact-checking of specific claims:
```bash
llmx chat -m gemini-3-flash-preview "Claim: [model's claim]. Actual code: [paste relevant code]. Is this claim accurate? Be precise."
```

### Step 5: Extract & Enumerate (Anti-Loss Protocol)

**Why this step exists:** Single-pass synthesis is lossy. The agent biases toward recent, vivid, or structurally convenient ideas and silently drops others. In observed sessions, users had to ask "did you include everything?" 3+ times — each time recovering omissions. The EVE framework (Chen & Fleming, arXiv:2602.06103) shows that separating extraction from synthesis improves recall +24% and precision +29%.

**Do this BEFORE writing any synthesis prose.**

**Use fast models for extraction.** This step is mechanical — a fast model (Flash or GPT-5.3 Instant) extracts just as well as the deep reviewers at 10x lower cost. Dispatch extraction to a fast model from a *different family* than the reviewer to avoid self-preference in what gets extracted:

```bash
# Extract Gemini's review with GPT-5.3 Instant (cross-family extraction)
llmx chat -m gpt-5.3-chat-latest --stream --timeout 120 \
  -f "$REVIEW_DIR/gemini-output.md" \
  -o "$REVIEW_DIR/gemini-extraction.md" "
<system>
Extract every discrete recommendation, finding, or claim as a numbered list. One item per line. Do not evaluate or filter — extract mechanically.
</system>

Extract all discrete ideas from this review."

# Extract GPT's review with Flash (cross-family extraction)
llmx chat -m gemini-3-flash-preview --timeout 120 \
  -f "$REVIEW_DIR/gpt-output.md" \
  -o "$REVIEW_DIR/gpt-extraction.md" "
<system>
Extract every discrete recommendation, finding, or claim as a numbered list. One item per line. Do not evaluate or filter — extract mechanically.
</system>

Extract all discrete ideas from this review."
```

**Why cross-family extraction:** Self-preference bias (Wataoka NeurIPS 2024) means a model's own family preferentially surfaces claims written in its style. Using GPT-fast to extract Gemini's claims, and Gemini-fast to extract GPT's claims, avoids this.

**5a. Extract claims per source.** For each model output, enumerate every discrete idea/recommendation/finding as a numbered item. One idea per line. Keep it mechanical — don't evaluate yet.

```markdown
## Extraction: gemini-output.md
G1. [Prediction ledger needed — no structured tracking exists]
G2. [Signal scanner has silent except blocks — masks failures]
G3. [DuckDB FTS preserves provenance better than vector DB]
...

## Extraction: gpt-output.md
P1. [Universe survivorship bias — S:5, D:5]
P2. [first_seen_date needed on all records for PIT safety]
P3. [FDR control mandatory — 5000-50000 implicit hypotheses/month]
...
```

**5b. Disposition table.** Every extracted item gets a verdict. No item left undispositioned.

```markdown
## Disposition Table
| ID  | Claim (short) | Disposition | Reason |
|-----|--------------|-------------|--------|
| G1  | Prediction ledger | INCLUDE — Tier 1 | Both models, verified gap |
| G2  | Silent except blocks | INCLUDE — Tier 6 | Verified in signal_scanner.py |
| G3  | DuckDB > vector DB | INCLUDE — YAGNI | Constitutional alignment |
| P1  | Universe survivorship | INCLUDE — Tier 4 | Verified, no PIT table exists |
| P2  | first_seen_date | INCLUDE — Tier 1 | Verified, downloads lack it |
| P3  | FDR control | DEFER | Needs experiment registry first |
| P7  | Kubernetes deployment | REJECT | Scale mismatch (personal project) |
| ... | ... | ... | ... |
```

Valid dispositions: `INCLUDE`, `DEFER (reason)`, `REJECT (reason)`, `MERGE WITH [ID]` (dedup).

**5c. Coverage check.** Before proceeding to synthesis:
- Count: total extracted, included, deferred, rejected, merged
- If any ID has no disposition → stop and fix
- Save extraction + disposition table to `$REVIEW_DIR/extraction.md`

This file is the checklist. If the user asks "did you include everything?" — point them here, not the prose.

### Step 6: Synthesize

Build the synthesis from the disposition table. Every INCLUDE item must appear. Reference IDs so coverage is auditable.

**Trust ranking for included items:**

| Trust Level | Criterion | Action |
|------------|-----------|--------|
| **Very high** | Both models agree + verified against code | Adopt |
| **High** | One model found + verified against code | Adopt |
| **Medium** | Both models agree but unverified | Verify before adopting |
| **Low** | Single model, unverified | Flag for investigation |
| **Reject** | Model recommends itself, or claim contradicts verified code | Discard |

**Output format:**

```markdown
## Cross-Model Review: [topic]
**Mode:** Review
**GPT:** GPT-5.4 (reasoning-effort high)
**Date:** YYYY-MM-DD
**Models:** [actual models used]
**Constitutional anchoring:** Yes/No (CLAUDE.md Constitution section or standalone, GOALS.md)
**Extraction:** N items extracted, M included, D deferred, R rejected

### Verified Findings (adopt)
| ID | Finding | Source | Verified How |
|----|---------|--------|-------------|
| G1, P4 | Prediction ledger needed | Gemini + GPT | No prediction table in DuckDB |

### Deferred (with reason)
| ID | Finding | Why Deferred |
|----|---------|-------------|

### Rejected (with reason)
| ID | Finding | Why Rejected |
|----|---------|-------------|

### Where I Was Wrong
| My Original Claim | Reality | Who Caught It |
|-------------------|---------|--------------|

### Gemini Errors (distrust)
| Claim | Why Wrong |

### GPT Errors (distrust)
| Claim | Why Wrong |

### Revised Priority List
1. ...
```

**Save both files:**
```bash
# Extraction + disposition (the checklist)
# Synthesis (the prose)
# Both persist in $REVIEW_DIR
```

### Step 7: Close the Loop (Mandatory if INCLUDE items exist)

**The synthesis is not the deliverable — the updated artifact is.** If you stop after writing the synthesis, the user has to tell you to apply the findings. That's supervision waste.

**Case A: Review target is an existing plan or implementation document.**
Apply verified INCLUDE items directly to the target:
- Bug fixes → patch the code/schema/config in the plan
- Architectural additions → add new sections
- Success criteria fixes → update the criteria
- Tag each change with the finding ID (e.g., "R2/P4")
- Don't ask permission — the INCLUDE disposition is the decision

**Case B: Review target is a decision, code, or architecture (no existing plan).**
Offer a plan-mode handoff:

> "Synthesis identified N actionable items. This review used ~X% context. Want me to write an implementation plan and hand off to a fresh context?"

If yes: call `EnterPlanMode`, write the implementation plan referencing INCLUDE items by ID (link to `$REVIEW_DIR/extraction.md`), then `ExitPlanMode`. The clear+execute dialog reclaims context — the plan file is the information bridge.

If no: end here. The synthesis and extraction persist in `$REVIEW_DIR/`.

**Case C: All findings are DEFER/REJECT or exploratory.**
Don't offer anything. The synthesis is the deliverable.

### Multi-Round Reviews

When running multiple dispatch rounds (e.g., Round 1 architecture + Round 2 red team):

1. **Extract per round, not per synthesis.** Each round's outputs get their own extraction pass (G1-Gn for round 1 Gemini, G2.1-G2.n for round 2 Gemini, etc.).
2. **Merge disposition tables across rounds** before writing the final synthesis. Dedup with `MERGE WITH [ID]`.
3. **Never synthesize a synthesis.** The final prose is written once from the merged disposition table. Don't compress round 1's synthesis — compress round 1's raw extraction alongside round 2's raw extraction.
4. **Total coverage count** in the final output: "R1: 47 items extracted, R2: 38 items extracted. Final: 85 total, 62 included, 14 deferred, 9 rejected."

This prevents the sawtooth pattern (compress → lose stuff → user catches → patch → compress again → lose different stuff).

## Known Model Biases

Flag these when they appear in outputs. Don't adopt recommendations that match a model's known bias without independent verification.

### Cross-Model Structural Biases

| Bias | What It Means | Measured Effect | Countermeasure |
|------|--------------|-----------------|----------------|
| **Correlated errors** | Models from the same provider/architecture share blindspots | ~60% shared wrong answers when both err (vs 33% random) — Kim et al. ICML 2025, pre-reasoning models | Never use same-family as both reviewer and synthesizer |
| **Self-preference** | Models prefer text that "reads like" their own distribution (perplexity-driven) | GPT-4: 74.9% demographic parity bias — Wataoka NeurIPS 2024 | Use a different-family model for synthesis; weight cross-family disagreements heavily |
| **Judge inflation** | LLM judges inflate accuracy of same-provider models | Systematic on Helm leaderboard — Kim et al. ICML 2025 | Cross-family review only. This skill already does this. |
| **Debate = martingale** | Sequential model discussion doesn't improve expected correctness | Formal proof + 7 benchmarks — Choi et al. 2025 | Vote/extract independently, don't let models respond to each other's reviews |

**Reasoning model caveat:** The above numbers come from pre-reasoning (2024-early 2025) models. Reasoning models (GPT-5.4, Gemini 3.1 Pro, Opus 4.6) show lower sycophancy (SYCON Bench) and bypass positional bias (thinking phase reasons about information location). Correlation rates for reasoning models are unmeasured — likely lower but not zero. Treat the numbers as upper bounds.

### Per-Model Biases

| Model | Bias | How It Manifests | Countermeasure |
|-------|------|-----------------|----------------|
| **Gemini 3.1 Pro** | Production-pattern bias | Recommends enterprise patterns (DuckDB migrations, service meshes) for personal projects | Check if recommendation matches project scale |
| **Gemini 3.1 Pro** | Self-recommendation | Suggests using Gemini for tasks, recommends Google services | Flag any self-serving suggestions |
| **Gemini 3.1 Pro** | Instruction dropping | Ignores structured output format in long contexts | Re-prompt if output sections are missing |
| **GPT-5.4** | Confident fabrication | Invents specific numbers, file paths, function names with high confidence | Verify every specific claim against actual code |
| **GPT-5.4** | Overcautious scope | Adds caveats that dilute actionable findings, hedges everything | Push for concrete recommendations |
| **GPT-5.4** | Production-grade creep | Recommends auth, monitoring, CI/CD for hobby projects | Match recommendations to actual project scale |
| **Flash / GPT-5.3 Instant** | Shallow analysis | Good for extraction and pattern matching, bad for architectural judgment | Use ONLY for Step 5 extraction, mechanical audits, and fact-checking |
| **Flash / GPT-5.3 Instant** | Recency bias | Defaults to latest patterns even when older ones are better | Don't use for "which approach" decisions |

## Model-Specific Prompting Notes

**Gemini 3.1 Pro (always used for review):**
- Excels at cross-referencing across large context (finds contradictions between file A and file B)
- **NEVER use `--no-stream` with Gemini 3.1 Pro** — long generations hang indefinitely. Always use default streaming.
- Temperature is locked at 1.0 server-side for thinking models
- Will recommend itself for tasks — always flag self-serving suggestions
- Tends to over-recommend architectural changes (DuckDB migrations, etc.)
- llmx default timeout is now 300s; use `--timeout 300` explicitly in dispatch commands

**GPT-5.4 (`gpt-5.4`) — review GPT:**
- `--reasoning-effort high` is essential for review mode (burns thinking time for deep fault-finding)
- `--reasoning-effort medium` for extraction tasks only
- MUST use `--stream` with reasoning-effort high — non-streaming timeouts are common
- Temperature locked at 1.0. `--timeout 600` minimum for high reasoning effort
- Tends toward overcautious "production-grade" recommendations for personal projects
- **Differentiated role:** Quantitative/formal analysis — logical inconsistencies, math errors, cost-benefit, testable predictions.

**Gemini Flash (`gemini-3-flash-preview`) — Fact-checking only:**
- Use for rapid verification of specific claims against code snippets
- Fast and cheap — good for 10-20 quick checks and mechanical audits
- Don't use for architectural judgment, only factual verification and pattern matching
- Note: `gemini-flash-3` and `gemini-3-flash` are both 404s — always use `gemini-3-flash-preview`

## Anti-Patterns

- **Synthesizing without extracting first.** The #1 information loss pattern. Never go from raw model outputs directly to prose synthesis. Always run the extraction + disposition step (Step 5) first. If you skip it, the user will ask "did you include everything?" and you will have lost items.
- **Synthesizing a synthesis.** Each compression pass drops ideas. If you have Round 1 synthesis + Round 2 outputs, don't compress the Round 1 synthesis — go back to Round 1's raw extraction and merge with Round 2's extraction. One synthesis pass from merged extractions, not cascaded compressions.
- **Adopting recommendations without code verification.** Both models hallucinated "missing" features that already existed in the codebase.
- **Treating model agreement as proof.** When both models err, they agree on the *same* wrong answer ~60% of the time (Kim et al. ICML 2025). Agreement is evidence, not proof — verify against source code.
- **Letting models respond to each other's reviews (debate).** Debate is a martingale — no expected correctness improvement (Choi et al. 2025, formal proof). Independent parallel reviews + voting outperforms sequential discussion. Never implement a "models critique each other's reviews" workflow.
- **Using same-family reviewers.** Claude reviewing Claude = same distribution. Same-model correction: 59.1% accuracy. Cross-family: 90.4% (FINCH-ZK). This skill exists because cross-family is the only form that provides real adversarial pressure.
- **Skipping the self-doubt section.** The "Where I'm Likely Wrong" section is the most valuable part of each review. Models that can't identify their own weaknesses are less trustworthy.
- **Same prompt to both models.** Gemini and GPT have different strengths. Sending the same qualitative prompt to both wastes GPT's formal reasoning capability. Gemini = patterns, GPT = quantitative/formal.
- **Writing to /tmp.** Review outputs are valuable artifacts. Always persist to `.model-review/YYYY-MM-DD-topic/`.
- **Using bare date directories.** `.model-review/2026-03-01/` will collide when two reviews run the same day. Always append a topic slug.
- **Skipping constitutional check.** Reviews without project-specific anchoring drift into generic advice. Always check for constitution (in CLAUDE.md or standalone) and GOALS.md first.
- **Mixing review and brainstorming.** This skill is convergent only. For divergent ideation, use `/brainstorm`.

$ARGUMENTS
