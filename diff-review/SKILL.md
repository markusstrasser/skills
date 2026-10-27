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

**Not Anthropic's built-in `/code-review`** (`/code-review ultra` is the paid multi-agent cloud review). Critique/execute closeouts call this skill for the diff layer. No timer rotation; a whole-project pass is `"$SCOUT" <project> --focus <focus>`. Naming/rotation history: [background.md](references/background.md).

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

**Provider order (local-first; full wording in [background.md](references/background.md)):**
1. **`openai`** (default) — `gpt-6-astra` low effort, codex-cli subscription ($0).
2. **`sol`** — `gpt-6.1-sol` high effort; rerun with `--provider sol` on an Astra plan-limit error (llmx exit 6).
3. **`sol-api`** — `gpt-6.1-sol` high on the metered OpenAI API (`--auth api`, ~$0.1–0.3 per review) when Astra and Sol both return exit 6.
4. **`google`** — Gemini via llmx (paid API); last resort. It may also be capped (exit 6 "SPENDING CAP REACHED").

No `cursor` provider (retired 2026-10-07). `--both` (google + openai; `--all-providers` is the same set) only for an explicitly requested high-recall review or a concrete unresolved risk needing another model; module size alone does not justify it.

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

## Module-depth lens (design-level findings; vocabulary and sources in [background.md](references/background.md))

- **Shallow module** — interface nearly as complex as its implementation; fix is depth (leverage at the interface), not more wrappers.
- **Hypothetical seam** — a port with a single implementation is needless indirection: one adapter = hypothetical, two = real. Flag single-adapter ports.
- **Deletion test** — if deleting the module breaks little, it is dead code / over-abstraction.
- **Tests past the interface** — tests asserting internal state instead of observable behavior.

## Metric-claim diffs (agent-authored)

When a diff claims a score, speedup or pass-rate gain, flag any same-diff edit to tests, scorers, tolerances, thresholds, fixtures or eval data, and check numeric checks are scale-invariant and cover the whole output (agents game graders unprompted; evidence in [background.md](references/background.md)).

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
- **[2026-10-26] The openai provider's fixed `--timeout 180` killed a 65 KB file (arena tools/wow-logger/src/bin/hudcheck.rs, llmx exit 4), and `--file` refuses a file over 100,000 bytes without chunking (hud.rs, 110,901 bytes): both stayed unreviewed until the parent ran `llmx chat --subscription -m gpt-6-astra --timeout 1200 -f <file>` by hand. The timeout should scale with batch bytes and `--file` should chunk.**
- **[2026-10-27] Sol does not survive Astra's account limit. Astra exited 6 with "You've hit your usage limit. Visit https://chatgpt.com/settings/usage to purchase more credits or try again at Nov 2nd, 2026 5:00 PM", and `gpt-6.1-sol` exited 6 a minute later with the identical text (genomics negatives-panels review, llmx logs 06:56/06:57 JST). That message is the ChatGPT account's usage limit, which both codex-cli models draw on; when it appears, skip step 2 and go to google (`gemini-4-argon`).**
- **[2026-10-27] Codex plan exhausted until 11-02 for both Codex models; Gemini monthly spending cap hit the same day; added `--provider sol-api` (metered gpt-6.1-sol) as step 3.**
