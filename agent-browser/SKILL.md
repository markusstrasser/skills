---
name: agent-browser
description: Headless/scripted browser automation from Bash (Vercel Labs CLI, Rust/CDP). Use for navigating pages, filling forms, clicking, screenshots, scraping JS-rendered pages, testing web apps, Electron apps, or any programmatic web interaction — especially in subagents, scouts, launchd jobs, and autonomous runs where claude-in-chrome MCP is unavailable. NOT for the operator's logged-in Chrome session (use claude-in-chrome) or static fetches (WebFetch/Firecrawl).
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*)
---

# agent-browser

Fast browser automation CLI for AI agents. Chrome/Chromium via CDP with accessibility-tree snapshots and compact `@eN` element refs (~200-400 tokens vs 3-5K for DOM dumps). Installed via brew (2026-07-20); headless by default, `--headed` for visible.

## Lane routing (ours, overrides the vendor's "prefer over everything")

| Need | Tool |
|---|---|
| Operator's logged-in Chrome, SSO sites, real tabs | claude-in-chrome MCP (interactive sessions only) |
| Static page fetch / crawl at scale | WebFetch / Firecrawl |
| Scripted or headless automation, JS-rendered pages, web-app verification, subagent/scout/launchd/autonomous contexts | **agent-browser** |

## Start here

This file is a discovery stub, not the usage guide. Before running any `agent-browser` command, load the workflow content from the CLI itself — it always matches the installed version:

```bash
agent-browser skills get core             # workflows, common patterns, troubleshooting
agent-browser skills get core --full      # + full command reference and templates
```

## Specialized skills (CLI-served)

```bash
agent-browser skills list                  # everything on the installed version
agent-browser skills get electron          # Electron desktop apps (VS Code, Slack, Discord, Figma, ...)
agent-browser skills get slack             # Slack workspace automation
agent-browser skills get dogfood           # Exploratory testing / QA / bug hunts
```

## Core loop

```bash
agent-browser open https://example.com
agent-browser snapshot -i        # @e1 [heading] … @e2 [link] …
agent-browser click @e2
agent-browser get url
agent-browser close
```

Also: `eval <js>` · `set viewport <w> <h>` / `set device <name>` · `network requests` · `console` · `react tree` / `vitals` (web-dev) · `--session <name>` isolation · `connect <port>` CDP-attach · `cookies set --curl <file>` for auth.

## Gotchas

- Bundled-Chrome download (`agent-browser install`) can time out; system-Chrome fallback works — don't block on it.
- Daemon persists between commands; `close --all` to reset every session.
- Observability dashboard on port 4848 (independent of sessions).
