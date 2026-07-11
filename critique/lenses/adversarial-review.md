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
