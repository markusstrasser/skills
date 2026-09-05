<!-- Reference for research-ops. Loaded on demand. -->
# Prompt Construction

## Choose a bounded question

Useful audit targets include wiring, drift, completeness, downstream impact,
hygiene, integration, and correctness against a specification or source paper.
Name the concrete property to check. Delegate independent work when it saves
time or improves quality; keep an already-resolved or trivial check local.

## State the dispatch contract

Tailor the prompt to the task, using specific starting paths and relevant callers:

```text
Task: [concrete question and authorized scope]
Evidence: [starting files/sources and relationships to trace]
Checks: [verifiable properties and useful finding categories]
Resources: [actual time/turn/cost/tool limits, if set]
Ownership: [read-only, or exact edit paths and commit responsibility]
Output: [final report captured by the CLI, or an authorized artifact path]
Cite file:line or primary sources for findings; separate evidence from inference.
You share the workspace with peers. Preserve their work and stay within ownership.
```

Choose the output mode before dispatch. A read-only lane can return its complete
report as final text for CLI `-o` capture. A worker-written artifact requires the
appropriate write scope and a specific path. See [Codex CLI dispatch](../../llmx-guide/references/codex-dispatch.md)
for current invocation, sandbox, tool availability, and recovery details.

## Make the work checkable

- "Read X and Y, compare field Z" — grounded comparison.
- "For each item in X, verify it exists in Y" — completeness.
- "Trace data from A through B to C" — wiring and caller behavior.
- "Count/rank/compute using this definition" — a reproducible measurement.

"Investigate X", "research best practices", and "check everything" need a
concrete question, evidence scope, and completion criterion. Web research is
possible when the configured tools permit it. An audit-only lane reports findings;
editing requires an authorized edit contract.

[Historical prompt](../../research/references/dispatch-reference-history.md#prompt-construction)
preserves the earlier model-specific advice and capability claims.
