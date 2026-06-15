<!-- Lens: large repo audit → plan critique. Evidence: genomics lingering-bugs session 2026-06-15. -->

# Repo Audit Plan Review — Lean Cross-Model Critique

Use when a session has already produced a **repo-grounded audit** (multi-lane inventory,
backlog, guard matrix) and needs **architecture/sequencing critique** — not when starting
from a plan packet alone.

**Trigger:** `/critique audit-plan [topic]` OR auto-route when context includes an audit
backlog (≥15 items) + a remediation plan.

**Do NOT use for:** diff review (`/code-review`), single-file bugs, or plans with no
repo inventory pass first.

**Core invariant:** No packet-only critic may judge a repo-scale plan whose premises have
not been falsified against the repo. Parallel readonly lanes on **first audit pass** are
mandatory — orchestrator context omits module clusters (2026-06-15 genomics). Skip lanes
only when a **fresh lane manifest** from the same session exists (stable `lane_id` + item
count hash in the combined packet).

---

## Why this exists

**Packet-only 4-axis review on audit plans is expensive and shallow.**

Measured 2026-06-15 (genomics lingering-bugs): 8 parallel repo lanes + Composer verify found
load-bearing seams (`execution_plan` ≠ `freshness_verdict`, wrapper finalize). Full
Gemini+GPT `model-review.py` returned 76 findings with high speculation density. Claude Opus
(llmx sub) + Codex CLI (llmx sub) converged on sequencing with sharper disagreements.

Rule: **lanes supply facts; verify supplies truth; critics supply architecture.**

**VOI boundary:** VOI scout (§1.5 in `SKILL.md`) runs on a **named fork** before expensive
adjudication. Lanes run **before critics** to inventory unknowns. VOI does not replace lanes
on first whole-repo audit — it decides whether a specific fork is worth probing, not whether
the repo was read.

---

## Pipeline (6 steps)

```mermaid
flowchart LR
  PF[Preflight] --> L[Parallel repo lanes]
  L --> CP[Completeness critic]
  CP --> M[Mechanical merge]
  M --> V[Verify decision claims]
  V --> C[2 orthogonal critics]
  C --> S[Synthesis in docs/audit]
  S --> H[Human sequencing call]
```

### Step 0 — Preflight (mandatory)

Before dispatching lanes:

- `git log --oneline -20 -- <decision-relevant paths>` — stale audit docs?
- Topic grep for parallel session work (same sweeps, same kernel)
- Worktree / `origin/main` staleness if subagents branch from remote
- **llmx billing smoke** (hard gate before background critics):

```bash
llmx chat --dry-run --subscription -m claude-opus-4-8 -e low \
  -o /tmp/llmx-claude-smoke.md "Reply exactly OK."
# exit 6 = billing dead — do not dispatch 8 lanes + 2 critics
```

Dispatch contract in every lane prompt: **current checkout, read-only, no commits, file-first output**.

### Step 1 — Parallel repo lanes (mandatory on first pass)

Launch **6–8** readonly subagents, one concern each. Use repo-specific lane registry when
needed (genomics: orchestrator, guards, runtime/Modal, silent-zero/payload, genotype, bridge).

Each lane writes **file-first** to a unique path:

`docs/audit/.scratch/<session-id>-<lane_id>.md` (or `.model-review/lanes/<session-id>-<lane_id>.md`)

**Lane output schema** (required fields per item):

| Field | Notes |
|-------|--------|
| `lane_id` | Stable id, e.g. `orchestrator` |
| `item_id` | `{lane_id}-{seq}` |
| `bug_class` | Dedupe key across lanes |
| `paths` | File paths |
| `evidence_quote` | ≤1 line from source |
| `guard_status` | caught / gap / unknown |
| `severity` | CRITICAL / HIGH / … |
| `status` | open / closed / uncertain |
| `fix_class` | unified-kernel / lint / doc / … |

**Soft target:** ≤25 open items per lane. If exceeded, include `dropped=N` with ids of
truncated items — never silent cap.

### Step 1.5 — Lane-partition completeness critic (mandatory when lanes run)

One cheap readonly agent after lanes return:

> "Which directories/modules in scope map to **no lane**? List gaps. Return lane-backed paths only."

Null/dead lane (dispatched but empty/error) **fails loud** — do not proceed to critics.

### Step 2 — Mechanical merge (orchestrator)

**No judgment merge:** union items by `(bug_class, primary_path)` key; preserve all
`lane_id` provenance. Assert `lanes_returned == lanes_dispatched`. Build combined packet
`<repo>/.model-review/<topic>-critique-context.md`:

```markdown
## Scope
- Project identity, N, rate of change, mission gate (from docs/GOALS.md if present)

## Lane manifest
- lane_id, item_count, dropped=N, output path

## Audit inventory summary
- Top backlog by severity (from merge)

## Proposed plan excerpt
- Sequencing, phases, DELETE list

## Task for critics
Adversarial only. UNIFIED root-cause fixes — not per-symptom lints.
Label every claim: lane-backed | verify-backed | speculative.
Ask for DELETE from plan and disagreements with other reviewers.
```

