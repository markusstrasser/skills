<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Phase 5: Execution Loop

## Execution Order

For each APPLY finding, ordered by:
1. BROKEN_REFERENCE first (prevent crashes)
2. ERROR_SWALLOWED second (prevent silent failures)
3. IMPORT_ISSUE third (prevent import-time errors)
4. Everything else by severity (high -> low)

## Per-Finding Loop

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

## Verification Matrix

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

## Scaffolding Phase (REQUIRES SEPARATE APPROVAL)

**This is a second change-set.** Do NOT auto-execute scaffolding after fixes.
Present scaffolding proposals to the user as a separate disposition table. Each proposal must include quantified benefit.

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
