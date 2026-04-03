---
name: project-upgrade
description: Autonomous codebase improvement. Standard mode finds bugs via Gemini+GPT. --harness finds architectural leverage (typed guarantees, enforcement, unification for agent-developed codebases). --deferred re-triages prior deferrals.
argument-hint: [path or --harness or --deferred or --quick or --thorough]
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Agent
  - Task
effort: medium
---

# Project Upgrade — Autonomous Codebase Improvement

Feed entire codebase to Gemini 3.1 Pro (1M context), get structured findings, triage with disposition table, execute fixes with verification and rollback. Each verified change gets its own git commit.

## Prerequisites

- `llmx` CLI installed (`which llmx`)
- Gemini API key configured (for 1M context analysis)
- Clean git working tree (will error if dirty)
- Project must fit in ~500K tokens (most projects under 50K LOC do)

## Phase 0: Pre-Flight

### Check Prior Artifacts

Before scanning, check if recent skill artifacts exist — they save re-discovery time:

```bash
ls ~/.claude/artifacts/$PROJECT_NAME/code-review-*.json 2>/dev/null
ls ~/.claude/artifacts/$PROJECT_NAME/model-review-*.json 2>/dev/null
```

If recent artifacts exist (within last 7 days), read them and incorporate their findings into Phase 2 triage. Don't re-scan for issues already identified by code-review or model-review.

### Environment

```bash
PROJECT_ROOT="${ARGUMENTS:-$(pwd)}"
PROJECT_ROOT=$(cd "$PROJECT_ROOT" && pwd)  # resolve to absolute
PROJECT_NAME=$(basename "$PROJECT_ROOT")
UPGRADE_DIR="$PROJECT_ROOT/.project-upgrade/$(date +%Y-%m-%d)"
mkdir -p "$UPGRADE_DIR"

cd "$PROJECT_ROOT"

# Fail if dirty working tree
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: Dirty working tree. Commit or stash first."
  exit 1
fi
```

### Backlog Gate

Before generating new findings, check if there's already a large unfixed backlog:

```bash
# Check existing finding volume
FINDING_COUNT=0
if [ -f "$PROJECT_ROOT/scripts/fix_backlog.py" ]; then
  FINDING_COUNT=$(cd "$PROJECT_ROOT" && uv run python3 scripts/fix_backlog.py count 2>/dev/null || echo 0)
elif [ -d "$PROJECT_ROOT/.project-upgrade" ]; then
  FINDING_COUNT=$(find "$PROJECT_ROOT/.project-upgrade" -name "*.json" -exec cat {} + 2>/dev/null | python3 -c "import sys,json; data=sys.stdin.read(); print(sum(len(json.loads(x)) if isinstance(json.loads(x),list) else 0 for x in data.split('}][{')))" 2>/dev/null || echo 0)
fi
```

If more than 50 unfixed findings exist, **do not generate more.** Instead:
1. Print: "⚠ Backlog has $FINDING_COUNT unfixed findings. Fix before auditing."
2. Show the top 10 by severity: `uv run python3 scripts/fix_backlog.py next 10` (if available)
3. Offer to switch to fix mode: pick the top finding and implement the fix
4. Only proceed with new audit if user explicitly overrides with `--force`

This gate prevents the audit-accumulation pattern where findings pile up faster than they're fixed.

### Detect project language and tooling

```bash
# Language detection
if [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
  LANG="python"
  RUNNER="uv run python3"
elif [ -f "package.json" ]; then
  LANG="javascript"
  RUNNER="npx"
elif [ -f "Cargo.toml" ]; then
  LANG="rust"
  RUNNER="cargo"
else
  LANG="generic"
  RUNNER=""
fi

# Test runner detection
if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ] && grep -q "pytest" pyproject.toml 2>/dev/null; then
  TEST_CMD="uv run pytest -x -q 2>&1 | tail -20"
elif [ -f "package.json" ] && grep -q '"test"' package.json; then
  TEST_CMD="npm test 2>&1 | tail -20"
elif [ -f "Cargo.toml" ]; then
  TEST_CMD="cargo test 2>&1 | tail -20"
else
  TEST_CMD=""
fi
```

### Baseline snapshot

Capture before-state for comparison:

```bash
# Line counts
find . \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.rs" \) \
  -not -path "*/node_modules/*" -not -path "*/__pycache__/*" -not -path "*/.git/*" | \
  xargs wc -l 2>/dev/null | tail -1 > "$UPGRADE_DIR/baseline-loc.txt"

# Import check (Python)
if [ "$LANG" = "python" ]; then
  find . -name "*.py" -not -path "./.git/*" -not -path "./__pycache__/*" | while read -r f; do
    uv run python3 -c "import ast; ast.parse(open('$f', encoding='utf-8').read())" 2>&1 || echo "SYNTAX_ERROR: $f"
  done > "$UPGRADE_DIR/baseline-syntax.txt" 2>&1
fi

# Test results (if tests exist) — capture exit code explicitly
if [ -n "$TEST_CMD" ]; then
  set +e
  eval "$TEST_CMD" > "$UPGRADE_DIR/baseline-tests.txt" 2>&1
  echo "EXIT_CODE=$?" >> "$UPGRADE_DIR/baseline-tests.txt"
  set -e
fi

# Lint results (Python)
if [ "$LANG" = "python" ] && command -v ruff &>/dev/null; then
  ruff check . --select E,F,W --statistics 2>&1 | tail -20 > "$UPGRADE_DIR/baseline-lint.txt"
fi
```

## Phase 1: Dump Codebase

