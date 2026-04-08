<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Phase 4: Triage Procedures

## 4a. Automated Validity Gate (pre-triage)

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
        desc = f.get('description', '')
        for path in f.get('files', []):
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

## 4b. Per-Finding Review

For each finding:
1. **Check `_auto_status`** — Skip INVALID_PATH findings (auto-rejected). Flag NEEDS_CHECK for closer inspection.
2. **Verify against actual code** — Read the file, check if the issue exists. Models hallucinate file paths and function names.
3. **Check if already fixed** — `git log --oneline -5 -- <file>` to see recent changes
4. **Assess risk** — Will this change break other things?
5. **Cross-check against project context** — You have more context than the models. Before presenting the disposition table, check each finding against:
   - **Prior decisions** (vetoed-decisions.md, CLAUDE.md) — does the finding conflict with or question an existing decision? Note the conflict in the disposition table. The model may be right that the decision is outdated — surface it, don't auto-reject.
   - **Deliberate design choices** — is the "bug" actually intentional? Check comments in code, data-sources.md for documented exclusions. If intentional, note why.
   - **Runtime environment** — does your knowledge of how the project runs (uv, editable installs, symlinks) change the finding's validity?
   - **Dead code** — is the affected code actually used? Check git recency + grep for callers before investing.
   The goal is informed triage, not deference to existing docs. Prior decisions can be wrong or stale. But you should know about them before dispositing, so the user can make a deliberate call at the approval gate.

## 4b. Disposition Table Template

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

## 4c. Coverage Check

- Count: total findings, verified, applied, deferred, rejected
- If any finding has no disposition -> stop and fix
- Save to `$UPGRADE_DIR/triage.md`

## 4d. Present to User

Show the disposition table. Ask for go/no-go before execution.

**The user approves, modifies, or aborts at this point.**
