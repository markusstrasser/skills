---
name: data-acquisition
description: Web scraping and data download toolkit — Scrapfly, Browserbase, curl_cffi, claude-in-chrome, Playwright. Covers which tool for which situation, API keys, fallback chains, authenticated session approaches, and what doesn't work on macOS. Use when downloading data, scraping websites, or automating browser interactions.
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

4. Need to render JavaScript?
   → Scrapfly with render_js=True
   → Browserbase (full cloud Chromium)
   → Playwright local — only if site doesn't block automation

5. Need to interact (click, fill forms, navigate)?
   → claude-in-chrome for authenticated sites
   → Browserbase for non-authenticated complex flows
   → Playwright local for simple non-protected sites

6. Stuck after 2-3 attempts?
   → STOP. Tell the user what you tried and what failed.
   → Don't build increasingly elaborate workarounds.
   → The blocker might be access-tier (membership, license), not technical.
```

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

**What:** Paid API that handles Cloudflare, renders JS, rotates proxies. Last resort for direct downloads when curl_cffi fails.

**Key:** `SCRAPFLY_KEY` in `.env.local` (same key across projects)

**When:** SSL failures + Cloudflare + bot detection that curl_cffi can't beat. Also good for JS-rendered content.

```python
from scrapfly import ScrapflyClient, ScrapeConfig
import os

key = os.environ.get("SCRAPFLY_KEY", "")
# Or load from .env.local:
# for line in open(".env.local"):
#     if line.startswith("SCRAPFLY_KEY="): key = line.split("=",1)[1].strip()

client = ScrapflyClient(key=key)

# Basic scrape
result = client.scrape(ScrapeConfig(url=url, asp=True, country="us"))

# With JS rendering
result = client.scrape(ScrapeConfig(url=url, asp=True, render_js=True, country="us"))

# Content is in result.content (str or bytes)
```

**Install:** `uv add scrapfly-sdk`

**Cost:** ~$0.001-0.01 per request depending on features. `asp=True` (anti-scraping protection) costs more.

### 3. Browserbase — Cloud Browser

**What:** Full cloud Chromium browser controlled via Playwright CDP. Good for complex JS sites that need real browser behavior.

**Keys:** `BROWSERBASE_API_KEY` and `BROWSERBASE_PROJECT_ID` in `.env.local`

**When:** Complex multi-step flows on non-authenticated sites. NOT for SSO/Google-login sites (Google blocks cloud browsers).

```python
from playwright.sync_api import sync_playwright
import os, json, urllib.request

# Create session
data = json.dumps({"projectId": os.environ["BROWSERBASE_PROJECT_ID"]}).encode()
req = urllib.request.Request(
    "https://api.browserbase.com/v1/sessions",
    data=data,
    headers={
        "x-bb-api-key": os.environ["BROWSERBASE_API_KEY"],
        "Content-Type": "application/json",
    },
    method="POST",
)
session = json.loads(urllib.request.urlopen(req).read())

# Connect via Playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(
        f"wss://connect.browserbase.com?apiKey={os.environ['BROWSERBASE_API_KEY']}&sessionId={session['id']}"
    )
    page = browser.contexts[0].pages[0]
    page.goto("https://example.com")
    # ... interact ...
    browser.close()
```

**Install:** `uv add playwright && playwright install chromium`

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

### 7. Playwright (local) — Headless Browser

**When:** Simple sites without bot detection. Rendering JS locally. Testing.

**Gotchas on macOS:**
- Chrome `--remote-debugging-port=9222` does NOT work — macOS App Sandbox blocks it
- Persistent context with Chrome profile copies cookies but NOT server-side sessions
- Use Playwright's own Chromium, not system Chrome, for automation

### 8. Plain requests/curl — Always Try First

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
