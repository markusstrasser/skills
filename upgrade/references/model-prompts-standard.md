<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Phase 2: Standard Model Prompts

## Extract Project Context

Before writing prompts, extract a project brief from CLAUDE.md or README that gives models operating context. This prevents false positives from missing domain knowledge.

```bash
# Extract project context for model prompts
PROJECT_CONTEXT=""
if [ -f "CLAUDE.md" ]; then
  PROJECT_CONTEXT=$(awk '/^## Project Purpose/,/^## [^P]/{print}' CLAUDE.md | head -15)
fi
if [ -z "$PROJECT_CONTEXT" ] && [ -f "README.md" ]; then
  PROJECT_CONTEXT=$(head -20 README.md)
fi
# Also include recent git activity for "what was recently fixed" context
RECENT_COMMITS=$(git log --oneline -10)
# And ruff pre-scan results (what's already clean)
RUFF_PRESCAN=""
if [ "$LANG" = "python" ] && command -v ruff &>/dev/null; then
  RUFF_PRESCAN=$(ruff check . --select F821,F601,E741,F811,F841 --statistics 2>&1 | tail -5)
fi
```

Include `PROJECT_CONTEXT`, `RECENT_COMMITS`, and `RUFF_PRESCAN` in both model prompts.

## Dispatch Both Models in Parallel

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

## Gemini Prompt (pattern/architecture focus)

Write to `$UPGRADE_DIR/gemini-prompt.md`:

```
You are analyzing an entire codebase for CONCRETE, VERIFIABLE improvements. Not vague suggestions — specific issues with specific fixes.

PROJECT: $PROJECT_NAME
LANGUAGE: $LANG

## Project Context (read this before analyzing)
$PROJECT_CONTEXT

## Recently Fixed (do not re-report)
$RECENT_COMMITS

## Pre-scan (already clean on these categories)
$RUFF_PRESCAN

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
  "id": "F001",
  "category": "<one of the categories below>",
  "severity": "high|medium|low",
  "files": ["path/to/file.py"],
  "lines": "optional line range, e.g. 45-67",
  "description": "What is wrong, specifically",
  "fix": "Exact change to make — code-level, not hand-waving",
  "verification": "How to confirm the fix works (a command, a grep, a test)",
  "risk": "What could break if this fix is wrong"
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
```

## GPT Prompt (harness/type-safety/agent-DX focus)

Write to `$UPGRADE_DIR/gpt-prompt.md`:

```
You are a senior software architect specializing in developer tooling, type systems, and AI-assisted development. Analyze this codebase for improvements to its SWE harness, abstractions, and developer experience.

## Project Context (read this before analyzing)
$PROJECT_CONTEXT

## Recently Fixed (do not re-report)
$RECENT_COMMITS

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
```

## Synthesize: Convergence Analysis

After both models return, read both `gemini-findings.json` and `gpt-findings.json` and produce a convergence table:
- **Convergent findings** (both models flagged) -> highest confidence
- **Model-unique findings** -> verify against code before accepting
- **Contradictions** -> investigate, don't auto-resolve

Write synthesis to `$UPGRADE_DIR/synthesis.md`.
