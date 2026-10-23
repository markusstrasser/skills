---
name: diff-review
description: "Use when: /diff-review, review our diff/commit range/changed files, plan/phase closeout diff layer. GPT-6 Astra (codex) scout; parent validates against code. NOT plan/findings review (/critique); NOT Anthropic's built-in /code-review."
user-invocable: true
argument-hint: '<ref range | files> [low|high] — e.g., "HEAD~3..HEAD", "abc123..def456 high"'
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Agent
effort: medium
---

# Diff Review

Run the code-review scout (local CLI — **GPT-6 Astra** via codex-cli subscription by default)
over a diff's changed files, validate findings against actual source code, implement safe fixes.

**Not Anthropic's built-in `/code-review`** (bundled in Claude Code; `/code-review ultra` is the
paid multi-agent cloud review). This skill was named `code-review` until 2026-10-18 and shadowed
the built-in. Critique/execute closeouts call this skill for the diff layer.

The 25-day project/focus rotation (`code-review-schedule.py`, `/loop /code-review`) was cut
2026-10-18 (operator: "no cronjobs"); per-project rotation runs had gone quiet while diff
closeouts ran near daily. A whole-project pass is still `"$SCOUT" <project> --focus <focus>`.

## Step 1: Determine Target

```bash
SCOUT="$HOME/Projects/agent-infra/scripts/code-review-scout.py"
```

Parse `$ARGUMENTS` as a git ref range or explicit files, plus an optional depth preset
(`low` / `high`, below). **Fail fast:** confirm each ref resolves (`git rev-parse`) and the diff
is non-empty before spawning scouts. List the changed files with `git diff --name-only <range>`.

Focuses: `refactoring`, `dead-code`, `optimization`, `patterns`, `silent-failure`, `security`.

## Step 2: Run Scout

Restrict the scout to the changed files — one `--file` call per file, or `--module` when the
changed files fill one directory. Select the depth preset below from the requested coverage and
concrete risk.

```bash
cd ~/Projects/agent-infra && uv run python3 "$SCOUT" <repo path> \
  --file <repo-relative file> --focus $FOCUS --provider openai --workers 2
```

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

**Timeout:** Set Bash timeout to 600000 (10 min) — a large diff can span many batches.

If the scout finds zero new findings, report that and stop. Don't fabricate work.

## Step 3: Read Findings

```bash
FINDINGS="$HOME/Projects/agent-infra/artifacts/code-review/$PROJECT/$(date +%Y-%m-%d).jsonl"
```

Read the JSONL file. Count findings by severity:

```bash
cat "$FINDINGS" | uv run python3 -c "
import json, sys
from collections import Counter
lines = [json.loads(l) for l in sys.stdin if l.strip()]
today = [l for l in lines if l.get('focus') == '$FOCUS']
by_sev = Counter(l['severity'] for l in today)
print(f'Today: {len(today)} findings (HIGH: {by_sev.get(\"HIGH\",0)}, MEDIUM: {by_sev.get(\"MEDIUM\",0)}, LOW: {by_sev.get(\"LOW\",0)})')
for l in sorted(today, key=lambda x: ('HIGH','MEDIUM','LOW').index(x['severity']))[:15]:
    print(f\"  {l['severity']:6} {l['file']}:{l['line']} {l['description'][:100]}\")
"
```

If no HIGH findings, scan MEDIUMs for the high-true-positive patterns (unchecked returncode,
divergent copies, code duplication) — these are often misclassified. Don't validate LOWs.

## Step 4: Validate ALL HIGH Findings

**This is the critical step. Models hallucinate code issues.**

Validate **every** HIGH finding, not a sample. Read the actual code for each one.

**Do NOT categorize-then-skip.** Read the code, judge individually.

**Skip anything tooling already enforces** (linter, type-checker, formatter) — those are caught for free;
review for what tools can't see. A finding a `ruff`/`pyright` run would flag is noise here.

### Triage by context, not by pattern name

| Context | Broad except is... | Unchecked returncode is... |
|---------|--------------------|----|
| Clinical/report output | **CONFIRMED** — silent data loss | **CONFIRMED** — garbage in reports |
| External API/network call | FALSE POSITIVE — correct pattern | N/A |
| `validate()` tool checks | FALSE POSITIVE — expected | FALSE POSITIVE |
| Post-output stats gathering | FALSE POSITIVE — acceptable | **PARTIAL** — should warn |

### For each finding

1. **Read the actual file** at the cited location. Line numbers are often wrong — search for the pattern.
2. **Verdict:** CONFIRMED / PARTIAL / FALSE POSITIVE
3. **CONFIRMED + straightforward fix (<20 lines):** fix, verify import/load, commit in target repo.

**Do NOT fix:** business-logic you haven't read, deliberate fuzzy joins, test side-effects, behavior-changing fixes.

## Step 5: Report

```
## Diff Review: $PROJECT <range> ($FOCUS)
- Findings: N total (H HIGH, M MEDIUM, L LOW)
- Validated: X of Y HIGH findings
- Confirmed: A, False positive: B, Partial: C
- Fixed: D changes committed
```

### Artifact Output

```bash
mkdir -p ~/.claude/artifacts/$PROJECT
```

Write `~/.claude/artifacts/$PROJECT/code-review-$(date +%Y-%m-%d).json` with confirmed/unfixed summary
for downstream skills (`/observe audit`, `/critique close`).

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

## Depth presets (for critique/execute callers)

| Preset | Scout focus | Provider | Notes |
|--------|-------------|----------|-------|
| `low` | patterns | openai | Per-phase gate; ≤4 findings target |
| `high` | security + patterns | openai + `--both` on diff scope | Slice closeout; recall mode |

Pass only changed files (`--file`, `--module`, or a hand-built context packet) — don't scan the
whole repo.

## Usage Examples

```
/diff-review HEAD~3..HEAD          # default preset (low)
/diff-review abc123..def456 high   # slice closeout, recall mode
```

## What This Skill Does NOT Do

- **Does not call Anthropic's built-in `/code-review`** — local scouts only.
- **Does not rotate through projects on a timer** — cut 2026-10-18.
- **Does not skip validation** — every HIGH requires reading actual code.
- **Does not fix everything** — only CONFIRMED straightforward fixes get committed.

$ARGUMENTS

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-07-14] Diff-scoped module dry-run silently omitted oversized changed files direct_table_online.py and test_direct_table_online.py while reporting success; scout must list/fail-loud on skipped files or chunk them.**
- **[2026-10-24] Module mode silently skipped every `.swift` file and extensionless script (suffix allowlist) and printed "No new findings" (arena tools/wow-run, 2,087 Swift lines). Fixed agent-infra ab4d70bd: more suffixes, shebang scripts, and a `Not reviewed (not source by suffix): …` stderr line. Read that line before reporting coverage.**
