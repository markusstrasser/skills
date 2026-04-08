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

## 1. Assemble Context

Write review material to a single context file. **Do NOT manually create `.model-review/` directories, write constitutional preambles, or assemble per-model files.** The script handles all of this.

**Pre-flight — constitutional check:** Before building context, check for constitution (standalone CONSTITUTION.md or `## Constitution` section in CLAUDE.md) and GOALS.md. If found, the script injects as preamble. If neither exists, warn user: *"No constitution or GOALS.md found. Reviews will lack project-specific anchoring."* Proceed anyway.

**Pre-flight — scope declaration (mandatory):** Include a `## Scope` block near the top:
- **Target users:** personal / team / multi-tenant / public
- **Scale:** current entity counts AND designed-for scale (e.g., "currently 40 compounds, designed for thousands of subjects")
- **Rate of change:** how often does new data arrive?

This prevents the #1 review failure mode: models optimizing for the wrong scale. Evidence: selve UMLS review (2026-04-06) — GPT scored a plan 27/100 as "over-engineered for 105 personal entities" when the actual scope was multi-user scalable. Required full re-dispatch after scope correction.

**Token budgets:** Gemini Pro sweet spot 80-150K (max ~800K). GPT-5.4 sweet spot 40-100K (max ~400K). Compact aggressively — 50K context = 5-10 min; 2K summary = ~1 min. Summarize rather than concatenate full files.

See `references/context-assembly.md` for detailed context gathering (narrow, broad, auto-assembled).

### Context Anti-Patterns (Shared Context = Shared Wrong Answers)

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
| **Missing scope declaration** — not stating target users and designed-for scale | Models assume personal/small when reviewing shared infra, or assume production when reviewing prototypes | Always include scope block (see above) |

## 2. Dispatch

**Always use the script.** It handles: output directory creation, constitutional preamble injection, context splitting, parallel llmx dispatch, extraction, and disposition generation.

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract \
  "$ARGUMENTS"
```

Set `timeout: 660000` on the Bash tool call. Add `--extract` to all standard/deep reviews.

For per-axis question customization, write a JSON file and pass `--questions`:
```bash
echo '{"arch": "Focus on cross-cutting concerns", "formal": "Verify the cost model math"}' > questions.json
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md --topic "$TOPIC" --project "$(pwd)" --extract \
  --questions questions.json
```
Axes not in the JSON fall back to the positional question.

### Depth Presets

Classify by blast radius, not file count:

| Preset | Axes | When |
|--------|------|------|
| `standard` (default) | arch + formal | Most new features |
| `--axes simple` | combined Gemini Pro | Config tweaks, refreshes |
| `--axes deep` | arch + formal + domain + mechanical | Structural changes, domain-dense |
| `--axes full` | all 5 | Shared infra, clinical, high-stakes |

| Axis | What it checks |
|------|---------------|
| `arch` | Patterns, architecture, cross-reference (Gemini Pro) |
| `formal` | Math, logic, cost-benefit, testable predictions (GPT-5.4 high reasoning) |
| `domain` | Domain fact correctness. Skip for pure code reviews. (Gemini Pro) |
| `mechanical` | Stale refs, wrong paths, naming. Include grep results — Flash hallucinates about fixed state (~13%). |
| `alternatives` | 3-5 genuinely different approaches (Kimi K2.5) |

**Genomics classification review** (monthly or after >10 commits to LR-engine/scoring): Use `--axes formal,domain`. GPT-5.4 found 11 conceptual/mathematical bugs for $6.54 — the only detector for incoherent Bayes, wrong concordance, excluded FDR families, surrogate endpoint fallacy.

Use `--context-files file1.py file2.py:100-150` to skip manual context assembly.

**NEVER downgrade models on failure.** If Pro or GPT-5.4 fails, the problem is dispatch (timeout, redirect, context size, rate limit) — not the model. Diagnose via stderr/exit code/`llmx --debug`. See `references/dispatch.md` for manual dispatch and troubleshooting.

## 3. Fact-Check (Mandatory)

**Both models hallucinate. Never adopt without verification.**

1. **Code claims** — Read the actual file. Models frequently cite wrong line numbers, invent function names.
2. **Research claims** — Check if the cited finding actually says what the model claims.
3. **"Missing feature" claims** — Grep the codebase. The feature may already exist.

Use a **different model family** than the claim's author. Cross-family verification: +31pp accuracy vs same-family (FINCH-ZK, Amazon 2025). For code claims, always verify by reading the actual file first.

## 4. Extract & Disposition

**STOP — did the script run with `--extract`?** If yes, read `disposition.md` and skip to Step 5. If not, see `references/extraction.md` for manual extraction workflow.

The core rule: **never go from raw model outputs directly to synthesis.** Extract mechanically first (cross-family fast models), then disposition every item, then synthesize. Extraction before synthesis: +24% recall, +29% precision (EVE, arXiv:2602.06103).

## 5. Synthesize

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

### Auto-Verify File-Specific Findings

If synthesis has INCLUDE items with file:line citations, invoke `/verify-findings` on the synthesis before Step 6. Only implement CONFIRMED or CORRECTED findings. Drop HALLUCINATED. Skip if all findings are architectural or fewer than 3 code citations.

### Over-Adoption Check

The disposition file includes an **Agent Response** template at the bottom (added by `--extract`). Fill it in before implementing any findings — the two questions are:

1. **Where do you disagree with the disposition?** "Nowhere" is valid. Don't invent disagreements.
2. **Context you had that the models didn't?** If the context file was comprehensive, say so.

Write your answers directly in `disposition.md`. Valid outcomes: "No changes" (proceed) or "Revising N items" (state which, why, update synthesis).

**Why this exists:** Models produce rigorous-looking analysis that can override your judgment through sheer detail. The template is in the artifact so it's visible every time you read the disposition — architecture over instructions.

## 6. Close the Loop (Mandatory if INCLUDE items exist)

**The synthesis is not the deliverable — the updated artifact is.**

- **Case A (existing plan/doc):** Apply verified INCLUDEs directly. Tag changes with finding IDs. Don't ask permission.
- **Case B (decision/code, no plan):** Offer plan-mode handoff if context is depleted.
- **Case C (all DEFER/REJECT):** Synthesis is the deliverable.

## Artifact Handoff

Write summary JSON to `~/.claude/artifacts/$(basename $PWD)/model-review-$(date +%Y-%m-%d).json` with: skill, project, date, topic, include/defer/reject counts, key_findings[]. Used by project-upgrade as a cache gate.

## References

- `references/context-assembly.md` — detailed context gathering patterns
- `references/dispatch.md` — full dispatch mechanics, manual dispatch, timeouts, model flags
- `references/extraction.md` — manual extraction workflow
- `references/prompts.md` — full prompt templates per model
- `references/biases-and-antipatterns.md` — known model biases, per-model failure modes, common mistakes

$ARGUMENTS

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] llmx output flag — never use shell redirects (> file) with llmx; use --output/-o flag instead. Shell redirects buffer until process exit, producing 0-byte files. Fixed in llmx v0.5.0 (2026-03-06).**
