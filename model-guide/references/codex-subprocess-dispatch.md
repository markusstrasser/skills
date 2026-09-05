# Codex as a research or implementation worker

Use the [canonical Codex dispatch guide](../../llmx-guide/references/codex-dispatch.md) for current flags, configuration, output capture and sandbox boundaries. Use [GPT guidance](PROMPTING_GPT.md) for Astra prompting. Both direct Codex and llmx's existing isolated research profile are supported routes; inspect a dry-run plan before choosing.

For a research lane, specify the bounded question, context already gathered, source-verification requirements and output contract. Single-quote shell prompts containing literal `$research`. Skills and MCPs come from the actual selected configuration; confirm required sources are available before a large fan-out.

A text-only reviewer can use `-s read-only` and `-o` for its final report. A worker writing a memo or implementing approved code needs `-s workspace-write` in the intended workspace. Give each lane its own output path; use managed worktrees for overlapping code changes. The parent owns review and commits.

Run a small end-to-end canary when transport, source access or artifact delivery is uncertain. Size it to that uncertainty, then inspect the result before scaling. Do not rerun an already-established canary for each routine lane. A bounded lane can retrieve and synthesize; split work when the budget or useful parallelism warrants it.

On completion, inspect the artifact and principal evidence. If output is incomplete, use the accessible raw rollout and files to recover or retry the bounded gap. Hidden reasoning is unavailable; a missing final report does not imply that all visible findings were lost. Preserve ownership and diagnose a blocking hook rather than disguising command text to evade it.

The [original dispatch notes](codex-subprocess-history.md) preserve the dated network, ownership, teardown and output incidents. Verify a benign-noise diagnosis against the actual process status and artifact; do not ignore an arbitrary error based on a historical example.
