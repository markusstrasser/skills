---
name: google-workspace
description: Automate Google Workspace via gws CLI — Drive uploads, Sheets logging, Gmail notifications, Calendar scheduling. Use when automating Workspace workflows, writing session logs to spreadsheets, uploading artifacts to Drive, or sending pipeline alerts. NOT for general API usage (use raw HTTP), non-Google services, or interactive human workflows.
user-invocable: true
argument-hint: [operation — e.g., "log metrics to sheet", "upload file", "send notification"]
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
effort: low
---

# Google Workspace Skill

One CLI (`gws`) for all Workspace APIs with structured JSON output designed for AI agents.

## Prerequisites ← Procedural

```bash
# First time only
npm install -g @googleworkspace/cli
gws auth setup   # creates Cloud project, enables APIs
gws auth login   # OAuth flow

# Verify
gws --version
```

For headless/CI: see [references/authentication.md](references/authentication.md).

## Core Patterns ← Template

### Drive: Upload & Search

```bash
# Upload file
gws drive files create --json '{"name": "report.pdf"}' --upload ./report.pdf

# List recent
gws drive files list --params '{"pageSize": 10}'

# Search
jq -n '{q: "name contains '\''Q1'\''"}' | xargs -I {} gws drive files list --params {}
```

### Sheets: Append Rows

```bash
# Create
gws sheets spreadsheets create --json '{"properties": {"title": "Session Log"}}'

# Append (single quotes for ! to avoid bash history expansion)
gws sheets spreadsheets values append \
  --params '{"spreadsheetId": "ID", "range": "Sheet1!A1", "valueInputOption": "USER_ENTERED"}' \
  --json '{"values": [["2026-03-05", "pipeline", "success"]]}'
```

### Gmail: Send Notification

```bash
# Encode and send
msg=$(echo -e "Subject: Alert\n\nPipeline failed." | base64 -w 0)
gws gmail users messages send --params '{"userId": "me"}' --json "{\"raw\": \"$msg\"}"
```

### Calendar: Block Time

```bash
gws calendar events insert --params '{"calendarId": "primary"}' \
  --json '{"summary": "Focus Block", "start": {"dateTime": "2026-03-06T10:00:00-08:00"}, "end": {"dateTime": "2026-03-06T11:00:00-08:00"}}'
```

## MCP Server ← Procedural

Expose as native tools in `.mcp.json`:

```json
{
  "mcpServers": {
    "gws": {
      "command": "gws",
      "args": ["mcp", "-s", "drive,sheets,gmail"]
    }
  }
}
```

**Tool counts:** drive (~50), sheets (~20), gmail (~30), calendar (~25). Stay under 50 total.

## Common Workflows ← Procedural

For detailed helper scripts, see [references/workflows.md](references/workflows.md).

Quick patterns:

```bash
# Stream paginated results to jq
gws drive files list --params '{"pageSize": 100}' --page-all | \
  jq -r '.files[] | select(.mimeType | contains("pdf")) | .name'

# Dry-run any command
gws drive files create --json '{"name": "test"}' --dry-run

# Multi-account
gws --account work@corp.com drive files list
```

## Guardrails ← Guardrail

- **Never** commit service account keys — use `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` env var
- **Always** quote `--params` JSON to prevent shell interpretation
- **Always** use single quotes for Sheet ranges (`'Sheet1!A1'`) to avoid `!` history expansion
- **Check** API is enabled if 403: `gws auth setup` or enable in Cloud Console

## Schema Introspection

```bash
gws schema drive.files.list      # request/response shape
gws schema sheets.spreadsheets.values.append
```

$ARGUMENTS
