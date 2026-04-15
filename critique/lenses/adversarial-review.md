<!-- Lens file for review skill: model mode dispatch methodology. Loaded on demand. -->

# Adversarial Review — Dispatch Methodology

## Axis Descriptions

| Axis | Model | What it checks | When to include |
|------|-------|---------------|-----------------|
| `arch` | Gemini 3.1 Pro | Patterns, architecture, cross-reference, constitutional alignment | Always (default) |
| `formal` | GPT-5.4 (high reasoning) | Math, logic, cost-benefit, testable predictions, quantified constitutional coverage | Always (default) |
| `domain` | Gemini 3.1 Pro | Domain fact correctness — citations, API endpoints, schemas, biological claims, numbers | Domain-dense plans; skip for pure code reviews |
| `mechanical` | Gemini Flash | Stale refs, wrong paths, naming inconsistencies, duplicated content | Large codebases; include grep results — Flash hallucinates about fixed state (~13%) |
| `alternatives` | Kimi K2.5 | 3-5 genuinely different approaches with different mechanisms | Architecture decisions; SEPARATE from convergent review (never mix critique + brainstorm) |

## Depth Presets

| Preset | Axes | Blast radius | Cost |
|--------|------|-------------|------|
| `standard` | arch + formal | User-facing default; most features | ~$2-4 |
| `deep` | arch + formal + domain + mechanical | User-facing; structural/domain-dense | ~$4-6 |
| `full` | all 5 | User-facing; shared infra, clinical, high-stakes | ~$6-10 |

Classify by blast radius, not file count. `standard` is the default.
The user-facing presets are `standard`, `deep`, and `full`; each includes GPT-5.4.
Gemini-only passes are internal-only and should not be documented to users as review presets.

## Per-Model Prompts

### Gemini — Architectural/Pattern Review (arch axis)

System: Concrete, no platitudes. Reference specific code/configs. Agent-built codebase (dev time = free). Budget ~2000 words, dense tables/lists.

Required sections:
1. Assessment of Strengths and Weaknesses — reference actual code
2. What Was Missed — cite files, line ranges, gaps
3. Better Approaches — Agree (refine) / Disagree (alternative) / Upgrade
4. What I'd Prioritize Differently — top 5, testable criteria
5. Constitutional Alignment — violations and well-served principles (or internal consistency if no constitution)
6. Blind Spots In My Own Analysis — where to distrust Gemini

### GPT-5.4 — Quantitative/Formal Analysis (formal axis)

System: Quantitative and formal ONLY. Other reviewers handle qualitative. Precise, show reasoning. Agent-built codebase. Budget ~2000 words, tables, source-graded claims.

Required sections:
1. Logical Inconsistencies — contradictions, assumptions, invalid inferences, math verification
2. Cost-Benefit Analysis — impact, maintenance burden, composability, risk. Filter on ongoing drag, NOT creation effort
3. Testable Predictions — falsifiable predictions with success criteria
4. Constitutional Alignment (Quantified) — per-principle coverage 0-100%, gaps, fixes
5. My Top 5 Recommendations — measurable impact, quantitative justification, verification metrics
6. Where I'm Likely Wrong — GPT-5.4 known biases: confident fabrication, overcautious scope-limiting, production-grade creep

### Gemini Pro — Domain Correctness (domain axis)

System: Domain-specific claim verification only. Per-claim verdict: CORRECT / WRONG / UNVERIFIABLE. Flag URLs, API endpoints, version numbers needing probes. Budget ~1500 words.

### Gemini Flash — Mechanical Audit (mechanical axis)

System: Mechanical audit only, no analysis. Find: stale refs, inconsistent naming, missing cross-refs, duplicates, wrong paths. Flat numbered list.

### Kimi K2.5 — Alternative Approaches (alternatives axis)

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
  "$QUESTION"
```

Set `timeout: 660000` on the Bash tool call (11 min). The script fires all queries in parallel.

### Script Flags

- `--extract` — Auto-extract claims via cross-family models, merge into `disposition.md`, and emit `coverage.json`. Add to all standard/deep/full reviews.
- `--verify` — After extraction, verify cited files/symbols exist. Implies `--extract`.
- `--questions FILE` — JSON mapping axis names to custom questions. Unmapped axes use positional question.
- `--context-files spec1 spec2` — Auto-assemble from `file.py`, `file.py:100-150`, `file.py:100` specs.
- `--axes NAME` — Preset name or comma-separated axes.

### Model Selection Contract

```
Gemini Pro:  architecture / pattern pass
GPT-5.4:     quantitative / formal pass
Flash:       fallback or extraction-only pass
Kimi K2.5:   alternatives-only pass when configured
```

The shared dispatch layer owns providers, transport, retries, and timeout
policy. This lens should describe review responsibilities, not raw model flags.

**NEVER downgrade models on failure.** Diagnose via shared dispatch metadata and
coverage artifacts instead of teaching transport-specific debugging here.

### Gemini Rate Limit Fallback

Script auto-detects Gemini Pro 503/rate-limit (exit 3 or stderr markers). On first failure, retries that axis with Flash. All subsequent Gemini Pro axes in the same dispatch also fall back to Flash (session-level). GPT axes are unaffected.

### Uncalibrated Threshold Flagging

Automatic with `--extract`: the script tags numeric thresholds (e.g., `>=20% AUPRC`) lacking cited sources with `[UNCALIBRATED]`. Common GPT failure mode: fabricating plausible thresholds. Treat as requiring your own derivation.

## Known Issues

- **Gemini Pro:** Production-pattern bias (enterprise for personal), self-recommendation (Google services), instruction dropping in long context
- **GPT-5.4:** Confident fabrication (invents numbers/paths), overcautious scope, production-grade creep
- **Flash/GPT-5.3:** Shallow analysis (extraction only), recency bias. Never use for architectural judgment.
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
- **Skipping constitutional check** — Unanchored reviews drift into generic advice.
- **Mixing review and brainstorming** — Convergent only. Use `/brainstorm` for divergent.
- **Priming tool names** — Turns critique into evaluation. Use `alternatives` axis separately.
- **Scale-ambiguous context** — Both models converge on the same wrong answer from shared misleading context.
- **"Top N" triage** — If INCLUDE, implement. DEFER needs explicit reason per item.
- **Skipping self-doubt section** — Most valuable part of each review.
