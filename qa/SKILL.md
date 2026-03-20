---
name: qa
description: QA methodology for web applications. Fix-first review with atomic commits, regression test generation, and before/after health scoring. Uses browse daemon for persistent browser interaction. Adapted from gstack's QA patterns with epistemic verification.
argument-hint: [URL or project to QA — e.g., "https://myapp.com", "~/Projects/publishing"]
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
effort: medium
---

# QA — Web Application Quality Assurance

## Prerequisites

- Browse daemon available: `$HOME/Projects/gstack-fork/browse/dist/browse status`
- If testing a local app: ensure dev server is running

```bash
B="$HOME/Projects/gstack-fork/browse/dist/browse"
TARGET="${ARGUMENTS}"
```

## Phase 1: Reconnaissance

```bash
$B goto "$TARGET"
$B snapshot -i -a    # interactive refs + annotated screenshot
$B links             # all navigation targets
$B forms             # all interactive elements
$B accessibility     # full a11y tree
```

Catalog:
- Page structure and navigation paths
- Interactive elements (forms, buttons, dropdowns)
- Dynamic content areas
- External resource dependencies

## Phase 2: Systematic Testing

### 2a. Visual/Layout
```bash
$B viewport 375x812 && $B screenshot mobile.png   # mobile
$B viewport 768x1024 && $B screenshot tablet.png   # tablet
$B viewport 1920x1080 && $B screenshot desktop.png # desktop
$B responsive screenshots/                          # all breakpoints at once
```

Check: broken layouts, overflow, hidden elements, z-index issues.

### 2b. Interaction Testing

For each interactive element from the snapshot:
```bash
$B snapshot -i
$B click @eN          # test each clickable
$B snapshot -D         # what changed? expected?
```

Check: broken links, form validation, error states, loading states.

### 2c. Form Testing

```bash
$B fill @eN ""              # empty submission
$B fill @eN "a"             # minimum input
$B fill @eN "<script>alert(1)</script>"  # XSS probe
$B fill @eN "'; DROP TABLE--"            # SQL injection probe
```

### 2d. Performance
```bash
$B perf                     # performance metrics
$B network                  # resource loading
$B console --errors         # JS errors
```

### 2e. Accessibility
```bash
$B accessibility            # full tree
$B js "document.querySelectorAll('img:not([alt])').length"  # missing alt text
$B js "document.querySelectorAll('a:not([href])').length"   # empty links
```

## Phase 3: Bug Classification

For each finding:

| Severity | Criteria | Action |
|----------|----------|--------|
| **CRITICAL** | Broken functionality, data loss, security | Fix immediately |
| **HIGH** | UX-breaking, accessibility failure | Fix in this session |
| **MEDIUM** | Visual inconsistency, minor UX issue | Fix if straightforward |
| **LOW** | Polish, optimization, nice-to-have | Report only |

### Verification Rule

**Every bug must be reproduced twice.** Run the interaction sequence again to confirm it's not a timing/race issue. Screenshot both runs.

**Cross-model verification (HIGH+ findings):** For bugs where the classification is ambiguous (is this a feature or a bug?), describe the behavior and expected behavior, then assess whether a reasonable user would consider this broken.

## Phase 4: Fix-First Review

For CRITICAL and HIGH bugs with clear fixes:

1. Identify the source file
2. Implement the fix
3. Verify via browse:
   ```bash
   $B reload
   $B snapshot -D    # verify fix shows in diff
   $B screenshot after-fix.png
   ```
4. Commit atomically:
   ```bash
   git add <file> && git commit -m "[qa] Fix <what> — <why>"
   ```

For MEDIUM bugs: batch and present to user for prioritization.
For ambiguous bugs: use AskUserQuestion with screenshot evidence.

## Phase 5: Health Score

Generate before/after metrics:

```
## QA Report: $TARGET

### Health Score
| Category | Before | After | Delta |
|----------|--------|-------|-------|
| JS Errors | N | M | -X |
| Broken Links | N | M | -X |
| Missing Alt Text | N | M | -X |
| Form Validation | N/M pass | N/M pass | +X |
| Mobile Layout | OK/BROKEN | OK | FIXED |

### Findings
| # | Severity | Description | Status |
|---|----------|-------------|--------|
| 1 | CRITICAL | ... | FIXED |
| 2 | HIGH | ... | FIXED |
| 3 | MEDIUM | ... | REPORTED |

### Evidence
Screenshots saved to: [path]
```

### Artifact Output

Write artifact for downstream pipeline consumption:

```bash
mkdir -p ~/.claude/artifacts/$(basename $PWD)
```

Write to `~/.claude/artifacts/$(basename $PWD)/qa-$(date +%Y-%m-%d).json`:
```json
{
  "skill": "qa",
  "project": "PROJECT",
  "date": "YYYY-MM-DD",
  "type": "qa-report",
  "content": {
    "target": "URL",
    "findings_total": N,
    "critical": C,
    "high": H,
    "fixed": F,
    "health_delta": "+X%"
  }
}
```

## Anti-Patterns

- **Testing without reproduction.** Every bug report needs 2 runs. Flaky != broken.
- **Fixing everything.** LOW findings are noise. Report and move on.
- **No evidence.** Every finding needs a screenshot or console output. "I saw a bug" is not a finding.
- **Skipping mobile.** 50%+ of web traffic is mobile. Always test at least one mobile viewport.
- **Security probes on production.** XSS/SQLi probes are for staging/dev only. Ask before probing production.

$ARGUMENTS
