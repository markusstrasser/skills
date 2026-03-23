---
name: trending-scout
description: Scan for new agent/AI developments across vendors and the ecosystem, filtered against what we already know. Use when the user asks about new developments, trending repos, vendor updates, "what's new in AI agents", "check for updates", "any new tools/frameworks", weekly landscape scans, or anything about recent agent ecosystem changes. Also use proactively when starting research or planning sessions that could benefit from awareness of recent developments.
argument-hint: '[vendor focus or topic, e.g. "anthropic", "mcp servers", "all"]'
effort: medium
user-invocable: true
---

# Trending Scout

Scan for genuinely new agent/AI developments, filtered against the known landscape. The goal: surface what's changed since last check, not rehash what's already in research memos.

## Core Principle

**Knowledge-diff, not news aggregation.** Every finding must answer: "What does this change about what we know or how we build?" Repos with 50K stars that don't affect our architecture are less interesting than a 200-star tool that solves a problem we have.

**Dev sources only.** Prioritize: API docs, dev docs, changelogs, release notes, trending repos (code you can read), "awesome-X" / "best of" lists. Deprioritize: tech journalism, announcement blog posts, hype pieces, product launches without code. The signal is in changelogs and READMEs, not TechCrunch.

## Input Handling

Accept optional focus:
- **No argument / "all"** — full scan across all categories
- **Vendor name** ("anthropic", "openai", "google") — vendor-focused scan
- **Topic** ("mcp", "frameworks", "benchmarks") — topic-focused scan
- **"weekly"** — full scan formatted for orchestrator pipeline output

## Phase 0: Establish Baseline

Before searching, load the known landscape so you can filter against it.

1. **Read the research index** — `.claude/rules/research-index.md` in meta (always auto-loaded if in meta). This tells you what topics have existing memos.

2. **Check the most recent trending-scout memo** — `research/trending-scout-*.md` in meta. This is the "last known state." Note dates and what was already evaluated.

3. **Check vendor-versions baseline** — run `uv run python3 scripts/vendor-versions.py` in meta for current SDK/CLI versions. This catches version bumps that searches might miss.

4. **Note the time window** — default is "since last scout memo date" or "past 7 days" if no prior memo exists.

## Phase 1: Multi-Source Parallel Scan

Dispatch parallel searches across sources and categories. Use subagents for parallelism when available (4+ independent search axes = always delegate).

### Search Matrix

| Category | Exa Query | Brave Query | Extras |
|----------|-----------|-------------|--------|
| **Anthropic** | "Anthropic Claude changelog" + date filter | "Claude Code release notes OR changelog" | WebFetch changelog + SDK releases (see Anthropic deep-check below) |
| **OpenAI** | "OpenAI Codex CLI changelog" + date filter | "OpenAI API changelog OR SDK release" | Check github.com/openai releases |
| **Google** | "Gemini CLI changelog release" + date filter | "Gemini API update OR google-genai SDK" | Check github.com/google-gemini releases |
| **Frameworks** | "AI agent framework" + date filter | "agent framework release 2026" | Check github trending |
| **MCP** | "MCP server model context protocol" + date filter | "new MCP server" | Check github.com/modelcontextprotocol |
| **Repos/Lists** | "awesome AI agents" + date filter | "trending AI repos github" | GitHub trending via Exa site filter |
| **Tools** | "AI coding tool SDK" + date filter | "cursor OR windsurf OR coding agent SDK changelog" | — |

### Anthropic Deep-Check (when focus is "anthropic" or "all")

This is the highest-signal category for our infrastructure. Don't just keyword-search — hit these sources directly:

1. **Claude Code changelog** — `WebFetch` the official changelog at `code.claude.com/docs/en/changelog`. Compare version numbers against `vendor-versions.py` output. Focus on: new hook events, new frontmatter fields, new CLI flags, SDK changes.

2. **Agent SDK releases** — Check `github.com/anthropics/claude-agent-sdk-typescript/releases` and `github.com/anthropics/claude-agent-sdk-python/releases` via Exa site-filtered search. Note new `query()` options, hook input fields, tool changes.

3. **Cookbook new patterns** — `web_search_advanced_exa` with `includeDomains: ["platform.claude.com"]` and date filter. Look for new notebook patterns (agent architectures, MCP patterns, tool use patterns).

4. **GitHub issues for features we track** — Search `github.com/anthropics/claude-code/issues` for issues we're watching (tool output compression #32105, Agent Teams stabilization). Check if closed/merged.

5. **Compare against deferred items** — Read `research/claude-code-native-features-deferred.md` in meta. Check if any "trigger to revisit" conditions are now met.

**Output for Anthropic category:** Version delta (old → new), new features categorized as (adopt now / evaluate / defer), and update to deferred-items memo if triggers are met.

### Source-Specific Techniques