### Diff-Aware Mode (recommended for repeat runs)

If a `.project-upgrade/last-baseline.sha` file exists, only analyze changed files + their import graph. 10x cheaper, can run daily.

```bash
LAST_SHA_FILE="$PROJECT_ROOT/.project-upgrade/last-baseline.sha"
DIFF_MODE="false"

if [ -f "$LAST_SHA_FILE" ]; then
  LAST_SHA=$(cat "$LAST_SHA_FILE")
  if git rev-parse --verify "$LAST_SHA" >/dev/null 2>&1; then
    CHANGED_FILES=$(git diff --name-only "$LAST_SHA" HEAD -- '*.py' '*.js' '*.ts' '*.rs' '*.go' '*.sh')
    if [ -n "$CHANGED_FILES" ]; then
      DIFF_MODE="true"
      echo "$CHANGED_FILES" > "$UPGRADE_DIR/changed-files.txt"
      echo "Diff-aware mode: $(echo "$CHANGED_FILES" | wc -l | tr -d ' ') files changed since $(echo $LAST_SHA | head -c 8)"
    else
      echo "No files changed since last run. Nothing to analyze."
      exit 0
    fi
  fi
fi
```

### Full Dump (first run or when --full flag is passed)

Bundle the codebase into a structured document for Gemini.

```bash
if [ "$DIFF_MODE" = "true" ]; then
  # Dump only changed files + their direct importers
  uv run python3 "$(dirname "$0")/scripts/dump_codebase.py" \
    "$PROJECT_ROOT" \
    --output "$UPGRADE_DIR/codebase.md" \
    --max-tokens 400000 \
    --files-from "$UPGRADE_DIR/changed-files.txt"
else
  uv run python3 "$(dirname "$0")/scripts/dump_codebase.py" \
    "$PROJECT_ROOT" \
    --output "$UPGRADE_DIR/codebase.md" \
    --max-tokens 400000
fi
```

If `dump_codebase.py` doesn't exist or fails, do it inline:

```bash
{
  echo "# Codebase: $PROJECT_NAME"
  echo ""

  # Project config files first
  for f in CLAUDE.md pyproject.toml Cargo.toml package.json Makefile; do
    [ -f "$f" ] && echo -e "\n## $f\n\`\`\`\n$(cat "$f")\n\`\`\`"
  done

  # All source files, sorted by modification time (newest first)
  find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.rs" -o -name "*.go" -o -name "*.sh" \) \
    -not -path "./.git/*" \
    -not -path "./node_modules/*" \
    -not -path "./__pycache__/*" \
    -not -path "./.venv/*" \
    -not -path "./target/*" \
    -not -path "./.project-upgrade/*" \
    -printf '%T@ %p\n' 2>/dev/null | sort -rn | cut -d' ' -f2- | while read filepath; do
      echo -e "\n## $filepath"
      echo '```'
      cat "$filepath"
      echo '```'
  done
} > "$UPGRADE_DIR/codebase.md"
```

Check token budget:
```bash
TOKEN_EST=$(wc -c < "$UPGRADE_DIR/codebase.md" | awk '{print int($1/4)}')
echo "Estimated tokens: $TOKEN_EST"
if [ "$TOKEN_EST" -gt 500000 ]; then
  echo "WARNING: >500K tokens. Consider splitting or truncating large files."
fi
```

## Phase 2: Multi-Model Analysis

Send codebase to BOTH Gemini 3.1 Pro AND GPT-5.4 in parallel. Cross-family review catches 31pp more errors than single-model (FINCH-ZK). Same-model review is a martingale.

**llmx provider names:** Google is `-p google` (NOT `-p gemini`). OpenAI is `-p openai`. Run `llmx --list-providers` if unsure.

**Temperature:** Gemini 3.1 Pro locks to 1.0 server-side (thinking model) — do NOT pass `-t`.

**IMPORTANT:** Always pass `--max-tokens 65536` on Gemini dispatches — the server default is 8K which silently truncates large JSON output.

**Coordination with other agents:** If the active Claude/Codex session count is >= 2, check what the other agent is working on BEFORE planning. On macOS/BSD, do **not** use `pgrep -c`; use `pgrep -lf claude | wc -l` or the existing `~/.claude/active-agents.json` probe. Then run `git log --oneline -10` and `cat MAINTAIN.md CYCLE.md 2>/dev/null | head -40`. Plan only your DELTA — items the other agent is NOT already handling. Don't re-plan owned work.

### Dispatch both models in parallel

```bash
# IMPORTANT: Use -f for context file, NOT cat | pipe (stdin dropped when prompt arg provided)
# Gemini (pattern detection, architecture, 1M context)
llmx chat -p google -m gemini-3.1-pro-preview \
  -f "$UPGRADE_DIR/codebase.md" \
  --stream --timeout 600 --max-tokens 65536 \
  -o "$UPGRADE_DIR/gemini-raw.txt" \
  "$(cat "$UPGRADE_DIR/gemini-prompt.md")" 2>"$UPGRADE_DIR/gemini-stderr.txt" &

# GPT-5.4 (formal reasoning, quantitative analysis)
llmx chat -p openai -m gpt-5.4 \
  -f "$UPGRADE_DIR/codebase.md" \
  --reasoning-effort high --stream --timeout 600 --max-tokens 32768 \
  -o "$UPGRADE_DIR/gpt-raw.txt" \
  "$(cat "$UPGRADE_DIR/gpt-prompt.md")" 2>"$UPGRADE_DIR/gpt-stderr.txt" &

