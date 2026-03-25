---
name: sweep
description: Verify-fix-reverify loop. Runs a verification command, fixes confirmed issues, re-verifies until clean or max iterations. Eliminates manual "rinse and repeat" coordination.
argument-hint: <verify-command> [--max-iterations N] [--fix-strategy auto|manual]
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Agent
effort: medium
---

# Sweep: Verify-Fix-Reverify Loop

You are running an autonomous verification loop. The user wants zero confirmed issues — your job is to iterate until that's true or you've hit the iteration limit.

## Parse Arguments

`$ARGUMENTS` contains the verification command and optional flags. Parse:
- **Verify command** (required) — the shell command to run for verification
- `--max-iterations N` (default: 5) — safety valve to prevent infinite loops
- `--fix-strategy auto|manual` (default: auto)
  - `auto`: fix confirmed issues directly, then re-verify
  - `manual`: list confirmed issues, wait for user approval before fixing

If the user provides just a description (not a command), help them construct the verify command first.

## The Loop

### Iteration N of max_iterations:

#### 1. Verify

Run the verification command via Bash. Capture full output.

```bash
# Example
uv run ruff check scripts/ --select E,F 2>&1
```

If the command exits 0 with no output: **done** — all clean. Print summary and stop.

#### 2. Classify Findings

For each issue in the output, classify:

| Classification | Meaning | Action |
|---------------|---------|--------|
| **CONFIRMED** | Real issue, fixable, clear what to change | Fix it |
| **FALSE_POSITIVE** | Not actually wrong, or intentional | Document why, skip |
| **UNCLEAR** | Needs investigation before fixing | Investigate, then reclassify |

**How to classify:** Read the relevant code. Understand the context. Don't blindly fix linter output — some findings are intentional patterns, suppressed warnings, or out-of-scope issues. If in doubt, classify as UNCLEAR and investigate.

#### 3. Fix (auto strategy)

For each CONFIRMED finding:
1. Read the relevant file(s)
2. Apply the minimal fix (Edit preferred over Write)
3. Record: file path, what changed, why

For UNCLEAR findings: investigate (read surrounding code, check if intentional), then reclassify as CONFIRMED or FALSE_POSITIVE.

If `--fix-strategy manual`: list all CONFIRMED findings with proposed fixes. Wait for user approval before applying.

#### 4. Check Termination

- **CONFIRMED count == 0** after fixing + re-verify: **done**. Print summary.
- **iteration == max_iterations**: **stop**. Print summary with remaining issues.
- **All remaining are FALSE_POSITIVE**: **done**. Print summary noting false positives.
- **No progress** (same issues found as last iteration): **stop**. The fixes aren't working — report what's stuck.
- Otherwise: **next iteration**.

## Commit Strategy

After each iteration that fixes issues, commit the changes:
```
[sweep] Fix N issues from {tool} — iteration M of K
```

This allows rollback of individual iterations if a fix introduces regressions.

## Summary (always print at end)

```
## Sweep Summary

| Metric | Value |
|--------|-------|
| Iterations run | N |
| Issues found (total, across all iterations) | N |
| Issues fixed | N |
| False positives | N |
| Remaining (unfixed) | N |

### Changes Made
- `path/to/file.py:42` — description of fix
- `path/to/other.py:17` — description of fix

### False Positives (not fixed)
- `path/to/file.py:55` — why this is intentional

### Remaining Issues (if any)
- `path/to/stuck.py:10` — why this couldn't be fixed
```

## Examples

```bash
# Lint sweep — fix all ruff errors iteratively
/sweep "uv run ruff check scripts/ --select E,F"

# Type-check sweep
/sweep "uv run mypy src/ --ignore-missing-imports" --max-iterations 3

# Custom verification script
/sweep "uv run python3 scripts/batch_verify_variants.py --extract scripts/"

# Manual approval mode
/sweep "uv run pytest tests/ -x" --fix-strategy manual
```

## Anti-Patterns to Avoid

- **Don't fix what you don't understand.** Read the code before editing. A "fix" that breaks intentional behavior is worse than the original issue.
- **Don't loop on the same unfixable issue.** If an issue persists after a fix attempt, classify it as remaining and stop.
- **Don't commit fixes that introduce new issues.** If your fix creates new findings, investigate before continuing.
- **Don't exceed max_iterations.** The limit exists to prevent runaway loops. Report what's left and let the user decide.
