---
name: data-acquisition
description: Web scraping and data download toolkit — curl_cffi, Scrapfly, Firecrawl, Browserbase, claude-in-chrome, Exa, Playwright. Covers which tool for which situation, API keys, fallback chains, structured extraction, authenticated session approaches, and what doesn't work on macOS. Use when downloading data, scraping websites, or automating browser interactions.
user-invocable: true
argument-hint: '[URL, site name, or scraping problem]'
---

# Data Acquisition & Web Scraping Toolkit

## Tool Selection — Decision Tree

```
What are you downloading?

0. Quick probe — is this URL alive? What's on this page?
   → WebFetch (built-in, no setup) or Exa crawling
   → Use BEFORE building any pipeline

1. Direct file URL (CSV, ZIP, JSON, PDF)?
   → curl/requests first. If SSL fails → fallback chain (§Fallback Chain)
   → If Cloudflare/bot detection → curl_cffi or Scrapfly

2. Page behind login/SSO?
   → claude-in-chrome (user's live Chrome session) — ONLY reliable approach
   → STOP if you hit CAPTCHA, MFA, or login wall — ask the human

3. Page behind Cloudflare/anti-bot?
   → curl_cffi (TLS fingerprint impersonation) — try first, free
   → Scrapfly (asp=True) — paid fallback, handles JS rendering too
   → Browserbase — cloud browser, last resort for complex JS

4. Need structured data from a page (not just raw HTML)?
   → Firecrawl extract — pass JSON schema, get typed output
   → Firecrawl also good for site crawl/map (discover all URLs on a domain)

5. Need to render JavaScript?
   → Scrapfly with render_js=True
   → Browserbase (full cloud Chromium)
   → Playwright local — only if site doesn't block automation

6. Need to interact (click, fill forms, navigate)?
   → claude-in-chrome for authenticated sites
   → Browserbase for non-authenticated complex flows
   → Playwright local for simple non-protected sites

7. Stuck after 2-3 attempts?
   → STOP. Tell the user what you tried and what failed.
   → Don't build increasingly elaborate workarounds.
   → The blocker might be access-tier (membership, license), not technical.

8. Software artifacts (git repos, model weights, packages)?
   → git clone for repos. huggingface-cli download for gated models.
   → Check LICENSE/access gates FIRST — tell user if signup needed.
   → For pip/uv packages: uv add, not pip install.
```

## Operational Guardrails

**Working directory:** Always use absolute paths for download destinations. The Bash tool can reset cwd between calls. Use `curl -o /absolute/path/file.csv` not `curl -o data/file.csv`.

**Large downloads (>100MB):** Use `run_in_background: true` on the Bash tool call. Check progress with `ls -lh /path/` while doing other work.

**Bulk downloads:** 0.5s between requests to same domain (government sites are polite but not infinite). `sleep 0.5` between curl calls.

**FRED shortcut:** Many macro data series are mirrored on FRED. Direct CSV: `curl -sL "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SERIES_ID" -o series.csv`

## Available Tools

### 1. curl_cffi — TLS Fingerprint Impersonation

**What:** Drop-in `requests` replacement that impersonates real browser TLS fingerprints. Bypasses most bot detection without a headless browser.

**When:** Cloudflare, Akamai, or other TLS-fingerprint-based blocks. First thing to try before paying for Scrapfly.

**Install:** `uv add curl_cffi` or `uvx --with curl_cffi python3 script.py`

```python
from curl_cffi import requests

# Impersonate Chrome
resp = requests.get(url, impersonate="chrome")

# With headers
resp = requests.get(url, impersonate="chrome", headers={"Accept": "application/json"})

# Streaming large files
resp = requests.get(url, impersonate="chrome", stream=True)
with open(dest, "wb") as f:
    for chunk in resp.iter_content(chunk_size=1 << 20):
        f.write(chunk)
```

**Gotcha:** `curl_cffi` is a C library binding — won't work in pure-Python environments. Needs system-level install on some platforms.

### 2. Scrapfly — Anti-Bot API

Paid API for Cloudflare/JS-rendered/bot-detected sites. Key: `SCRAPFLY_KEY` in `.env.local`.
When: SSL failures + Cloudflare + bot detection that curl_cffi can't beat.
```python
from scrapfly import ScrapflyClient, ScrapeConfig
client = ScrapflyClient(os.environ.get("SCRAPFLY_KEY", ""))
result = client.scrape(ScrapeConfig(url=url, asp=True, render_js=True, country="us"))
# result.content has the HTML
```
Install: `uv add scrapfly-sdk`. Cost: ~$0.001-0.01/request, `asp=True` costs more.

### 3. Browserbase — Cloud Browser

Full cloud Chromium via Playwright CDP. Keys: `BROWSERBASE_API_KEY` + `BROWSERBASE_PROJECT_ID` in `.env.local`. Use for complex multi-step JS flows on non-authenticated sites. NOT for SSO/Google-login (Google blocks cloud browsers). Install: `uv add playwright && playwright install chromium`. See Browserbase docs for connection boilerplate.

