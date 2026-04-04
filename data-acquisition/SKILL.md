---
name: data-acquisition
description: Web scraping and data download toolkit — curl_cffi, Scrapfly, Firecrawl, Browserbase, claude-in-chrome, Exa, Playwright. Covers which tool for which situation, API keys, fallback chains, structured extraction, authenticated session approaches, and what doesn't work on macOS. Use when downloading data, scraping websites, or automating browser interactions.
user-invocable: true
argument-hint: '[URL, site name, or scraping problem]'
effort: medium
---

# Data Acquisition & Web Scraping Toolkit

## Tool Selection — Decision Tree

```
What are you downloading?

0. Quick probe — is this URL alive? What's on this page?
   → WebFetch (built-in, no setup) or Exa crawling
   → Use BEFORE building any pipeline

1. Direct file URL (CSV, ZIP, JSON, PDF)?
   → curl/requests first. If SSL fails → fallback chain below
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

## Tool Quick Reference

Per-tool details, code examples, and setup in `references/`.

| Tool | When | Free? | Reference |
|------|------|-------|-----------|
| plain requests/curl | Default first attempt, works ~80% | Yes | [plain-requests.md](references/plain-requests.md) |
| curl_cffi | Cloudflare/TLS fingerprint blocks | Yes | [curl-cffi.md](references/curl-cffi.md) |
| Scrapfly | Anti-bot + JS rendering curl_cffi can't beat | Paid | [scrapfly.md](references/scrapfly.md) |
| Browserbase | Complex multi-step JS flows (not SSO) | Paid | [browserbase.md](references/browserbase.md) |
| claude-in-chrome | ANY login/SSO — only reliable approach | Free | [claude-in-chrome.md](references/claude-in-chrome.md) |
| WebFetch | Quick URL probe (built-in) | Free | [webfetch.md](references/webfetch.md) |
| Exa | Search + content extraction via MCP | Free | [exa.md](references/exa.md) |
| Firecrawl | Structured extraction, site crawl/map | Paid | [firecrawl.md](references/firecrawl.md) |
| Playwright | Local headless browser, simple sites | Free | [playwright.md](references/playwright.md) |
| Software artifacts | Git repos, HF models, packages | Free | [software-artifacts.md](references/software-artifacts.md) |

## The Fallback Chain

Ordered by cost — free strategies first:

```
1. requests.get()              — plain HTTP, works 80% of the time
2. requests.get(verify=False)  — SSL certificate issues
3. curl --insecure             — different TLS stack, catches edge cases
4. curl --tlsv1.2 --insecure  — force TLS 1.2 for old servers
5. Scrapfly (asp=True)         — paid, handles Cloudflare/anti-bot
```

Each strategy checks for **HTML traps** (got a landing page instead of data) and cleans up partial files on failure.

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

## API Keys

All keys in `.env.local` at project root (gitignored). Details + load pattern: [api-keys.md](references/api-keys.md)

## Download Verification & QA

Always verify downloads — HTML traps, truncated files, wrong schemas are common. Full verification checklist, resumable download pattern, and format-specific profiling: [download-verification.md](references/download-verification.md)

## Anti-Patterns

1. **Don't build Playwright automation for SSO sites.** Use claude-in-chrome.
2. **Don't retry a wall with fancier code.** If the blocker is access-tier (not technical), stop coding.
3. **Don't accumulate probe/download scripts.** Document the lesson, delete the script.
4. **Don't use `browser_cookie3` for anything beyond simple cookie-auth sites.** SSO breaks it.
5. **Don't pay for Scrapfly/Browserbase before trying curl_cffi.** Free first, paid last.
