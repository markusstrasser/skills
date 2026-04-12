---
name: sweep
description: "Cheap-model codebase consistency scan. Uses structural analysis + Gemini Flash as classifier to find pattern drift, convention violations, config misalignment, and function divergence. Git-change-driven scope. Near-free ($0 via CLI). Use when: 'check for inconsistencies', 'sweep the codebase', 'what diverged recently', 'pattern drift'."
user-invocable: true
argument-hint: "[axes...] [--depth N] [--path dir]"
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: medium
---

# Sweep — Structural Consistency Scan

Find pattern drift and convention violations across a codebase using structural
analysis first, then Gemini Flash as a cheap classifier for cross-file
consistency. Git-log-driven scope focuses on areas that changed recently.

## Why This Exists (Not /upgrade)

`/upgrade audit` dumps the whole codebase to Gemini Pro + GPT-5.4 ($$$) for
bug-finding. `/sweep` does the opposite: mechanical/structural analysis covers
80% of consistency issues for $0, then Flash classifies the remaining ambiguous
cases. Different tool, different cost profile, different failure mode coverage.

| | `/upgrade audit` | `/sweep` |
|---|---|---|
| Model | Gemini Pro + GPT-5.4 | Gemini Flash (free CLI) |
| Cost | $2-5 per run | ~$0 |
| Time | 15-30 min | 5-10 min |
| Focus | Bugs, error handling, logic | Pattern drift, convention compliance, config alignment |
| Scope | Whole codebase | Git-change-driven hot zones |
| Strength | Finds subtle logic bugs | Finds structural inconsistency across many files |

## Invocation

```
/sweep                          # All axes, default depth 40
/sweep config conventions       # Specific axes only
/sweep --depth 100              # Deeper git history
/sweep --path scripts/          # Scope to directory
```

## Methodology

Five phases, each building on the last. Phases 1-2 are mechanical (no model).
Phase 3 uses Flash. Phase 4 verifies. Phase 5 synthesizes.

### Phase 1: Scope (git-driven, ~30s)

Identify hot zones from recent git activity.

```bash
# Recent commits with file stats
git log --oneline --stat --no-merges -${DEPTH:-40} | head -300

# Group by file to find churn hotspots
git log --oneline --no-merges -${DEPTH:-40} --format="" --name-only | sort | uniq -c | sort -rn | head -30
```

The output identifies:
- **Bulk-change commits** (10+ files) — highest drift risk
- **Fix-wave commits** ("Fix N failures", "Fix N promoted") — residual issues likely
- **File churn hotspots** — files changed repeatedly indicate instability

### Phase 2: Structural Checks (mechanical, ~3 min)

Run cross-file analysis for each active axis. These are deterministic — no
model needed. See `references/axes.md` for the check scripts per axis.

**Output format per check:**
```
AXIS: config
CHECK: database_versions.json vs dataset_registry.py alignment
FOUND: 45 entries in A not in B, 28 entries in B not in A
SEVERITY: HIGH
FILES: config/database_versions.json, scripts/dataset_registry.py
```

Collect all findings into a structured list before moving to Phase 3.

### Phase 3: Flash Classification (~1 min)

For each axis with ambiguous findings (pattern consistency, cross-file logic),
prepare a focused context file and dispatch to Gemini Flash via the shared
dispatch wrapper.

**Dispatch pattern:**
```bash
# Prepare axis context (concatenate relevant file heads)
# IMPORTANT: one combined file, not multiple -f flags
awk 'FNR==1{print "\n=== FILE: " FILENAME " ===\n"}1' file1.py file2.py > /tmp/sweep_axis.txt

# Prepend the analysis prompt
cat references/flash-prompts.md axis_prompt > /tmp/sweep_prompt.txt
cat /tmp/sweep_prompt.txt /tmp/sweep_axis.txt > /tmp/sweep_combined.txt

# Dispatch via shared wrapper
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile fast_extract \
  --context /tmp/sweep_combined.txt \
  --prompt "Execute the analysis task. Be concise and specific. For each issue: file, concept, what's wrong, what it should be." \
  --output /tmp/sweep_axis_results.md
```

**Parallel dispatch:** Each axis gets its own dispatch. Run them in parallel
(background Bash commands or parallel Agent calls). Flash is fast enough that
serial is also acceptable for < 4 axes.

