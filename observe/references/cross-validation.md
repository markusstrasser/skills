<!-- Reference file for project-upgrade skill. Loaded on demand. -->

# Phase 3: Cross-Validation (Optional)

For high-stakes projects or `--thorough`, run a second-pass review through the
shared review surface instead of constructing a one-off GPT shell pipeline.

## Shared Contract

Inputs:

- the primary `findings.json`
- a bounded set of source files referenced by those findings
- the same packet/manifest discipline used in Phase 2

Outputs:

- a second-pass findings/disposition artifact
- `coverage.json` showing which axes ran and what context was dropped or kept

## Procedure

1. Count current findings in `findings.json`.
2. If the count is large or the project is high-stakes, build a focused packet
   containing:
   - the first-pass findings
   - only the source files cited by those findings
   - the concrete validation question for the second pass
3. Dispatch via the shared review contract with GPT-inclusive axes.
4. Compare the first-pass and second-pass artifacts:
   - confirmed findings
   - false positives
   - newly surfaced findings
5. Trust the second pass only after checking its `coverage.json` for axis gaps or
   packet truncation.

## What Not To Do

- do not pipe giant ad hoc markdown blobs into raw model commands
- do not bypass packet manifests for “just one more GPT check”
- do not consume raw transcripts when structured artifacts are available
