<!-- Reference file for llmx-guide skill. Loaded on demand. -->

# Direct Codex CLI Usage & Parallel Dispatch

## Direct Codex CLI Usage (without llmx)

For subagent dispatch and non-interactive tasks, call `codex exec` directly:

```bash
# Simple task
codex exec --full-auto "Review the error handling in scripts/*.py"

# With output capture
codex exec --full-auto -o findings.md "Audit this codebase for dead code"

# Specific working directory
codex exec --full-auto -C /path/to/project "List all API endpoints"

# Structured output
codex exec --full-auto --output-schema schema.json "Extract function signatures"
```

**Key facts (v0.123.0, verified with gpt-5.5 on 2026-04-24):**
- **Auth:** ChatGPT account (browser login). Subscription-tier models work: `gpt-5.5` (default), `gpt-5.4`, `gpt-5.3-codex`. `o3`, `gpt-4.1`, etc. are rejected.
- **Token overhead:** ~37K tokens per call from MCP server tool descriptions (9 servers). No flag to disable. Structural cost — fine for substantial tasks, wasteful for trivial queries.
- **MCP servers loaded:** context7, exa, research, meta-knowledge, brave-search, paper-search, perplexity, scite, codex_apps. Configured in `~/.codex/config.toml`.
- **`--ephemeral`:** Avoid — sandbox cleanup deletes file writes including `-o` output.
- **`--full-auto`:** Sandboxed auto-approval (workspace-write). Required for non-interactive use.
- **`--search`:** Only works in interactive mode, NOT in `exec`. Use MCP tools instead.
- **Default model:** Set in `~/.codex/config.toml` (`model = "gpt-5.5"`). Don't pass `--model` unless overriding.

**As Claude Code subagent:** Call via Bash tool. Set `timeout: 120000` or higher. Output is on stdout (last message repeated at end). Use `-o FILE` for file capture, but read/copy immediately — sandbox cleanup can delete.

## Codex Parallel Research Dispatch (from agent context)

Dispatch pattern for firing multiple Codex agents from Claude Code Bash tool:

```bash
# Parallel dispatch — background each, wait for all
codex exec --full-auto -o docs/audit/codex-topic-a.md \
  "Use exa and perplexity MCP tools for web search. [TASK]. \
   End with a COMPLETE markdown report as your final message. \
   Do NOT create any files." &

codex exec --full-auto -o docs/audit/codex-topic-b.md \
  "Use exa and perplexity MCP tools for web search. [TASK]. \
   End with a COMPLETE markdown report as your final message. \
   Do NOT create any files." &

wait
# Immediately git add — sandbox cleanup can delete files
git add docs/audit/codex-*.md
```

**Critical `-o` gotcha:** `-o FILE` captures the agent's **last text message only**. If the agent spends all turns on MCP tool calls and never produces a final text response, `-o` writes 0 bytes. The prompt **must** include: `"End with a COMPLETE markdown report as your final message. Do NOT create any files."` Without this, ~50% of agents produce empty output files.

**Brave contention:** When dispatching 4+ parallel agents, they all share Brave's 1 req/sec rate limit (Free plan). This causes cascading 429s. Fix: tell agents to `"Use exa for web search (NOT brave-search)"` when running 4+ in parallel. 1-2 parallel agents can use Brave fine.

**Perplexity quota:** Perplexity MCP can hit `401 insufficient_quota`. Tell agents: `"Use exa as primary search tool. Try perplexity as secondary — if it returns 401, continue with exa only."` Exa-only agents still produce good results (7-14KB reports observed).

**Practical limits (2026-03-26 tested):**
- 4 parallel agents: all MCP servers start successfully (36 server instances)
- 6 parallel agents: works but Perplexity quota depletes fast
- Output success rate: ~70% with the "COMPLETE report as final message" prompt instruction, ~30% without it
- Bash tool timeout: set `timeout: 600000` (10 min) — agents need 3-5 min each with MCP startup

**Diagnostics — `codex doctor`** (Codex 0.131+): runtime/auth/network/config check. Run it before debugging llmx codex-cli failures manually.

**Codex 0.134+ (2026-05-26):** `--profile` is the primary profile selector; read-only MCP servers get parallel tool calls. `--subscription` (or legacy `--lite bare`/`--lite research`) use the `~/.codex-{bare,research}` profile dirs — after a Codex upgrade, verify nothing routes through unexpected user-config plugins. Don't hand-edit `~/.codex-*/config.toml`; codex rewrites it on launch.

## Codex Inherits the Caller's CWD — Blind/Isolated Dispatch Footgun

`llmx -p codex-cli` hands the caller's CWD to the codex subprocess (`cli_backends.py` "Actual cwd
handed to the CLI subprocess"), and codex has READ access to that tree by default. A prompt-level
information diet does NOT hold: the model explores the repo and absorbs context you withheld.

Evidence (2026-06-12, hutter): a "map-blind" brainstorm arm dispatched from the project root
reproduced same-day ledger specifics it was never given — exact probe values (500k→250k), a
same-day measurement verdict ("LUT slow/null"), and internal key notation (`{1}`) — silently
voiding the independent-convergence design.

For genuinely blind / context-isolated codex dispatch:
- `cd` to a clean directory first (e.g. `mkdir -p /tmp/blind-$$ && cd /tmp/blind-$$`), passing
  context ONLY via `-f` files copied there; or
- use the API transport (`-m gpt-5.5` direct, no `-p codex-cli`) — no filesystem at all; or
- `--subscription` (no tools) when training-knowledge-only is the point.

Repo access is a FEATURE for map-aware/audit dispatches — make the choice explicit per arm, and
state in the output memo which arms had filesystem access.
