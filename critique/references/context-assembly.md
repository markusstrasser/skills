<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Context Assembly

Detailed instructions for assembling review context. SKILL.md covers the anti-patterns table (the judgment calls); this file covers the mechanical "how to gather context" instructions.

## Narrow Reviews (Manual Assembly)

The review target (plan, design doc, code) plus enough surrounding context for models to understand the decision space. Use Read/Grep to gather, then Write to a single `context.md`.

**Context sources to check** (not all required -- pick what's relevant to *this* review):

| Source | When to include | How to get it |
|--------|----------------|---------------|
| The artifact itself | Always | Read the file |
| Code it references | When reviewing a plan or design that names specific files | Read the referenced files, or summarize signatures |
| Tests for that code | When reviewing implementation correctness | Grep for test files, include relevant cases |
| Recent git history | When reviewing a change or refactor | `git log --oneline -10 -- <path>` or `git diff` |
| Related CLAUDE.md sections | When the review involves conventions or architecture | Read the relevant section, not the whole file |
| Project operational context | When the review touches code with deliberate constraints | `.claude/rules/vetoed-decisions.md`, key rules files, data-sources docs. Models that don't know about vetoes and deliberate exclusions will propose re-enabling them. Include as context, not binding constraints — the model may correctly argue a prior decision is outdated. |
| Upstream constraints | When the review depends on external APIs, schemas, or specs | Include the relevant spec snippet |

**What NOT to include:** unrelated code, full CLAUDE.md dumps, entire test suites, historical context that doesn't inform the decision. Noise dilutes the review -- models spend tokens on irrelevant material instead of finding real problems.

## Broad Reviews (Codebase/Architecture)

For whole-repo or multi-file architectural reviews, you need a compressed representation of the codebase.

**Options (check in order):**
1. **`.claude/rules/codebase-map.md`** -- already auto-loaded in your context if it exists. File map with descriptions + import edges. Available in: meta, intel, genomics, research-mcp, selve. If present, you already have it -- just include it in the context file.
2. **`repo-summary.py --compact`** -- generate on-demand if no codebase-map exists. Good for "what does this repo do" reviews.
3. **`repo-outline.py outline`** -- function/class signatures. Good for API surface or coupling reviews.
4. **`.context/` views** -- if the project has them (`make -C .context all 2>/dev/null`).
5. **Manual assembly** -- Read key files (entry points, config, core logic), summarize the rest. Most flexible but slowest.

For broad reviews, always include: entry points, the files under question, and the project's stated architecture (CLAUDE.md relevant sections). Omit: tests, generated files, vendored deps.

## Shared Packet Path

For repo automation, prefer the shared packet builders over hand-assembling markdown:

- `review/scripts/build_plan_close_context.py` now emits both the markdown packet and a sidecar manifest
- `review/scripts/model-review.py` builds one shared context packet and reuses it across axes
- overview generation uses the same packet spine for prompt payload construction

The shared packet layer generalizes mechanics only:

- block rendering
- provenance labeling
- hashing / manifests
- truncation markers

It does **not** generalize task-specific file selection. Builders still decide what belongs in context.

## Governance Relevance (Agent Curates — Do NOT Dump the Charter)

The dispatch script does **not** auto-inject the goals/governance charter (it biases
reviewers toward compliance over independent judgment — 2026-06-15 biased-critique
incident). Blind-adversarial is the default. `--charter-anchor` is the explicit opt-in
that injects the full `GOALS.md` verbatim, for a *compliance* review only.

For everything else, the orchestrating agent curates: select the few **current +
relevant** principles from `GOALS.md`/`CLAUDE.md`/constitution that bear on THIS review
and add them to the `--context` packet as a short, targeted block — not the whole charter.

- **Relevant + current only.** Re-read the source and confirm each principle still
  exists before quoting it (governance drifts; a stale quote misleads the reviewer).
- **Frame for judgment, not obedience.** Header it *"Relevant project constraints —
  apply your own judgment; flag the work if it violates these, AND flag a constraint if
  it looks wrong here."* Never *"review against these, not your priors."*
- **Default to none.** No on-point principle → inject nothing.

See SKILL.md § *Governance relevance — curate, do NOT dump the charter* for examples.