**Context budget:** Flash has 1M token context. Include full files for small
modules (< 500 lines), head-only (first 80 lines) for large files. The
structural checks from Phase 2 tell you which files to include.

### Phase 4: Verification (~2 min)

**Flash hallucinates specifics.** Before including any Flash finding in the
report, verify it against source:

1. **File/function existence:** `ls`, `grep` the claimed path/name
2. **Copy-paste claims:** Read the actual lines — is the description really wrong?
3. **Missing feature claims:** `grep` for the claimed missing function/type
4. **Schema mismatch claims:** Read the Pydantic model AND the JSON — do they actually conflict?

**Verification hit rate from this session:** Flash correctly identified 5/6
specific findings. 1 hallucinated finding (trait_panels.json structure was
nested under `panels` key, not top-level — the scan script failed, not the
data). Expect ~80% accuracy on specific claims, higher on structural patterns.

Drop any finding that fails verification. Don't present unverified Flash output
as confirmed.

### Phase 5: Synthesis (~2 min)

Write findings to `docs/audit/sweep-{date}/findings.md` using the template in
`references/findings-template.md`. Group by severity tier:

| Tier | Meaning | Example |
|------|---------|---------|
| CRITICAL | Semantic data errors, wrong biological/business facts | Copy-paste descriptions on wrong entities |
| HIGH | Structural inconsistency blocking orchestration/automation | Unregistered stages, missing decorators, dual identical functions |
| MEDIUM | Pattern drift causing confusion, silent bug risk | Diverged duplicate functions, stalled migrations |
| LOW | Tech debt, cosmetic inconsistency | Image declaration variety, naming mismatches |

For each finding, include:
- **ID** (F1, F2, ...)
- **Severity tier**
- **What:** one-line description
- **Evidence:** the grep/script output that proves it
- **Files:** affected file list
- **Fix:** concrete remediation (not "should be fixed")

End with a **Remediation Plan** — phased, ordered by severity, with effort
estimates. Deferred items get explicit justification.

## Axes

| Axis | What it checks | Mechanical | Flash |
|------|---------------|------------|-------|
| `config` | Config JSON vs Pydantic models, dual-registry alignment, schema drift | Yes | Yes |
| `conventions` | Import patterns, decorator adoption, function compliance (`write_json_atomic` vs `json.dump`, `run_cmd` vs `subprocess.run`) | Yes | No |
| `duplication` | Diverged copy-paste functions across files (hash comparison) | Yes | Optional |
| `registration` | Stage registry vs actual scripts, dataset registry completeness | Yes | No |
| `ir` | Typed IR layers: payload/adapter/assembly/policy coverage, orphan types, phantom imports | No | Yes |
| `lifecycle` | `@stage` / `init_stage` / `finalize_stage` / `vol.commit` consistency | Yes | No |
| `paths` | `Paths()` adoption vs legacy `DATA_DIR` / f-string construction | Yes | No |

**Default:** all axes. Specify axis names as positional args to filter.

See `references/axes.md` for the mechanical check scripts per axis.

## Anti-Patterns

1. **Don't send the whole codebase to Flash.** It's a classifier, not a
   reviewer. Send focused slices (10-20 file heads per axis, < 50KB each).

2. **Don't skip Phase 2.** Mechanical checks catch 60-70% of findings for
   $0 and 0 hallucination risk. Flash is for the remaining ambiguous cases.

3. **Don't trust Flash file paths.** Verify every path it mentions.
   Hallucination rate on specific paths: ~15-20%.

4. **Don't use this for bug-finding.** Pattern drift ≠ bugs. Use `/upgrade
   audit` for "is this code correct?" and `/sweep` for "is this code
   consistent with the rest?"

5. **Don't re-run on the same commit range.** Check `docs/audit/sweep-*/`
   for prior findings first. Run delta only on new commits since last sweep.

## Integration with Other Skills

- After `/sweep` finds convention violations → `/upgrade harness` to add enforcement
- After `/sweep` finds diverged functions → extract to shared module (manual or `/simplify`)
- After `/sweep` finds config drift → `/bio-verify` for biological constant validation
- `/improve harvest` can consume sweep findings as input

## Cost Model

- Phase 1-2: $0 (local grep/python)
- Phase 3: $0 (Gemini Flash via CLI free tier)
- Phase 4-5: $0 (local verification + writing)
- **Total: $0 per run** unless CLI rate-limited (then ~$0.01 via API fallback)