### 4. claude-in-chrome — User's Live Chrome Session

**What:** MCP tools that control the user's actual Chrome browser via the Claude extension. Only way to use existing authenticated sessions (SSO, Google login, institutional access).

**When:** ANY site requiring login — ICPSR, NCES, bank portals, institutional archives. This is the ONLY approach that works for SSO-authenticated sessions.

**Workflow:**
```
1. mcp__claude-in-chrome__tabs_context_mcp  → get tab IDs (ALWAYS first)
2. mcp__claude-in-chrome__navigate          → go to URL
3. mcp__claude-in-chrome__find              → locate elements by description
4. mcp__claude-in-chrome__computer          → click, type, scroll, screenshot
5. mcp__claude-in-chrome__javascript_tool   → run JS in page context
6. mcp__claude-in-chrome__get_page_text     → extract page content
```

**Key patterns:**
- Wait after navigation: `computer(action="wait", duration=3)`
- Screenshot before clicking: `computer(action="screenshot")` to see what's there
- JS for data extraction: `javascript_tool` for reading DOM programmatically
- `find` for natural language element location: `find(query="download button")`

**When to ask the human for help:**
- **CAPTCHA or visual challenge** — you can't solve these. Ask the user to complete it, then resume.
- **MFA / 2FA prompt** — the user must enter their code. Wait for them.
- **Login required and user isn't logged in** — don't try to enter credentials. Tell the user to log in manually in Chrome, then continue.
- **Site asks for terms acceptance / license agreement** — the user must review and accept. Don't click "I agree" on their behalf for legal agreements.
- **Download leads to a file picker / OS dialog** — you can't interact with OS-level dialogs. Ask the user to handle it.
- **Repeated failures after 2-3 attempts** — stop, explain what you tried, ask for guidance.

**Downloads:**
- Clicked downloads go to the user's Chrome Downloads folder (usually `~/Downloads/`)
- After triggering a download, wait a few seconds, then check `~/Downloads/` for the new file
- Move/copy the file to the project data directory — don't leave it in Downloads
- Always verify: `file <downloaded>` to check type, `head -5` to check for HTML traps

**JS gotchas:**
- `await` in `javascript_tool` requires wrapping: `(async () => { ... })()`
- Return values containing URLs with query strings may show as `[BLOCKED: Cookie/query string data]` — simplify queries to avoid returning raw URLs
- Don't trigger `alert()`, `confirm()`, or `prompt()` — browser dialogs block the extension completely. Use `console.log()` + `read_console_messages` instead.

### 5. WebFetch — Quick Page Grabs (Claude Code built-in)

**What:** Claude Code's built-in `WebFetch` tool. Fetches a URL and returns content. No authentication, no JS rendering.

**When:** Quick checks — is this URL alive? What does this page say? Grab a JSON API response. Check if a download link works before building a full pipeline.

**Limitations:** No cookies/auth, no JS rendering, may be blocked by Cloudflare. Falls back gracefully — use it as a fast probe before reaching for heavier tools.

### 6. Exa — AI-Powered Search & Crawl (MCP)

**What:** Exa search API available via MCP. `web_search_exa` for finding URLs, `crawling_exa` for extracting page content cleanly.

**When:** Finding download URLs, discovering dataset pages, extracting structured content from known URLs. Good for content extraction without browser automation.

```
mcp__exa__web_search_exa       → find pages by topic
mcp__exa__crawling_exa         → extract clean content from a URL
mcp__exa__web_search_advanced_exa → filtered search (date, domain, etc.)
```

### 7. Firecrawl — Scrape, Crawl, Extract (MCP or API)

**What:** API that scrapes pages into clean markdown and extracts structured JSON via LLM. Also crawls entire sites and maps URL structures.

**Key:** `FIRECRAWL_API_KEY` in `.env.local` (starts with `fc-`). MCP server: `firecrawl-mcp` (npx).

**When:** You need structured data from a page (not just raw HTML). Pass a JSON schema, get typed output. Also good for site-wide crawl/discovery.

