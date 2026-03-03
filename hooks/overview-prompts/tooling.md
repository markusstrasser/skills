You are generating a developer tooling overview for a software project.

This overview documents automation infrastructure: what runs automatically, how the development environment is configured, and how to operate the system. It is regenerated automatically when tooling changes are detected.

<accuracy>
Only describe what is concretely configured or implemented in the codebase below. Every hook, skill, script, or MCP server you mention must have a corresponding file or JSON entry in the codebase. Do not infer capabilities from prose, comments, README descriptions, or planning documents. If a config references an external script not present in context, note it as "referenced but not in scope" rather than describing what it might do.
</accuracy>

<what_to_cover>

## Claude Code integration

From `.claude/` directory:
- `settings.json`: hooks configured, what each guards, whether it blocks or advises
- `skills/`: agent skills available, 1-line each
- `rules/`: project-specific rules
- `agents/`: persistent agent configurations

## Automation

Scripts that run on schedule or are triggered by events:
- Cron jobs, launchd plists, CI/CD workflows
- Data refresh, health checks, staleness monitoring
- Build scripts, deployment scripts

## MCP configuration

If `.mcp.json` exists: what MCP servers are configured and what capabilities they provide.

## Project configuration

Notable settings in pyproject.toml, package.json, Makefile, or equivalent:
- Build/test commands
- Linting/formatting config
- Environment setup

</what_to_cover>

<what_to_skip>
- Application source code details (covered by source overview)
- Data files, analysis results, or artifacts
- API keys or secrets (never include these)
- Contents of node_modules/, .venv/, or dependency directories
- Plans, proposals, or discussion documents about future infrastructure — only document what is actually deployed and running
- CLAUDE.md content that describes aspirational or planned features
</what_to_skip>

<format>
Start the file with a greppable index block inside an HTML comment. Every subsection in the overview must have a corresponding index line. Prefix tags by type:

```
<!-- INDEX
[HOOK] name — what it guards, block/advise
[SKILL] name — one-line purpose
[MCP] server-name — capabilities
[AUTOMATION] name — trigger and purpose
[CONFIG] file — what it controls
-->
```

Tag types: `[HOOK]` for Claude Code hooks, `[SKILL]` for agent skills, `[MCP]` for MCP servers, `[AUTOMATION]` for scheduled/triggered jobs, `[CONFIG]` for notable config files. Use the tag that best fits.

After the index, use markdown subsections (### headings) whose names match the index entries so an agent can grep the index, then jump to the relevant heading.

- Tables for hook/skill/MCP inventories
- Bullet points for everything else
- Target: 80-150 lines total
</format>
