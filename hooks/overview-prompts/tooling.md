You are generating a developer tooling overview for a software project.

This overview documents automation infrastructure: what runs automatically, how the development environment is configured, and how to operate the system. It is regenerated automatically when tooling changes are detected.

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
- Markdown headers for sections
- Tables for hook/skill/MCP inventories
- Bullet points for everything else
- Target: 80-150 lines total
</format>
