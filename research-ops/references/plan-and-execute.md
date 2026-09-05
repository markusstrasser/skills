<!-- Reference for research-ops. Loaded on demand. -->
# Plan and Execute

## Plan the authorized work

Use a plan sized to the findings. For a substantial change, record:

```markdown
# Audit Findings — Fix & Refactor Plan
**Session:** YYYY-MM-DD | **Project:** <name>
## Context
<What the audit found and what was verified>
## Changes
<For each finding: files, what changes, why, and relevant verification>
## Execution order
<Dependencies and any meaningful phases>
## Dispositions
<Every confirmed finding: implement, already resolved, or defer with a reason>
```

Prioritize bugs, then drift, then hygiene. Cite the verified finding for each fix,
state scope honestly, and include the commands or source checks that will verify
it. Do not silently select only the top findings; give each a disposition.

## Carry authorization through execution

An audit-and-fix request authorizes its reversible implementation; an approved
plan carries through its phases without another approval pause. Continue after
relevant validation. Phase count alone does not create a new checkpoint.

Honor explicit audit-only, plan-only, read-only, and no-commit instructions. If
an unresolved decision or an actual protected boundary requires user input,
first complete the already-authorized work needed for a concrete, reviewable
proposal. Do not require a special "full auto" phrase for authorized follow-through.

## Execute and verify

1. Read the target implementation and relevant callers before editing.
2. Make coherent fixes with one logical change per commit when commits belong to
   this lane. If the parent owns integration, hand off the changed files and leave
   commits to the parent.
3. Run checks that test the changed behavior and complete required project or
   evaluation contracts. Use a focused test, source comparison, or affected-script
   run as appropriate. Do not create implementation-mirroring tests for reversible,
   low-impact edits. Run a full suite when integration scope, a required gate, or
   an unresolved concern warrants it. Repeat or broaden only for new changes,
   failures, or unanswered concerns.
4. Verify each fix against the selected checks. Runtime shape failures need an
   actual runtime check; a prose edit need not inherit a script or full-suite run.
5. Include adjacent cleanup when it unblocks the work. Split a >100-line cleanup
   or a public API/contract change into its own logical change and describe it.
6. Delegate bounded independent work when it saves time or improves quality,
   with explicit ownership and an output contract.
7. When repairing a path, locate and inspect the real destination and structure;
   do not infer it from directory names.

## Preserve peer work

Inspect status before edits and handoff. Use managed worktrees for overlapping
code work. Keep outputs distinct and obey the caller's ownership boundaries.
Never stage or commit a peer's edits to make the checkout clean. When this lane
owns a commit, select only its changes; same-file mixed authorship requires hunk
selection. A parent-owned lane may finish with its edits uncommitted for integration.

## Closeout and existing logs

Verify the owned result, then report findings addressed, validation, changed paths,
commits if any, and explicit deferrals. Unrelated peer changes are not a closeout
failure. Follow the project's commit format and cite the audit finding.

If the project uses `MAINTAIN.md`, preserve its existing integration contract:
- Append to `## Log`: `YYYY-MM-DD | dispatch-research | N findings, M applied, D deferred | [commit range]`.
- Append deferred findings to `## Queue` with IDs continuing the M00N sequence.
- Append applied fixes to `## Fixed`.
- Use real commit references. When the parent owns commits, hand off the pending
  log details for that integration; never insert an `uncommitted` placeholder.

[Historical procedure](../../research/references/dispatch-reference-history.md#plan-and-execute)
preserves the original approval, test, path-recovery, and shared-checkout advice.
