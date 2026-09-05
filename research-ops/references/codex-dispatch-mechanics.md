# Codex research dispatch mechanics

Use the [canonical Codex CLI guide](../../llmx-guide/references/codex-dispatch.md) for current flags and configuration. Use [research-worker guidance](../../model-guide/references/codex-subprocess-dispatch.md) for lane design and evidence verification.

For a read-only audit with final-text capture:

```bash
codex exec -s read-only -C /path/to/repo -o docs/audit/codex-topic.md \
  'Read the named files, check the stated properties, and cite exact evidence. Return the complete report as your final message. Keep the assigned scope.'
```

For a worker-written artifact, use workspace-write in the appropriate managed workspace and ask for the file path plus a concise verdict. Decide completeness from the artifact, not the length of the return message. Choose the model explicitly only when the lane requires an override; otherwise honor the configured model.

Parallelize independent lanes within the runtime/provider limits. Distinct output files and ownership are required; wait through the owning process/harness and inspect exit status, stderr and artifacts before integrating. Preserve raw rollouts when recovery or evaluation requires them. The parent reviews findings at their sources and commits exact owned paths.

A source/backend failure calls for a supported alternate source or transport with the same evidence contract. Report an unresolved access limitation; do not interpret it as absence of evidence. The old fixed file/turn quotas and unconditional recovery workflow are not defaults for every bounded lane.

The [historical dispatch notes](codex-dispatch-history.md) preserve earlier flags, contention observations and output-loss reports. Their model names and rates need current verification before reuse.
