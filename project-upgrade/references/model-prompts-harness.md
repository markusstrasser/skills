<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Phase 2H: Harness Mode Prompts

## Context Preparation

Instead of dumping the full codebase, split into two targeted chunks:

**Core modules** (~80-120K tokens): Shared infrastructure that everything imports.

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

Bundle core modules into `core-modules.md`. Bundle a sample of 10-15 leaf scripts (diverse categories) into `leaf-samples.md`. The leaf samples show how core modules are consumed.

## GPT Deep Queries (3 parallel, targeted angles)

Dispatch 3 GPT-5.4 queries in parallel, each with the same context but a different architectural angle. Use `--reasoning-effort high` and `--max-tokens 32768`.

### Prompt 1 — Enforcement (`prompt-enforcement.md`)

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

### Prompt 2 — Contracts (`prompt-contracts.md`)

```
You are a type system architect reviewing this codebase. Find the highest-ROI type
safety investments — places where adding types prevents the most downstream errors
per line of type annotation added.

Focus on:
1. Functions returning dict[str, Any] that have a stable shape -> TypedDict
2. Pydantic models that are .model_dump()'d immediately -> keep as model, use attribute access
3. String parameters that accept a closed set of values -> StrEnum or Literal
4. Protocols for duck-typed interfaces (multiple implementations, no shared base)
5. @overload for functions that return different types based on arguments

For each: file, function, current return type, proposed type, number of callers affected.
Return as JSON array with: id, category (typed_return|keep_model|str_enum|protocol|overload),
files, function_name, callers_affected, description, code_sketch.
```

### Prompt 3 — Unification (`prompt-unification.md`)

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

## Gemini Role in Harness Mode

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
