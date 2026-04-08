<!-- Reference file for data-acquisition skill. Loaded on demand. -->

# Firecrawl — Scrape, Crawl, Extract (MCP or API)

**What:** API that scrapes pages into clean markdown and extracts structured JSON via LLM. Also crawls entire sites and maps URL structures.

**Key:** `FIRECRAWL_API_KEY` in `.env.local` (starts with `fc-`). MCP server: `firecrawl-mcp` (npx).

**When:** You need structured data from a page (not just raw HTML). Pass a JSON schema, get typed output. Also good for site-wide crawl/discovery.

## Unique Strengths (things other tools don't do)

- **Structured extraction** — define a JSON schema, Firecrawl returns typed data. "Get all download links and file sizes from this page" in one call.
- **Site crawl** — recursively follow links across a domain, get markdown for each page
- **Site map** — discover all URLs on a domain without scraping content (good for finding download pages)
- **Batch scrape** — many URLs in one call with the same schema

## MCP Tools

```
firecrawl_scrape    → single page to markdown/JSON
firecrawl_crawl     → recursive site crawl
firecrawl_extract   → structured extraction with schema + prompt
firecrawl_map       → discover URLs on a domain
firecrawl_search    → search + scrape in one call
```

## Python (direct API)

```python
from firecrawl import Firecrawl

fc = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])

# Clean markdown from a page
result = fc.scrape(url="https://example.com/datasets")
print(result.data["markdown"])

# Structured extraction with schema
schema = {
    "type": "object",
    "properties": {
        "datasets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "url": {"type": "string"},
                    "size": {"type": "string"}
                }
            }
        }
    }
}
result = fc.extract(
    urls=["https://example.com/datasets"],
    prompt="Extract all dataset names, download URLs, and file sizes",
    schema=schema,
)
```

**Install:** `uv add firecrawl` or use MCP (`npx -y firecrawl-mcp`)

**Limitations:** No auth/cookies (use claude-in-chrome for login-gated sites). Anti-bot handling weaker than Scrapfly's `asp=True`. Costs per scrape.
