<!-- Reference for research-ops. Loaded on demand. -->
# Paper-Reading Dispatch

Use for comparing a tool's implementation with its source papers.

## Establish the source

Treat a supplied DOI as a locator: resolve it and verify the title, authors, and
version against the paper being cited. Search by title/author when the identifier
is absent or does not match. Never invent a DOI or accept an agent's correction
without checking the paper's identity and content.

If a configured scholarly service fails, use an available source fallback such
as OpenAlex, PMC, or the publisher. Check the configured tool schema before using
backend options. Record the failed source and the fallback actually used; a
transport failure is not evidence that the paper does not exist.

## Bound the comparison

Size the lane from its actual resource budget, source availability, and comparison
complexity. Do not infer a universal turn limit or tools-per-agent quota from an
older session. Assign concrete implementations and checkable paper claims. Split
independent comparisons when useful, and preserve findings incrementally during
substantial work so a partial result can be inspected.

For each finding, retain the paper/version, relevant passage or location, code
file:line, observed mismatch, and any inference or uncertainty. Check substantive
source claims and severity rather than relying on a model-specific reputation.

## Preserve the output through the actual dispatch

Use [Codex CLI dispatch](../../llmx-guide/references/codex-dispatch.md) for current
model/tool routing, sandbox scope, completion handling, and recovery. A read-only
lane can return its complete final report for `-o`; a lane writing an artifact
needs an authorized writable path. Keep outputs distinct and owned.

Inspect completion status and the promised output before declaring it missing or
recovering it. Use available raw logs and artifacts for recovery. If the selected
runner actually tears down ephemeral storage, preserve its owned output before
that teardown. Do not stage files merely because a worker has emitted them, and
never sweep peer edits into a commit.

[Historical paper-audit notes](../../research/references/dispatch-reference-history.md#paper-reading-dispatch)
retain the 2026-03-18 DOI/S2 incidents, GPT-5.4 observations, earlier turn estimates,
and output-loss reports. Those reports do not establish current universal limits
or file-persistence behavior.