**Unique strengths (things other tools don't do):**
- **Structured extraction** — define a JSON schema, Firecrawl returns typed data. "Get all download links and file sizes from this page" in one call.
- **Site crawl** — recursively follow links across a domain, get markdown for each page
- **Site map** — discover all URLs on a domain without scraping content (good for finding download pages)
- **Batch scrape** — many URLs in one call with the same schema

**MCP tools:**
```
firecrawl_scrape    → single page to markdown/JSON
firecrawl_crawl     → recursive site crawl
firecrawl_extract   → structured extraction with schema + prompt
firecrawl_map       → discover URLs on a domain
firecrawl_search    → search + scrape in one call
```

**Python (direct API):**
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

### 8. Playwright (local) — Headless Browser

**When:** Simple sites without bot detection. Rendering JS locally. Testing.

**Gotchas on macOS:**
- Chrome `--remote-debugging-port=9222` does NOT work — macOS App Sandbox blocks it
- Persistent context with Chrome profile copies cookies but NOT server-side sessions
- Use Playwright's own Chromium, not system Chrome, for automation

### 9. Software & Model Artifacts

Not web scraping — but frequently needed during data-acquisition tasks.

**Git repos:** `git clone --depth 1 URL dest/` (shallow clone saves bandwidth)
**HuggingFace models:** `huggingface-cli download ORG/MODEL --local-dir dest/` (needs `huggingface-hub` installed, some models need `huggingface-cli login` for gated access)
**Python packages:** `uv add PACKAGE` (never bare `pip install`)
**Large files from GitHub Releases:** `curl -L -o file "https://github.com/.../releases/download/TAG/FILE"`

If a model/dataset requires license acceptance or signup, STOP and tell the user which ones need manual action.

### 10. Plain requests/curl — Always Try First

```python
import requests
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 ..."}, timeout=120, stream=True)
```

## The Fallback Chain (from intel/tools/download.py)

Ordered by cost — free strategies first:

```
1. requests.get()              — plain HTTP, works 80% of the time
2. requests.get(verify=False)  — SSL certificate issues
3. curl --insecure             — different TLS stack, catches edge cases
4. curl --tlsv1.2 --insecure  — force TLS 1.2 for old servers
5. Scrapfly (asp=True)         — paid, handles Cloudflare/anti-bot
```

Each strategy checks for **HTML traps** (got a landing page instead of data) and cleans up partial files on failure. Logs to `manifest.jsonl` for retry.

## Per-Domain Gotchas

| Domain | Issue | Solution |
|--------|-------|----------|
| `sec.gov` | Requires email in User-Agent, rate limit 10 req/sec | `User-Agent: project-name admin@email.com`, 0.1s delay |
| `bls.gov` | Blocks default UA | Use browser UA string |
| `data.cms.gov` | SPA redirects, HTML trap | Check Content-Type, verify file isn't HTML |
| `census.gov` | Rate limits | 0.5s delay between requests |
| `lda.senate.gov` | Aggressive rate limit | 2.5s delay |
| ICPSR (Keycloak SSO) | Cookies don't transfer, session is server-side | claude-in-chrome only |
| Google accounts | Blocks cloud browsers | claude-in-chrome only |

## What Does NOT Work (Don't Try)

| Approach | Failure mode |
|----------|-------------|
| **browser_cookie3 for SSO sites** | Extracts cookies from Chrome's cookie DB, but server-side sessions don't transfer. Site sees empty session. |
| **Chrome `--remote-debugging-port` on macOS** | App Sandbox prevents port from opening. `lsof` shows nothing. |
| **Playwright persistent context + Chrome profile** | Copies cookies/local storage but SSO session state lives server-side. Doesn't work for ICPSR, Google, etc. |
| **Browserbase + Google SSO** | Google fingerprints cloud browser environments and blocks login. |
| **Browserbase + Keycloak email login** | If account was created via Google SSO, there is no password. "Sign in with email" button exists but login fails. |

## API Keys Location

All keys live in `.env.local` at project root (gitignored):

```bash
SCRAPFLY_KEY=scp-live-...        # Same key works across projects
FIRECRAWL_API_KEY=fc-...         # Also available as MCP (firecrawl-mcp)
BROWSERBASE_API_KEY=bb_live_...
BROWSERBASE_PROJECT_ID=...
```

Load pattern:
```python
from pathlib import Path
env = Path(__file__).resolve().parents[1] / ".env.local"
for line in env.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
```

## Download Verification

Always verify downloads contain what you expect:

```bash
# Check file type
file downloaded.zip                      # should say "Zip archive data"

# Check zip contents for actual data (not just docs)
unzip -l downloaded.zip | grep -iE '\.(sav|dta|dat|csv|tsv|parquet|sas7bdat|xpt) '

# Check for HTML trap (got a login page instead of data)
head -5 downloaded.csv                   # should NOT start with <!DOCTYPE
python3 -c "open('f.zip','rb').read(4)" # should be PK\x03\x04 for zip

# Check file size is reasonable
ls -lh downloaded.zip                    # 70 MB zip is real; 21 KB is codebook-only
```

## Resumable Downloads

For large files (>100 MB), use resume-capable downloads:

```python
import os
from curl_cffi import requests

def download_resumable(url, dest):
    headers = {}
    mode = "wb"
    if os.path.exists(dest):
        size = os.path.getsize(dest)
        headers["Range"] = f"bytes={size}-"
        mode = "ab"

    resp = requests.get(url, impersonate="chrome", headers=headers, stream=True)
    if resp.status_code == 416:  # Range not satisfiable = already complete
        return

    with open(dest, mode) as f:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            f.write(chunk)
```

## Anti-Patterns

1. **Don't build Playwright automation for SSO sites.** Use claude-in-chrome.
2. **Don't retry a wall with fancier code.** If the blocker is access-tier (not technical), stop coding.
3. **Don't accumulate probe/download scripts.** Document the lesson, delete the script.
4. **Don't use `browser_cookie3` for anything beyond simple cookie-auth sites.** SSO breaks it.
5. **Don't pay for Scrapfly/Browserbase before trying curl_cffi.** Free first, paid last.