Append full plan markdown. **One combined file** — pre-concatenate; do not rely on multi-file
`-f` for Gemini. **Soft target ≤80KB** — split by plan phase if larger; note `dropped_sections`.

### Step 3 — Verify pass (mandatory; decision-dependent, not top-N)

Verify every claim that changes **sequencing, deletion, unification, or blast radius** —
not "top 10 by severity." At least one repo-access pass:

```bash
agent -p --mode ask --trust --model composer-2.5 \
  --workspace "$REPO" --output-format text \
  -f "$REPO/.model-review/<topic>-critique-combined.md" \
  "Fact-check decision-dependent claims with file:line. Mark feasible one-session vs multi-session."
```

Or orchestrator Read/Grep on load-bearing claims. **Critics receive the verified subset**
plus full inventory summary — not unverified bulk.

Composer verify here is **verify bucket only** — not a third sequencing critic unless
Claude/Codex disagree.

### Step 4 — Lean critics (2 max, orthogonal, background)

**Default pair** (audit-plan exception — not a global replacement for `model-review.py --axes standard`):

| Critic | Lens | Dispatch |
|--------|------|----------|
| Claude Opus | Sequencing / unification | `llmx chat --subscription -m claude-opus-4-8` |
| Codex | Premise-soundness / false-positive risk | `llmx chat -p codex-cli -m gpt-5.5` |

```bash
cd "$REPO"
cat .model-review/<topic>-critique-context.md path/to/plan.md \
  > .model-review/<topic>-critique-combined.md

llmx chat --subscription -m claude-opus-4-8 \
  -f .model-review/<topic>-critique-combined.md \
  -e high \
  -o .model-review/critique-claude-opus-subscription.md \
  "Adversarial. UNIFIED root-cause fixes. Label claims lane-backed|verify-backed|speculative. Return: Findings | Top 3 | DELETE | Disagreements"

llmx chat -p codex-cli -m gpt-5.5 \
  -f .model-review/<topic>-critique-combined.md \
  -e high \
  -o .model-review/critique-codex-cli.md \
  "Same contract but focus on false premises, noise, and claims that should be deleted."
```

**Run both in background** (`run_in_background`). **No skill-prescribed `--timeout`.** The
orchestrator inspects the running shell task / terminal / agent output and kills manually if
stuck. Read `-o` when the task completes (llmx writes on success). Proceed with whichever
critic finished if one is still running.

**Skip by default:** full `model-review.py --axes standard` on whole-repo audit plans —
escalate to one subpart only after lean pass converges on problem statement.

### Step 5 — Synthesize and commit durable artifact

Merge into **4 buckets:**

| Bucket | Action |
|--------|--------|
| **Convergent** (2+ critics + verify) | Adopt in plan sequencing |
| **Divergent** (critics disagree) | Human call — do not blend |
| **Verify-only** | Code-grounded; may override critics |
| **Single-source speculative** | Discard unless verify confirms |

**Deliverable:** `docs/audit/YYYY-MM-DD-<topic>-audit-plan.md` in the **repo** (committed).
Include: convergence table, lane manifest hash, minimal evidence excerpts. Raw critic outputs
stay in gitignored `.model-review/`.

---

## Oracle-anchored gate (load-bearing)

When the plan proposes **unifying classifiers/kernels** (freshness, completion, dispatch):

1. **Freeze human-validated truth fixtures FIRST** (golden set, append-only).
2. Parity tests assert against **oracle**, not path-vs-path agreement.
3. **Never** replace the oracle with machine-derived projection from the kernel under test.

Evidence: 41% concordant kernel + "delete independent witness" = silent-proxy-as-truth trap
(Claude Opus critique, genomics 2026-06-15).

---

## Multi-session coordination

Before dispatching Modal compute from an audit plan:

- Check parallel sessions for **same file sweeps** (e.g. 13× `modal_*.py` run-secret edits).
- **Compute may run in parallel**; **trusted SUCCESS claims** wait until kernel + oracle land.
- Document conflicts in plan synthesis (who owns sweep vs kernel work).

---

## When to escalate to full `model-review.py`

- Clinical/shared-infra ADR with formal invariants → add `--axes standard,formal` on **one subpart**
- Lean critics agree on problem but propose incompatible replacements → `--axes standard` on that subpart only
- Hallucination rate on verify pass >40% → discard critic, re-run with tighter packet

---

## Anti-patterns

| Anti-pattern | Fix |
|--------------|-----|
| Critique before repo lanes on first pass | Critics invent backlog; run lanes first |
| 4-axis on 80KB unverified mega-packet | Lean 2-critic + verify after lanes |
| Orchestrator "top 10" merge judgment | Mechanical dedupe + decision-dependent verify |
| Trust path-vs-path parity | Oracle-anchored tests |
| Only `.cursor/plans/` + gitignored `.model-review/` | Commit `docs/audit/*-audit-plan.md` |
| Foreground long critic dispatches | Background; orchestrator inspects task, kills manually |
| `claude -p` with `ANTHROPIC_API_KEY` set | `llmx chat --subscription` strips key |
| Optional scratch files for lane output | File-first mandatory; unique session-lane paths |
| Same-axis redundant critics | Orthogonal lenses: sequencing vs premise-soundness |
