<!-- Reference file for dispatch-research skill. Loaded on demand. -->
# Codex Dispatch Mechanics

## Dispatch execution

```bash
mkdir -p docs/audit  # or wherever findings should go

# Parallel dispatch (max 4 when MCPs are needed)
codex exec --model gpt-5.4 --full-auto \
  -o docs/audit/codex-{slug}.md \
  "You are auditing a codebase. Read files at their full paths. \
   Cite file:line for findings. \
   Do NOT create any files or write any templates. Just read code and analyze. \
   BUDGET: Read at most 5 files. After that, STOP and synthesize. \
   Spend 70% of effort reading, 30% writing your report. \
   A partial report is infinitely better than no report. \
   Your final text message will be captured automatically. \
   End with a COMPLETE markdown report of all findings. \
   TASK: [prompt]" &

codex exec --model gpt-5.4 --full-auto \
  -o docs/audit/codex-{slug}.md \
  "..." &

wait

# IMMEDIATELY copy -o output after agents finish (sandbox cleanup can delete them)
for f in docs/audit/codex-*.md; do
  [ -f "$f" ] && cp "$f" "$f.bak"
done
```

## Key flags

- `exec` — non-interactive mode (not the interactive `codex` command)
- `--full-auto` — sandboxed auto-approval (replaces old `--approval-mode full-auto`)
- **Do NOT use `--ephemeral`** — sandbox cleanup deletes file writes made during execution, including `-o` output. Without `--ephemeral`, session is persisted but files survive. Cost: ~100KB per session in `~/.codex/sessions/`.
- `-o FILE` — captures last agent *text* message to file. **Caveats:**
  - If the agent spends all turns on tool calls and never produces a final text response, `-o` writes nothing. Always include in prompt: "End with a markdown summary of all findings."
  - **Files written by agents inside the sandbox may be cleaned up on agent exit.** The `-o` output file itself can also be deleted by sandbox cleanup if `--ephemeral` is used. Always `git add` or `cp` output files immediately after agents complete.
  - If `-o` files are empty or missing after agent completion, check `~/.codex/sessions/` for the session — but note that reasoning payloads are encrypted and findings are NOT recoverable from logs.
- `--search` — **only works in interactive mode, NOT in `exec`**. Use MCP tools instead.

## MCP tools

Codex shares the global MCP config (`~/.codex/config.toml`). 9 configured MCPs (context7, exa, research, meta-knowledge, brave-search, paper-search, perplexity, scite, codex_apps) are available to `exec` agents automatically. Each contributes to the ~37K token overhead.

## MCP contention

Max 4 parallel Codex agents when MCPs are needed. Each agent starts its own MCP server instances (9 servers x N agents). 5+ concurrent agents can overwhelm the system (132+ simultaneous MCP startups observed).

## S2 API outages

Semantic Scholar returns 403 periodically. Tell agents to fall back to `backend="openalex"` for `search_papers` if S2 fails. Or instruct agents to use `exa` web search as a paper-discovery fallback.

## Output location

Tell agents to write markdown findings to the **repo** (`docs/audit/`), NOT `/tmp`. macOS cleans up `/tmp` between sessions. If you dispatch through `meta/scripts/codex_dispatch.py`, raw stdout/stderr now default to `docs/archive/audit-logs/<run>/` whenever `--output-dir` is under `docs/audit/`. If you keep extra sweep logs yourself, put them there too, not active `docs/audit/`. After agents complete, immediately `git add` the markdown outputs before they can be cleaned up.

## Fallback

If Codex isn't installed, write prompts to `.claude/research-dispatch.md` as numbered prompts the user can copy-paste or route to another model.
