<!-- Reference for research-ops. Loaded on demand. -->
# Verification Procedure

Check every reported finding against the relevant authoritative evidence before
calling it confirmed. An agent's confidence or model identity is not verification.

## Check the promised result

1. **Complete output:** inspect the requested artifact or captured final report.
   It must satisfy the dispatch contract and be readable and untruncated; no line
   minimum applies. A short final pointer to a complete artifact is valid.
2. **Real paths:** resolve cited paths, including symlinks. Search locates a path;
   inspect the actual file before deciding it exists, is absent, or is obsolete.
3. **Supported claims:** read the cited implementation and relevant callers or
   primary source. Confirm line references and the behavior being claimed.
4. **Accurate measurements:** independently reproduce counts or computations
   material to the finding, using the actual data slice and stated definition.
5. **Defensible classification:** distinguish a behavioral defect from a style
   preference; justify severity using the observed effect.

| Signal | Verification |
|---|---|
| Invented or obsolete path | Locate and resolve the actual path; inspect its contents and history. |
| Wrong count | Reproduce the count with the same scope and definition. |
| Allegedly missing behavior | Trace the actual implementation and callers. |
| Inflated severity | Check the consequence and downgrade or reject unsupported severity. |
| "Already fixed" claim | Git search/log locates a candidate change; inspect the current implementation and use a relevant probe when needed. A commit message alone does not prove the fix. |
| Wrong DOI | Resolve it and verify that paper identity and source content support the claim. |

For memo artifacts with paper citations, follow [paper evidence checks](../../research/references/paper-evidence.md#mechanical-citation-gate-for-memo-artifacts)
for the current mechanical gate, blocking/advisory distinction, and parser limits.
Identifier existence and venue do not establish that a paper supports the finding;
source inspection still supplies that check.

## Return the verified findings

Report confirmed findings, corrections, and rejected claims with reasons where
applicable. Use enough detail to make the result reviewable; do not pad an empty
or small audit to satisfy a length quota. Recover incomplete output according to
the [current dispatch contract](../../llmx-guide/references/codex-dispatch.md).

The [dated GPT-5.4 observations](../../research/references/dispatch-reference-history.md#verification-procedure)
preserve the original error-rate claims and 2026-03-18 session note. They are
historical samples, not a current model accuracy estimate.
