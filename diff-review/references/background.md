# diff-review background and evidence

<!-- moved-from diff-review/SKILL.md L22-28 2026-10-26 -->
## Naming and rotation history (moved verbatim from SKILL.md)

> Moved verbatim from diff-review/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

**Not Anthropic's built-in `/code-review`** (bundled in Claude Code; `/code-review ultra` is the
paid multi-agent cloud review). This skill was named `code-review` until 2026-10-18 and shadowed
the built-in. Critique/execute closeouts call this skill for the diff layer.

The 25-day project/focus rotation (`code-review-schedule.py`, `/loop /code-review`) was cut
2026-10-18 (operator: "no cronjobs"); per-project rotation runs had gone quiet while diff
closeouts ran near daily. A whole-project pass is still `"$SCOUT" <project> --focus <focus>`.

<!-- moved-from diff-review/SKILL.md L53-64 2026-10-26 -->
## Provider order (full wording) (moved verbatim from SKILL.md)

> Moved verbatim from diff-review/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

**Provider order (local-first):**
1. **`openai`** (default) — `gpt-6-astra` at low effort via codex-cli subscription ($0).
   Operator decision 2026-10-07: Astra low replaces Composer 2.5.
2. **`sol`** — `gpt-6.1-sol` at high effort, subscription. Rerun with `--provider sol` on a Codex
   plan-limit error for Astra (llmx exit 6).
3. **`google`** — Gemini via llmx (paid API path since 2026-05-31). Use when both Codex models
   are exhausted.

Composer 2.5 and the scout's `cursor` provider were retired 2026-10-07.
For an explicitly selected high-recall review or a concrete unresolved risk that needs another
model, use `--both` (google + openai; `--all-providers` is the same set). Module size alone does
not require a broader panel.

<!-- moved-from diff-review/SKILL.md L141-161 2026-10-26 -->
## Module-depth lens and metric-claim evidence (full wording) (moved verbatim from SKILL.md)

> Moved verbatim from diff-review/SKILL.md (2026-10-26, context-cost reduction; SKILL.md keeps a one-line rule for each actionable item).

## Module-depth lens (design-level findings)

Beyond line-level smells, flag shallow / over-abstracted design — vocabulary from Ousterhout/Feathers
(see `agent-infra/research/2026-06-19-mattpocock-skills-best-ideas.md`):

- **Shallow module** — an interface nearly as complex as its implementation (a thin pass-through adding
  no leverage). Fix is depth, not more wrappers. **Depth = leverage at the interface**, not a line ratio.
- **Hypothetical seam** — a port/interface with a **single** implementation is needless indirection.
  Rule: *one adapter = hypothetical seam, two = real* (= our proven-common-≥2). Flag single-adapter ports.
- **Deletion test** — if this module/abstraction were deleted, what actually breaks? If little, it isn't
  pulling weight (a dead-code / over-abstraction finding).
- **Tests past the interface** — a test that asserts internal state (must change whenever the
  implementation changes) instead of observable behavior. The interface is the test surface.

## Metric-claim diffs (agent-authored)

When a diff claims a score, speedup or pass-rate gain, flag any edit in the same diff to tests, scorers,
tolerances, thresholds, fixtures or eval data, and check that numeric checks are scale-invariant and cover
the whole output. Coding agents game graders unprompted: an absolute-tolerance check accepted a kernel
that wrote 0.3% of its output as a "283×" speedup (arXiv:2609.21058), and agents that owned their
evaluation hacked it in 30.5% of open-ended tasks (arXiv:2609.28614).
