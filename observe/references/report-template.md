<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Phase 6: Report Template

## Report Format

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

## MAINTAIN.md Integration

If `MAINTAIN.md` exists in the project root (project uses `/maintain`), **you must** also:
- Append to `## Log`: `YYYY-MM-DD | project-upgrade | N findings, M applied, D deferred | [commit range]`
- Append deferred findings (DEFER disposition) to `## Queue` with IDs continuing the M00N sequence
- Append applied fixes to `## Fixed`

This feeds results into the SWE quality lane so `/maintain` can track them.

## Save Baseline SHA (for diff-aware next run)

```bash
git rev-parse HEAD > "$PROJECT_ROOT/.project-upgrade/last-baseline.sha"
echo "Saved baseline SHA for next diff-aware run: $(cat $PROJECT_ROOT/.project-upgrade/last-baseline.sha | head -c 8)"
```
