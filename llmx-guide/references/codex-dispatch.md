# Codex CLI dispatch

Checked against installed `codex exec --help` on 2026-09-05. Use [model-guide](../../model-guide/SKILL.md) for model/effort choice and current Astra prompting. The removed `--full-auto` and `--cwd` flags are not valid invocation options.

## Pick the actual work boundary

```bash
# Analysis: read the workspace and return a report; the CLI captures final text.
codex exec -s read-only -C /path/to/project -o findings.md 'Review the named files. Return the findings as your final message.'

# Authorized edits: confine shell writes to the selected worktree.
codex exec -s workspace-write -C /path/to/worktree -c model_reasoning_effort=medium 'Implement the approved change and run its relevant checks.'

# Existing structured-output consumer.
codex exec -s read-only --output-schema schema.json 'Extract the requested records.'
```

`exec` is non-interactive. `-s` chooses shell sandbox scope; it does not itself authorize spending, MCP side effects or bypassing configured approvals. Use `-C`/`--cd` for the working root. Keep user/project execpolicy rules and approval controls unless the actual task explicitly authorizes an applicable change.

Omit `-m` to use the configured model; pass it only for an intended override. Astra accepts the full effort names supported by the actual runtime; do not use the old `med` abbreviation. Verify model/effort in the dispatch record when the model identity is part of an evaluation.

## Configuration and overhead

Direct dispatch loads the configured tools and discovered instructions. Tool availability and startup overhead depend on that configuration; old fixed server/token counts are historical. The CLI has `--ignore-user-config` for an explicitly isolated configuration, and `-c` overrides for selected settings. Inspect `--help` and the resulting dispatch plan instead of assuming a remembered bare profile works.

For llmx, `--mode agent --subscription` uses the caller workspace; isolated `--lite bare`/`--lite research` profiles are existing controlled routes. Run `llmx chat --dry-run ...` first and inspect transport, model, applied effort and tool profile. The research profile supplies the research MCP. `--ignore-rules` skips execpolicy `.rules` files; it does not remove project AGENTS.md. An isolated profile needs an appropriately isolated working directory.

Use the smallest tool set the task needs. Do not disable required research sources merely to reduce startup cost. Auth follows the selected Codex account/profile; an offline plan does not prove a successful authenticated model call.

## Outputs, concurrency and recovery

Choose one output contract: final text captured with `-o`, or a worker-written artifact with a short final pointer. In the latter case grant the necessary workspace write scope. A brief final message is valid if the promised artifact is complete. Inspect files and exit status before deciding that recovery is needed.

`-o` captures the last assistant text message, so the brief must request the actual final report when that is the chosen contract. `--ephemeral` means no persisted session files; avoid it when raw rollout recovery or audit history is required. It is not documented as deleting arbitrary workspace output.

Delegate independent lanes within available quota, provider limits and file ownership. Keep outputs distinct, use managed worktrees for overlapping code, and leave commits to the parent. Use completion notifications or the owning process wait mechanism; preserve the actual return status and stderr. A failed transport is not a failed capability.

## Blind versus repository-aware work

Codex can read its working tree. A prose information restriction alone does not make a run blind. For a blind lane, use a clean authorized directory with only its allowed material, or an appropriate text-only API route within the spending boundary. For repository-aware review, preserve access and say which evidence was available.

## Live Codex Desktop threads

The Codex tab of ChatGPT.app runs its own `codex app-server` over stdio. `pgrep -l codex` shows it as a child of ChatGPT.app. Its threads are ordinary Codex sessions:

- **Reading a thread.** Transcripts are in `~/.codex/sessions/YYYY/MM/DD/rollout-*-<thread uuid>.jsonl`.
  - Line 1's `payload` holds `originator: "Codex Desktop"`, `cwd` and the model.
  - A subagent's rollout carries `source.subagent.thread_spawn.parent_thread_id`, a nickname and an `agent_path`.
  - Messages between agents are encrypted (`gAAAA…`), but commands and their outputs are plain.
  - User-role entries that start with `<environment_context>` come from the app (the date rollover at local midnight, the subagent list), not from the user.
- **No supported programmatic send-now (changed 2026-11-22).** The IPC router (`~/.codex/ipc/ipc.sock`) that `codex-thread steer` used was dropped in that app build. The live channel is the app-tools socket `/tmp/codex-app-tools/<uuid>.sock`, which a peer authorizer (native `browser-use-peer-authorization.node`) restricts to the app's own code-signed process tree (reason codes `untrusted-process-ancestry`, `untrusted-code-signing-identity`). That boundary is deliberate — do not try to defeat it. `codex-thread steer|settings|unqueue` now exit 3 with this explanation. To reach a running turn immediately, click "Steer" on a queued message in the app, or type into the composer.
- **Queueing (the only programmatic route): `codex-thread queue <uuid> --message <text>`** wraps the app's bundled `codex queue` (binary `/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex`). It writes to `~/.codex/queue_1.sqlite`; the app submits the message when the thread's **current turn ends** — for a long turn that is many minutes away, and the message is invisible in the composer until then (verified 2026-11-25: a note queued behind a 30-min turn landed only at turn end).
  - `codex-thread status <uuid> [--grep TEXT]` shows the thread's queued rows, whether its turn is running, and whether text has reached the rollout. "Queued" is not "delivered": confirm with `status --grep`.
  - Before queueing, check the text is not already in the thread's user messages or `queued_items` (`status` shows the latter).
- **Do not resume a thread the app holds** with `codex resume` or `codex exec resume`. The source refuses a second writer ("thread already has an active writer"; test `queue_succeeds_when_another_server_owns_the_thread`).

Checked 2026-11-25 against ChatGPT.app's bundled codex-cli 0.171.0-alpha.13 (app build 26.1117.41037). `codex queue` returned rc 0, its row appeared in `queued_items`, and it was delivered when the thread's running turn ended. The old `codex-thread steer` route has no listener (the router socket was removed); `codex-thread steer|settings|unqueue` exit 3 with that note.

[Historical observations](codex-dispatch-history.md) retain the original overhead, output-loss, contention and isolation incidents. Re-probe live limits before using those old rates or model lists in a current decision.
