<!-- Reference file for data-acquisition skill. Loaded on demand. -->

# API Keys Location

All keys live in `.env.local` at project root (gitignored):

```bash
SCRAPFLY_KEY=scp-live-...        # Same key works across projects
FIRECRAWL_API_KEY=fc-...         # Also available as MCP (firecrawl-mcp)
BROWSERBASE_API_KEY=bb_live_...
BROWSERBASE_PROJECT_ID=...
```

## Load Pattern

```python
from pathlib import Path
env = Path(__file__).resolve().parents[1] / ".env.local"
for line in env.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
```