wait
echo "Both models complete"
```

### Gemini prompt (pattern/architecture focus)

Write to `$UPGRADE_DIR/gemini-prompt.md`:

```bash
cat > "$UPGRADE_DIR/gemini-prompt.md" << 'PROMPT_EOF'
You are analyzing an entire codebase for CONCRETE, VERIFIABLE improvements. Not vague suggestions — specific issues with specific fixes.

PROJECT: $PROJECT_NAME
LANGUAGE: $LANG

RULES:
1. Only report issues you are CERTAIN about. If unsure, skip it.
2. Every finding MUST reference specific file paths.
3. 'Add more tests' is NOT a finding. 'Function X in file Y handles user input with no validation' IS.
4. Infer the project's conventions from the MAJORITY pattern, then find VIOLATIONS of that convention.
5. Do NOT suggest rewriting working code for style preferences.
6. Do NOT suggest adding comments, docstrings, or type annotations unless something is actively misleading.
7. Do NOT suggest enterprise patterns (monitoring, CI/CD, auth) for personal/small projects.

OUTPUT FORMAT: Respond with ONLY a JSON array. No markdown, no commentary. Each element:
{
  \"id\": \"F001\",
  \"category\": \"<one of the categories below>\",
  \"severity\": \"high|medium|low\",
  \"files\": [\"path/to/file.py\"],
  \"lines\": \"optional line range, e.g. 45-67\",
  \"description\": \"What is wrong, specifically\",
  \"fix\": \"Exact change to make — code-level, not hand-waving\",
  \"verification\": \"How to confirm the fix works (a command, a grep, a test)\",
  \"risk\": \"What could break if this fix is wrong\"
}

CATEGORIES (only these):
- DEAD_CODE: Functions, classes, imports, or entire files never used anywhere in the codebase
- NAMING_INCONSISTENCY: Naming that violates the project's own majority convention
- PATTERN_INCONSISTENCY: Error handling, logging, config access, or init patterns that differ from the dominant pattern in this codebase
- DUPLICATION: Logic duplicated across 2+ files (not similar — actually duplicated)
- ERROR_SWALLOWED: Bare except, empty catch, errors logged but not raised, silent failures
- IMPORT_ISSUE: Circular imports, imports that would fail, unused imports (only flag if >3 unused in one file)
- HARDCODED: Paths, URLs, thresholds, credentials that should be config/constants
- BROKEN_REFERENCE: References to files, functions, variables, or modules that don't exist
- MISSING_SHARED_UTIL: A pattern repeated 3+ times that should be extracted to a shared utility
- COUPLING: Module A depends on Module B's internals when it shouldn't need to

PRIORITY ORDER: BROKEN_REFERENCE > ERROR_SWALLOWED > IMPORT_ISSUE > DUPLICATION > PATTERN_INCONSISTENCY > MISSING_SHARED_UTIL > the rest.

CRITICAL: Output valid JSON only. Start with [ and end with ]. No text before or after.
PROMPT_EOF
```

### GPT prompt (harness/type-safety/agent-DX focus)

Write to `$UPGRADE_DIR/gpt-prompt.md`. Give GPT a DIFFERENT angle than Gemini — harness improvements, type safety architecture, agent-friendly patterns:

```bash
cat > "$UPGRADE_DIR/gpt-prompt.md" << 'PROMPT_EOF'
You are a senior software architect specializing in developer tooling, type systems, and AI-assisted development. Analyze this codebase for improvements to its SWE harness, abstractions, and developer experience.

Focus areas:
1. **Harness improvements** — decorators, base classes, protocols that prevent incorrect code
2. **Programmatic enforcement** — what can be enforced at import/test/commit time?
3. **Unification opportunities** — repeated patterns that should be centralized
4. **Type safety architecture** — what type checking investment gives the best ROI?
5. **Agent DX patterns** — patterns that prevent common AI agent mistakes
6. **Scalability patterns** — what will break as the codebase grows?

Be specific. Reference exact files, function names, line counts. Don't propose things that already exist.

Return findings as JSON array:
[{"id": "G001", "title": "...", "category": "harness|hooks|unification|type_safety|agent_dx|scalability", "priority": "HIGH|MEDIUM|LOW", "scripts_affected": "N scripts", "approach": "...", "code_sketch": "..."}]
PROMPT_EOF
```

### Parse both outputs

Extract JSON from both model responses (they sometimes wrap in markdown):

```bash
for MODEL in gemini gpt; do
python3 << PYEOF
import json, re, sys

text = open('$UPGRADE_DIR/${MODEL}-raw.txt').read()

# Strip markdown code fences if present
text = re.sub(r'```json\s*', '', text)
text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)

# Find the first complete JSON array (non-greedy would fail on nested arrays)
# Instead, find first [ and use bracket counting
start = text.find('[')
if start == -1:
    print(f'ERROR: No JSON array found in ${MODEL} output', file=sys.stderr)
    sys.exit(1)

depth = 0
end = start
for i, ch in enumerate(text[start:], start):
    if ch == '[': depth += 1
    elif ch == ']': depth -= 1
    if depth == 0:
        end = i + 1
        break

json_str = text[start:end]

# Sanitize trailing commas (LLMs produce these frequently)
json_str = re.sub(r',\s*([\]}])', r'\1', json_str)