**Exa** (primary — semantic search, good for discovering things you wouldn't keyword-match):
```
web_search_advanced_exa:
  query: "<category query>"
  numResults: 10
  startPublishedDate: "<window_start in YYYY-MM-DD>"
  type: "auto"
```

**Brave** (secondary — independent index, good for triangulation):
```
brave_web_search:
  query: "<category query>"
  count: 10
  freshness: "pw"  # past week
```

**arxiv** (for research papers):
```
search_arxiv:
  query: "AI agent <topic>"
  max_results: 5
```

**GitHub trending** (for repos — use Exa with site filter):
```
web_search_advanced_exa:
  query: "AI agent tool"
  numResults: 10
  includeDomains: ["github.com"]
  startPublishedDate: "<window_start>"
```

### Parallel Dispatch Pattern

When subagents are available, dispatch one per vendor category:
- Agent 1: Anthropic (Exa + Brave + anthropic.com)
- Agent 2: OpenAI (Exa + Brave)
- Agent 3: Google (Exa + Brave)
- Agent 4: Ecosystem (frameworks + MCP + tools via Exa + Brave + GitHub)
- Agent 5: Research papers (arxiv + S2)

Each agent returns: `[{title, url, date, one_line_summary, why_relevant}]`

When running without subagents, execute searches sequentially but batch by source (all Exa queries together, then all Brave queries).

## Phase 2: Deduplicate and Filter

### Against Known Landscape

For each finding, check:
1. **Already in a research memo?** — grep research/ for the repo name, tool name, or key concept
2. **Already in CLAUDE.md or rules?** — might be documented as infrastructure we use
3. **Version bump of known tool?** — compare against vendor-versions output. Note the delta but don't treat as "new"

### Quality Filters

Drop findings that are:
- **Tech news / hype** — journalist write-ups, "revolutionary AI agent" blog posts, product launch PR. If there's no code, changelog, or API doc behind it, skip it.
- **Pre-alpha / concept only** — README-only repos, no releases
- **Irrelevant domain** — AI developments that don't touch agent infrastructure (e.g., image generation models, unless they have agent implications)
- **Duplicates** — same finding from multiple sources (keep the most informative source)
- **No code to read** — if you can't look at a repo, SDK, or API surface, it's not actionable

### Relevance Scoring

Rate each surviving finding on two axes:
- **Value**: How much does this change what we know or how we build? (1-5)
- **Maintenance**: What would it cost to adopt/integrate? (1-5, lower is better)

Keep findings where Value > Maintenance, or where Value = 5 regardless of maintenance.

## Phase 3: Output

### Memo Format

Write to `research/trending-scout-YYYY-MM-DD.md` in meta:

```markdown
# Trending Scout — YYYY-MM-DD

**Date:** YYYY-MM-DD
**Window:** [start] to [end]
**Sources:** Exa, Brave, arxiv, GitHub
**Findings:** N new, M version bumps, K already known (filtered)

---

## New Findings (ranked by value - maintenance)

### 1. [Name]

| Field | Content |
|-------|---------|
| Source | [URL] (stars if GitHub, citations if paper) |
| What it does | One paragraph |
| Why relevant | How this relates to our infrastructure |
| Integration path | What we'd do with this (adopt / extract pattern / watch / ignore) |
| Current overlap | What we already have that's similar |
| Maintenance cost | Ongoing drag if adopted |
| Verdict | **Adopt** / **Extract pattern** / **Watch** / **Ignore** |

### 2. ...

## Version Bumps

| Tool | Previous | Current | Notable Changes |
|------|----------|---------|-----------------|
| ... | ... | ... | ... |

## Already Known (filtered out)

Brief list of things found in search that we already track — confirms coverage, no action needed.

## Search Log

What was searched, what returned useful results, what didn't. Helps calibrate future scans.
```

### Pipeline Output

When invoked as `--weekly` or via orchestrator, also:
1. Update the research index in `.claude/rules/research-index.md` if new memo warrants a permanent entry
2. Commit the memo: `[research] Trending scout — N new findings, window YYYY-MM-DD to YYYY-MM-DD`

## Orchestrator Integration

This skill is designed to run as a weekly orchestrator pipeline. The pipeline template:

```json
{
  "name": "trending-scout",
  "schedule": "weekly",
  "steps": [
    {
      "type": "prompt",
      "project": "meta",
      "prompt": "/trending-scout weekly"
    }
  ]
}
```

## Edge Cases

- **No new findings**: Write the memo anyway — "no new findings" is a valid data point that confirms the landscape is stable. List what was searched.
- **Overwhelming volume**: Cap at 10 findings per scan. Rank aggressively. Link to sources for the rest.
- **Stale baseline**: If no prior trending-scout memo exists, the first run is a broader landscape scan. Subsequent runs are diffs.
- **Rate limits**: If Exa or Brave rate-limits mid-scan, note which categories were incomplete in the search log.
