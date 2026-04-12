# Flash Prompt Templates

Gemini Flash prompt templates for each axis that needs model classification.
Prepend the appropriate template to the combined context file before dispatch.

## Promoted Scripts Pattern Consistency

```
TASK: Analyze these pipeline scripts for pattern inconsistencies.
Focus on:
1. Import patterns — do they all use the same imports from modal_utils, pipeline_core, etc?
2. Stage function signatures — do they follow @stage decorator pattern consistently?
3. Error handling — init_stage/finalize_stage lifecycle consistency
4. Path construction — do they use Paths() class or ad-hoc f-strings?
5. JSON output — write_json_atomic vs json.dump
6. subprocess calls — run_cmd vs subprocess.run
7. Config loading — pipeline_config typed loaders vs ad-hoc json.load
8. Volume commit patterns — proper commit lifecycle

For each issue: filename, line concept, what's wrong, what it should be.
Be precise and terse. No preamble.
```

## IR Consistency

```
TASK: Analyze the Finding IR (Intermediate Representation) module for internal consistency.
Focus on:
1. Every payload type in finding_ir.py should have a corresponding adapter in finding_adapters.py or finding_adapters_pgx.py
2. Every adapter should be registered in the dispatch dict or called from load_all_evidence
3. finding_assembly.py should reference all assertion types from finding_ir.py
4. finding_policy.py should handle all domains from finding_ir.py
5. Look for orphan types (defined but never referenced outside their own module)
6. Look for phantom imports (imported from modules that don't define the imported name)
7. Look for string literals that should be enum values

For each issue: file, concept, what's wrong, what it should be.
Be precise. No preamble.
```

## Config Consistency

```
TASK: Check consistency across these config files.
Focus on:
1. database_versions.json — do entries use consistent field names? Any using size_gb vs size_mb?
2. trait_panels.json �� do descriptions match the gene/variant they're attached to? Any cross-contamination?
3. pipeline_config.py Pydantic models — do they match the JSON structures they load?
4. triage_thresholds.json — referenced correctly by pipeline_config.py?
5. multi_hit_syndromes.json — gene symbols valid? Evidence domains match finding_ir.py domains?
6. Any schema drift between config JSON and Pydantic models

Be precise and terse. No preamble.
```

## Cross-File Function Consistency

Use when the duplication axis finds diverged functions. Send the full function
bodies from each file.

```
TASK: These functions share the same name but have diverged across files.
For each function group:
1. What are the semantic differences between variants? (not just formatting)
2. Which variant is most complete/correct?
3. Can they be unified into one shared implementation?
4. Are the differences intentional (different contexts) or accidental (copy-paste drift)?

Be precise. No preamble.
```

## General Pattern Scan

Fallback for project-specific axes not covered above.

```
TASK: Scan these files for inconsistencies in the following patterns:
{DESCRIBE_PATTERNS_HERE}

For each inconsistency found:
- File and approximate location
- What the pattern should be (based on majority usage)
- What the file actually does
- Whether this is likely intentional or accidental

Be precise and terse. No preamble.
```