try:
    data = json.loads(json_str)
    with open('$UPGRADE_DIR/${MODEL}-findings.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(f'${MODEL}: Parsed {len(data)} findings')
except json.JSONDecodeError as e:
    print(f'ERROR: Invalid JSON from ${MODEL}: {e}', file=sys.stderr)
    with open('$UPGRADE_DIR/${MODEL}-raw-extract.txt', 'w') as f:
        f.write(json_str)
    sys.exit(1)
PYEOF
done
```

### Synthesize: Convergence Analysis

After both models return, the orchestrating agent (Claude) reads both `gemini-findings.json` and `gpt-findings.json` and produces a convergence table:
- **Convergent findings** (both models flagged) → highest confidence
- **Model-unique findings** → verify against code before accepting
- **Contradictions** → investigate, don't auto-resolve

Write synthesis to `$UPGRADE_DIR/synthesis.md`.

## Phase 3: Cross-Validate (Optional)

For high-stakes projects, send a focused summary to GPT-5.4 for second opinion:

```bash
# Only if findings.json has >10 items or user requested thorough mode
FINDING_COUNT=$(python3 -c "import json; print(len(json.load(open('$UPGRADE_DIR/findings.json'))))")

if [ "$FINDING_COUNT" -gt 10 ] || [ "$THOROUGH" = "true" ]; then
  # Send findings + key files to GPT for validation
  {
    echo "# Gemini's Findings (verify these)"
    cat "$UPGRADE_DIR/findings.json"
    echo ""
    echo "# Key Source Files"
    # Include only files referenced in findings
    python3 -c "
import json
findings = json.load(open('$UPGRADE_DIR/findings.json'))
files = set()
for f in findings:
    files.update(f.get('files', []))
for f in sorted(files):
    print(f)
" | head -20 | while read filepath; do
      [ -f "$filepath" ] && echo -e "\n## $filepath\n\`\`\`\n$(cat "$filepath")\n\`\`\`"
    done
  } | llmx chat -m gpt-5.4 --reasoning-effort high --stream --timeout 600 "
Gemini analyzed a codebase and produced findings (JSON above). Your job:

1. For each finding: is it CORRECT? Does the code actually have this issue?
2. Which findings are FALSE POSITIVES? (Gemini hallucinated the problem)
3. What did Gemini MISS that you can see in the source files?
4. Rank the real findings by IMPACT (which fixes prevent the most future bugs).

Output a JSON array of objects:
{\"id\": \"F001\", \"verdict\": \"CONFIRMED|FALSE_POSITIVE|NEEDS_CHECK\", \"reason\": \"...\"}

Include new findings Gemini missed as {\"id\": \"NEW_001\", \"verdict\": \"NEW\", ...} using the same schema as Gemini's findings.
" > "$UPGRADE_DIR/gpt-validation.txt" 2>&1
fi
```

## Phase 4: Extract & Triage (Anti-Loss Protocol)

Same pattern as model-review: extract every finding, disposition each one, verify coverage.

### 4a. Automated validity gate (pre-triage)

Before human review, auto-check each finding to reject obvious hallucinations:

```bash
python3 << 'PYEOF'
import json, subprocess

findings = json.load(open('$UPGRADE_DIR/findings.json'))
for f in findings:
    f['_auto_status'] = 'PLAUSIBLE'
    # Check file paths exist
    for path in f.get('files', []):
        result = subprocess.run(['test', '-f', path], capture_output=True)
        if result.returncode != 0:
            f['_auto_status'] = 'INVALID_PATH'
            f['_auto_reason'] = f'File not found: {path}'
            break
    # For DEAD_CODE: grep for callers (dynamic dispatch caveat applies)
    if f.get('category') == 'DEAD_CODE' and f['_auto_status'] == 'PLAUSIBLE':
        # Extract function/class name from description if possible
        desc = f.get('description', '')
        for path in f.get('files', []):
            # Quick check: is the file imported anywhere?
            result = subprocess.run(
                ['grep', '-rl', path.split('/')[-1].replace('.py', ''), '.'],
                capture_output=True, text=True
            )
            if len(result.stdout.strip().split('\n')) > 1:
                f['_auto_status'] = 'NEEDS_CHECK'
                f['_auto_reason'] = 'File is referenced elsewhere — verify manually'

with open('$UPGRADE_DIR/findings.json', 'w') as out:
    json.dump(findings, out, indent=2)

invalid = sum(1 for f in findings if f['_auto_status'] == 'INVALID_PATH')
check = sum(1 for f in findings if f['_auto_status'] == 'NEEDS_CHECK')
plausible = sum(1 for f in findings if f['_auto_status'] == 'PLAUSIBLE')
print(f'Pre-triage: {plausible} plausible, {check} needs check, {invalid} invalid paths')
PYEOF
```

### 4b. Read all findings

Read `findings.json`. If GPT validation exists, cross-reference.

For each finding:
1. **Check `_auto_status`** — Skip INVALID_PATH findings (auto-rejected). Flag NEEDS_CHECK for closer inspection.
2. **Verify against actual code** — Read the file, check if the issue exists. Models hallucinate file paths and function names.
3. **Check if already fixed** — `git log --oneline -5 -- <file>` to see recent changes
4. **Assess risk** — Will this change break other things?

### 4b. Build disposition table

```markdown
## Disposition Table
| ID   | Category | Severity | Disposition | Reason | Risk |
|------|----------|----------|-------------|--------|------|
| F001 | BROKEN_REFERENCE | high | APPLY | Verified: import references deleted file | Low |
| F002 | DEAD_CODE | low | APPLY | Confirmed: function never called | None |
| F003 | DUPLICATION | medium | DEFER | Requires shared util extraction first | Medium |
| F004 | NAMING | low | REJECT | Gemini hallucinated: name IS consistent | N/A |
```

Valid dispositions: `APPLY`, `DEFER (reason)`, `REJECT (reason)`, `MERGE WITH [ID]`

**Evidence requirements for dispositions:**
- **DEFER with "no incidents"**: Must `grep -i KEYWORD CLAUDE.md` and show zero matches. Unverified "no incidents" claims miss documented pitfalls. (Retro 2026-03-27: G008 deferred citing "no incidents" when CLAUDE.md pitfall #18 was the exact incident.)
- **REJECT with "already exists"**: Must cite the specific file:line or test name that provides the existing coverage. "Already enforced by X" without a citation is an unverified factual claim.

### 4c. Coverage check

- Count: total findings, verified, applied, deferred, rejected
- If any finding has no disposition → stop and fix
- Save to `$UPGRADE_DIR/triage.md`

### 4d. Present to user

Show the disposition table. Ask for go/no-go before execution.

**The user approves, modifies, or aborts at this point.**

## Phase 5: Execute (Autonomous After Approval)

For each APPLY finding, ordered by:
1. BROKEN_REFERENCE first (prevent crashes)
2. ERROR_SWALLOWED second (prevent silent failures)
3. IMPORT_ISSUE third (prevent import-time errors)
4. Everything else by severity (high → low)

### Per-finding execution loop

```
For each APPLY finding:
  1. SNAPSHOT: note current HEAD commit
  2. READ: Read all files involved
  3. FIX: Apply the change (Edit tool, not Write — preserve surrounding code)
  4. VERIFY: Run category-specific verification (see matrix below)
  5. If VERIFY passes:
     git add <files>
     git commit -m "[project-upgrade] <category>: <description>"
  6. If VERIFY fails:
     git reset --hard HEAD
     git clean -fd
     Log failure to $UPGRADE_DIR/failures.md
     Continue to next finding
  7. INVARIANT CHECK: After each finding (pass or fail):
     git status --porcelain must be empty
     If not empty, stop and investigate before continuing
```

### Verification matrix

| Category | Verification Command | Pass Condition |
|----------|---------------------|----------------|
| DEAD_CODE | `grep -r "function_name" <project>` + `python3 -c "import <module>"` | Zero callers + no ImportError after removal. Caveat: dynamic dispatch (`getattr`, CLI entry_points) invisible to grep |
| NAMING_INCONSISTENCY | `grep -r "old_name" <project>` | Zero matches |
| PATTERN_INCONSISTENCY | Run existing tests if any | Tests still pass |
| DUPLICATION | Run existing tests + import check on extracted util | Tests pass, util imports |
| ERROR_SWALLOWED | Run existing tests | Tests pass, no new bare except |
| IMPORT_ISSUE | `python3 -c "import <module>"` | No ImportError/circular |
| HARDCODED | `grep -r "<hardcoded_value>" <project>` | Moved to config, old refs gone |
| BROKEN_REFERENCE | `python3 -c "import <module>"` | No ImportError |
| MISSING_SHARED_UTIL | Run existing tests + verify callers updated | Tests pass |
| COUPLING | Import each module independently | Independent import works |

**For JavaScript/TypeScript:** Replace `python3 -c "import"` with `node -e "require()"` or `tsc --noEmit`.
**For Rust:** `cargo check` after each change.
**For all languages:** If tests exist, run them. Test failure = revert.

### Scaffolding phase (REQUIRES SEPARATE APPROVAL)

**This is a second change-set.** Do NOT auto-execute scaffolding after fixes.
Present scaffolding proposals to the user as a separate disposition table. Each proposal must include quantified benefit (e.g., "reduces N duplicated try/except blocks to 1 shared utility").

After individual fixes, assess whether the project needs shared infrastructure:

1. **Shared error handling** — If ERROR_SWALLOWED findings were >3, propose a common error handler
2. **Shared config** — If HARDCODED findings were >3, propose a config module
3. **Import validator** — If IMPORT_ISSUE findings were >2, propose a CI/pre-commit check:
   ```python
   # scripts/check_imports.py — run in CI or as pre-commit hook
   import importlib, sys, pathlib
   errors = []
   for f in pathlib.Path('.').rglob('*.py'):
       module = str(f).replace('/', '.').replace('.py', '')
       try: importlib.import_module(module)
       except Exception as e: errors.append(f"{f}: {e}")
   if errors:
       print('\n'.join(errors))
       sys.exit(1)
   ```
4. **Lint config** — If the project has no linter config, add minimal ruff/eslint

Each scaffolding addition is also committed separately.

## Phase 6: Report

Generate before/after comparison:

```markdown
## Project Upgrade Report: $PROJECT_NAME
**Date:** $(date +%Y-%m-%d)
**Model:** Gemini 3.1 Pro (analysis) + Claude (execution)

### Summary
- Findings: N total (M verified, D deferred, R rejected)
- Applied: X changes across Y files
- Reverted: Z changes (verification failed)
- Scaffolding: [list of infrastructure additions]

### Before/After Metrics
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Lines of code | ... | ... | ... |
| Syntax errors | ... | ... | ... |
| Lint warnings | ... | ... | ... |
| Test results | ... | ... | ... |

### Changes Applied
| Commit | Category | Files | Description |
|--------|----------|-------|-------------|
| abc1234 | BROKEN_REFERENCE | file.py | Fixed import of deleted module |
| ... | ... | ... | ... |

### Changes Reverted (verification failed)
| Finding | Category | Why Failed |
|---------|----------|------------|
| F012 | DUPLICATION | Extracted util broke 2 tests |

### Deferred (manual attention needed)
| Finding | Category | Why Deferred |
|---------|----------|-------------|
| F003 | COUPLING | Requires architectural decision |

### Remaining Recommendations
[Findings that were deferred or need human judgment]
```

Save to `$UPGRADE_DIR/report.md`.

### MAINTAIN.md Integration

If `MAINTAIN.md` exists in the project root (project uses `/maintain`), **you must** also:
- Append to `## Log`: `YYYY-MM-DD | project-upgrade | N findings, M applied, D deferred | [commit range]`
- Append deferred findings (DEFER disposition) to `## Queue` with IDs continuing the M00N sequence
- Append applied fixes to `## Fixed`

This feeds results into the SWE quality lane so `/maintain` can track them.

### Save Baseline SHA (for diff-aware next run)

```bash
git rev-parse HEAD > "$PROJECT_ROOT/.project-upgrade/last-baseline.sha"
echo "Saved baseline SHA for next diff-aware run: $(cat $PROJECT_ROOT/.project-upgrade/last-baseline.sha | head -c 8)"
```

## Anti-Patterns

- **"Top N" triage of confirmed findings.** If a finding is dispositioned APPLY, it gets implemented — all of them. Don't self-select "the top 5 most impactful" and silently drop the rest. If you need to defer something, change its disposition to DEFER with a per-item reason, not a ranking cutoff.
- **Applying all findings without verification.** Each change MUST be verified independently. A "batch apply" that breaks something has no rollback granularity.
- **Trusting Gemini's file paths.** Verify every file path before editing. Gemini hallucinates paths ~15% of the time.
- **Trusting Gemini's "this function is never called."** Grep the codebase. Dynamic dispatch, string-based imports, and CLI entry points are invisible to static analysis.
- **Applying low-severity findings that touch many files.** NAMING_INCONSISTENCY affecting 20 files is high risk for low reward. Defer unless automated (find-and-replace with verification).
- **Skipping the triage step.** The user MUST see and approve the disposition table before execution. This is the kill switch.
- **Over-scaffolding.** Don't add monitoring, CI/CD, auth, or other enterprise patterns to personal projects. Match scaffolding to project scale.

## Effort Tiers

- **Quick scan** (`--quick`): Phase 0-2 only. Produces findings list, no execution. ~2 minutes.
- **Standard** (default): Full pipeline. Triage + execute + report. ~15-30 minutes.
- **Thorough** (`--thorough`): Adds GPT cross-validation (Phase 3). ~30-60 minutes.
- **Harness hardening** (`--harness`): Replaces standard prompts with architecture-focused deep queries. See Phase 2H below.
- **Deferred re-triage** (`--deferred`): Phase 6 only. See below.

## Phase 2H: Harness Hardening Mode (`--harness`)

### The agent-vs-human tradeoff

Standard project-upgrade assumes a human-developed codebase: conventions are readable, patterns are intentional, and large refactors are expensive because human time is the bottleneck. Findings are point fixes — "this specific thing is wrong."

Agent-developed codebases have different failure modes and different economics:

| Dimension | Human-developed | Agent-developed |
|-----------|----------------|-----------------|
| **Why bugs happen** | Logic errors, edge cases | Hallucinated field names, copy-pasted definitions, wrong dict keys, open string vocabularies |
| **What prevents bugs** | Code review, conventions, institutional knowledge | Types, import-time checks, AST linters, StrEnums — things that produce errors, not warnings |
| **Cost of large refactors** | High (human hours) | Near-zero (agent tokens). Scope is never a valid deferral reason. |
| **Convention adherence** | Reasonable — humans read READMEs | Unreliable — agents read types and get import errors. A convention without enforcement is a suggestion. |
| **Duplication pattern** | Intentional variation, DRY applied naturally | Accidental — agents copy-paste definitions across files because they sample partial context |
| **Value of cleanup** | Moderate (readability) | High (prevents compounding drift across future agent sessions) |
| **What to optimize for** | Fewer current bugs | Fewer categories of future bugs |

This means: **in agent codebases, the highest-ROI investment is enforcement infrastructure that makes incorrect code fail at import/construction time, not documentation or convention that agents may not read.** A StrEnum that rejects invalid values prevents more bugs than a comment explaining valid values.

It also means: **never defer based on scope.** "96 scripts to touch" is a parallelizable task, not a blocker. The only valid deferrals are concrete blockers (missing data, needs human semantics decision, dependency chain). This is the opposite of human-project triage where effort is the primary filter.

### What it does

Replaces the standard Phase 2 model prompts with architecture-focused deep queries that find **structural leverage points** — typed guarantees, programmatic enforcement, and unification that prevents entire classes of agent errors. Not "what's broken" but "where can we add guarantees that prevent breakage."

### When to use

- Codebase is primarily agent-developed (enforcement > convention)
- After a standard run has already cleaned obvious bugs
- When the goal is "fewer categories of future bugs" not "fewer current bugs"
- When the codebase has grown to 50+ files with shared modules

### What it finds that standard mode misses

Standard mode finds: dead code, broken references, swallowed errors, duplicated logic.

Harness mode finds:
- **Pydantic roundtrips** — models immediately `.model_dump()`'d back to dicts, losing type safety
- **Open vocabularies** — string fields that should be StrEnum (agents will hallucinate invalid values)
- **Missing Protocols** — duck-typed interfaces with no structural typing contract
- **Duplicate definitions** — constants/sets defined in N files instead of imported from one (agents copy-paste)
- **dict[str, Any] returns** — high-traffic functions returning untyped dicts (agents will index with wrong keys)
- **Missing import-time checks** — registries that should fail loudly when a new subclass has no handler
- **Missing runtime invariants** — cross-field consistency checks that should fire at construction time
- **AST-lintable agent failure modes** — hardcoded threshold literals, hallucinated field names, unsafe key patterns

### Context preparation

Instead of dumping the full codebase, split into two targeted chunks:

**Core modules** (~80-120K tokens): Shared infrastructure that everything imports — config loaders, utility modules, data models, decorators, core abstractions. These are the files where architectural changes have the widest blast radius.

```bash
# Identify core modules (imported by 5+ files)
python3 -c "
import re, collections
from pathlib import Path
imports = collections.Counter()
for f in Path('scripts').glob('*.py'):
    for m in re.findall(r'^from (\w+) import|^import (\w+)', f.read_text(), re.M):
        mod = m[0] or m[1]
        imports[mod] += 1
for mod, count in imports.most_common():
    if count >= 5:
        print(f'{count:3d}  {mod}')
" > "$UPGRADE_DIR/core-module-list.txt"
```

Bundle core modules into `core-modules.md`. Bundle a sample of 10-15 leaf scripts (diverse categories) into `leaf-samples.md`. The leaf samples show how core modules are consumed — without them, the model proposes changes that break callers.

**Leaf samples** (~50-80K tokens): 10-15 representative consumer scripts. Pick diversity: one Modal stage, one local analysis, one lint script, one report generator, one panel script, etc.

### GPT deep queries (3 parallel, targeted angles)

Dispatch 3 GPT-5.4 queries in parallel, each with the same context but a different architectural angle. Use `--reasoning-effort high` and `--max-tokens 32768`.

**Prompt 1 — Enforcement** (`prompt-enforcement.md`):

```
You are auditing this codebase for places where correctness is convention-dependent
but could be made structurally enforced. The codebase is entirely agent-developed —
agents don't read conventions, they read types and get import errors.

Find opportunities for:
1. Import-time checks (fail at import if a contract is violated)
2. Runtime assertions at construction boundaries (dataclass __post_init__, Pydantic validators)
3. AST-based lint rules for patterns agents get wrong (hardcoded values, wrong field names)
4. Type narrowing that eliminates categories of runtime errors (@overload, StrEnum, TypedDict)

For each finding: file path, current code, proposed enforcement, what class of bugs it prevents.
Return as JSON array with: id, category (import_check|runtime_assert|ast_lint|type_narrow),
files, description, code_sketch, bug_class_prevented.
```

**Prompt 2 — Contracts** (`prompt-contracts.md`):

```
You are a type system architect reviewing this codebase. Find the highest-ROI type
safety investments — places where adding types prevents the most downstream errors
per line of type annotation added.

Focus on:
1. Functions returning dict[str, Any] that have a stable shape → TypedDict
2. Pydantic models that are .model_dump()'d immediately → keep as model, use attribute access
3. String parameters that accept a closed set of values → StrEnum or Literal
4. Protocols for duck-typed interfaces (multiple implementations, no shared base)
5. @overload for functions that return different types based on arguments

For each: file, function, current return type, proposed type, number of callers affected.
Return as JSON array with: id, category (typed_return|keep_model|str_enum|protocol|overload),
files, function_name, callers_affected, description, code_sketch.
```

**Prompt 3 — Unification** (`prompt-unification.md`):

```
You are looking for duplication and fragmentation in this codebase — places where
the same concept is defined in multiple files, or where N scripts each implement
their own version of a pattern that should be shared.

Find:
1. Constants/sets defined in 3+ files (e.g., consequence categories, threshold values)
2. Utility functions reimplemented across scripts (e.g., AF parsing, path construction)
3. Configuration patterns that drift between files (some use typed config, some use raw dicts)
4. Data loading patterns duplicated across consumers

For each: list ALL files that have the duplicate, the canonical location (if one exists),
and the migration path. Do NOT propose centralizing things that genuinely vary per-script.
Return as JSON array with: id, category (constant_dup|util_dup|config_drift|loader_dup),
all_files, canonical_location, migration_path, description.
```

### Gemini role in harness mode

Gemini gets the FULL codebase (its 1M context advantage) but with a modified prompt focused on cross-file pattern detection:

```
Analyze this entire codebase. Do NOT look for bugs. Instead, find STRUCTURAL PATTERNS:

1. Which constants, sets, or type definitions appear in 3+ files? List EVERY file.
2. Which functions return dict[str, Any] but always return the same shape?
3. Which string parameters accept only 2-5 distinct values across the codebase?
4. Which pairs of files define the same class/function independently?

This is a DUPLICATION and FRAGMENTATION scan, not a bug scan.
Return JSON array with: id, pattern_type, all_files (complete list), description.
```

Gemini's strength here is completeness — it sees ALL files and can count N accurately. GPT's strength is depth — it reasons about type system architecture. They cover different axes.

### Triage differences

Standard triage asks "is this a real bug?" Harness triage asks:

1. **Does the enforcement already exist?** (Models hallucinate missing features at ~40% rate)
2. **How many callers does this affect?** (Grep the function/type, count importers)
3. **Is the "duplicate" actually intentional variation?** (Some scripts legitimately extend a base set)
4. **What's the injection point?** (Can we change one function/decorator, or do we need N file edits?)

Apply threshold: items that affect <3 files or prevent <1 known bug class → DEFER.

### Expected yield vs standard

| Metric | Standard | Harness |
|--------|----------|---------|
| Findings per model | 10-30 | 5-15 (fewer, higher leverage) |
| Hallucination rate | 40-55% | 40-55% (same — models still hallucinate) |
| Lines changed per finding | 5-20 | 20-200 (structural, not point fixes) |
| Bug classes prevented | 0 (fixes existing bugs) | 1-3 per finding (prevents future classes) |
| AST linters produced | 0 | 2-4 new lint scripts |
| Best paired with | Nothing (standalone) | `--deferred` follow-up after 1 week |

## Phase 6: Deferred Re-Triage (`--deferred`)

Second pass on deferred items from a prior project-upgrade run. No model scan — starts from the existing deferred list in CYCLE.md (or equivalent task queue). Skips Phases 1-3 entirely.

### Why this exists

Deferred items from model reviews have a ~40-50% noise rate because:
- Models hallucinate missing features (the feature was already implemented)
- Models propose registries/abstractions for 3-item collections (overengineering)
- Models flag "drift" in code with no incident history
- Scope estimates assume per-file changes when a single injection point exists
- Deferrals made under context pressure use vague triggers ("when X causes a bug")

Fresh exploration against actual code state resolves these.

### Workflow

**6a. Load deferred items.** Read the deferred section from CYCLE.md or the prior run's triage file. Each item has an ID, description, category, and trigger condition.

**6b. Explore each item.** For each deferred item, dispatch Explore agents to check:
- Does the problem actually exist in the current codebase?
- Has it already been fixed since the deferral?
- Is the trigger condition met?
- What is the real scope? (Find the injection point — often smaller than the description implies.)

Parallelize exploration across items. This is read-only — no code changes yet.

**6c. Re-triage with three dispositions:**

| Disposition | Criteria | Action |
|-------------|----------|--------|
| **KILL** | Problem doesn't exist, feature already implemented, overengineering for current scale, blocked on another killed item | Remove from queue. Document why — prevents re-proposal. |
| **EXECUTE** | Problem is real, trigger is met, scope is tractable | Plan and execute in this session. |
| **KEEP-DEFERRED** | Problem is real but has a concrete blocker (missing data, architectural dependency, needs human decision) | Leave in queue with updated trigger. "Large scope" alone is NOT a valid blocker — agents handle scope. |

**Evidence requirements:**
- **KILL** must cite what was checked (grep output, file read, feature location)
- **EXECUTE** must have verified the problem exists in current code
- **KEEP-DEFERRED** must name a specific blocker, not "needs more design"

**6d. Present disposition table to user.** Same approval gate as Phase 4.

**6e. Execute all EXECUTE items.** Same per-finding loop as Phase 5: read → fix → verify → commit. Order by impact (bugs before cleanup).

**6f. Update queue.** Remove KILL and EXECUTE items from deferred section. Update KEEP-DEFERRED items with refined triggers. Log the session.

### Key practices

1. **Explore before disposition.** Never re-triage from the description alone. Read the actual code. Descriptions from model reviews are hypotheses, not facts.

2. **Kill is the most valuable disposition.** Every killed item is a future agent session not wasted on a phantom problem. The anti-entropy value of removing noise from a task queue is high.

3. **Find the injection point.** "Metadata envelope for 96 scripts" is a 3-line change if there's a shared `finalize()` function. "Consolidate definitions across 15 files" is a mechanical migration. Scope estimates from model reviews assume per-file surgery — check for centralized injection points first.

4. **Bug-first ordering.** If exploration reveals an actual bug among the deferred items (not just cleanup), execute it first. It's the highest-impact item regardless of its original priority label.

5. **No scope-based deferrals when agents execute.** In agent-developed codebases, the only valid KEEP-DEFERRED reasons are: (a) missing external data, (b) needs human decision on semantics, (c) blocked by another item that isn't ready. "Too many files to touch" is not a blocker — it's a parallelizable task.

6. **Mechanical migrations → worktree agents.** When an EXECUTE item is "replace X with Y in N files" (e.g., consequence set consolidation), dispatch a worktree agent. The parent focuses on items requiring judgment.

### Expected yield

From observed runs:
- ~40% of deferred items are KILL (noise)
- ~50% are EXECUTE (trigger met, scope tractable)
- ~10% are genuine KEEP-DEFERRED (real blocker)
- Bug discovery rate: ~1 real bug per 10 deferred items (hidden among cleanup)

## Known Limitations

- **Dynamic dispatch**: Python's `getattr()`, `importlib.import_module()`, and CLI `entry_points` are invisible to Gemini's static analysis. Dead code findings for these patterns need manual verification.
- **Test coverage**: If the project has no tests, verification degrades to syntax/import checks only. The skill will note this in the report.
- **Monorepos**: Projects >500K tokens need splitting. Run per-package or per-directory.
- **Non-Python**: JavaScript and Rust support is functional but less tested. The verification matrix is most battle-tested for Python.

## Evaluation Scorecard

After each run, measure these to calibrate the pipeline:

| Metric | Target | Failure Threshold | What It Means |
|--------|--------|-------------------|---------------|
| Finding correctness | ≥60% verified correct | <40% | Model step not ROI-positive |
| Apply success rate | ≥80% retained (with tests) | <60% | Verification or triage is too weak |
| Zero unreviewed changes | 100% | Any violation | Constitutional breach |
| No test regression | Baseline pass → post-run pass | Any regression | Per-finding verification broken |
| Static error reduction | Errors_after ≤ Errors_before | Errors increase | Skill is introducing bugs |
| Time-to-value | ≤45 min (repos <150K LOC) | >2 hours | Human time dominates, ROI collapses |

Track these across runs to decide: is the pipeline improving the project, or just churning?
