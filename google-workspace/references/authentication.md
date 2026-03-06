# Google Workspace Authentication

Multiple auth workflows for different environments.

## Development (Interactive)

```bash
gws auth setup    # One-time: creates project, enables APIs
gws auth login    # OAuth flow with browser
```

Requires `gcloud` CLI for automated setup.

## Headless/CI (Service Account)

```bash
export GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE=/path/to/service-account.json
# Optional: domain-wide delegation
export GOOGLE_WORKSPACE_CLI_IMPERSONATED_USER=admin@example.com
gws drive files list
```

## Token Export (Agent Machines)

```bash
# On authenticated machine:
gws auth export --unmasked > credentials.json

# On agent machine:
export GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE=/path/to/credentials.json
```

## Multi-Account

```bash
gws auth login --account work@corp.com
gws auth login --account personal@gmail.com
gws auth list
gws auth default work@corp.com
gws --account personal@gmail.com drive files list
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `GOOGLE_WORKSPACE_CLI_TOKEN` | Direct access token |
| `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` | Service account or OAuth credentials |
| `GOOGLE_WORKSPACE_CLI_IMPERSONATED_USER` | Domain-wide delegation target |
| `GOOGLE_WORKSPACE_CLI_ACCOUNT` | Default account override |

## Security

- Credentials encrypted at rest (AES-256-GCM) via OS keyring
- Service account keys: store in CI secrets only
- Unverified apps limited to ~25 scopes; select specific services: `gws auth login -s drive,sheets`
