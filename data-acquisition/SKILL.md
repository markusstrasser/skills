---
name: data-acquisition
description: Hard-won lessons for downloading datasets from academic repositories (ICPSR, NCES, Dataverse, etc.) and authenticated web scraping. Use when acquiring research data, navigating gated archives, or automating downloads through authenticated browser sessions. Prevents wasted cycles on dead-end approaches.
user-invocable: true
argument-hint: '[dataset name or repository URL]'
---

# Data Acquisition — Anti-Waste Playbook

Every rule below was learned by failing first. Follow the decision tree before writing any download code.

## Decision Tree: Can I Get This Data?

```
1. Is it on a Dataverse instance (Harvard, UNC, etc.)?
   → YES: curl/wget directly. No auth needed. Best case.
   → NO: continue

2. Is it on ICPSR?
   → Check which ICPSR archive (see §ICPSR below)
   → DSDR archive + per-dataset format buttons visible? → Downloadable via Chrome session
   → DSDR archive + no format buttons on data rows? → RESTRICTED despite "public-use" label
   → ICPSR archive (not DSDR)? → Requires institutional membership for data files
   → Study-level download only returns codebooks. Always.

3. Is it on NCES?
   → Check DataLab Online Codebook (JS SPA, only 1991+ studies)
   → HS&B (1980s) is NOT in Online Codebook — only in PowerStats (remote analysis, no download)
   → HSLS/ELS/NELS/ECLS-K ARE in Online Codebook with downloadable microdata

4. Is it behind any login wall?
   → See §Authenticated Downloads below
```

## ICPSR Architecture (critical)

### Three tiers of ICPSR access

| Tier | URL pattern | Data files? | What you need |
|------|-------------|-------------|---------------|
| **DSDR (public)** | `icpsr.umich.edu/web/DSDR/studies/{id}` | YES if per-dataset rows show sizes + format buttons | Free ICPSR account + terms acceptance |
| **DSDR (restricted label)** | Same URL, but data rows have no size/no download button | NO | Restricted Data Use Agreement |
| **ICPSR archive** | `icpsr.umich.edu/web/ICPSR/studies/{id}` | Codebooks only | Institutional ICPSR membership |

### How to tell before wasting time

1. Go to `https://www.icpsr.umich.edu/web/DSDR/studies/{id}/datadocumentation`
2. Look at the dataset table (DS0, DS1, DS2...)
3. **If DS1+ rows show a Size column value (e.g., "85 MB") AND have a download button** → data is downloadable
4. **If DS1+ rows show blank Size and no download button** → data is restricted, stop here
5. DS0 is always documentation-only

### ICPSR terms acceptance flow

The "I Agree" button does NOT appear on the `/terms` page. It appears as a **React modal** when you click a per-dataset download button on the `/datadocumentation` page. The flow:

1. Navigate to `/datadocumentation`
2. Click the download icon on a dataset row
3. Select a format (Stata, SPSS, etc.) from the dropdown
4. Terms modal appears → scroll to bottom → click "Agree"
5. Redirects to "Your Download Should Begin Shortly" page with meta-refresh

### ICPSR download URL patterns

```
# Study-level (ALWAYS codebooks only — don't bother)
https://www.icpsr.umich.edu/web/{archive}/studies/{id}/versions/{ver}/download/spss

# Per-dataset (works for DSDR public studies)
https://www.icpsr.umich.edu/web/{archive}/studies/{id}/versions/{ver}/datasets/{dsNum}/download/stata

# Meta-refresh redirect page extracts actual download UUID:
<meta http-equiv="refresh" content="...url=https://pcms.icpsr.umich.edu/pcms/performDownload/{uuid}">
```

### Known DSDR studies that actually deliver data

| Study | ICPSR ID | Size | Works? |
|-------|----------|------|--------|
| FFCWS (Fragile Families) | 31622 | 2 GB (all years) | YES — per-dataset download with format buttons |
| SECCYD Phase I-IV | 21940, 21941, 21942, 22361 | ? | NO — "public-use" label but data rows have no download buttons |

## NCES Architecture

- **DataLab Online Codebook** (`nces.ed.gov/datalab/onlinecodebook/`): JS SPA, only lists 1991+ studies (ECLS-K, ELS, HSLS, NELS, NHES, SSOCS, SASS). HS&B not included.
- **DataLab PowerStats** (`nces.ed.gov/datalab/`): Remote analysis (regressions, tables) — includes HS&B, but NO microdata download.
- **Old Online Codebook** (`nces.ed.gov/surveys/*/OnlineCodebook/`): Decommissioned, returns HTTP 500.
- **Restricted-use license**: Individual researchers can apply regardless of institution. Separate from ICPSR membership.

## Authenticated Downloads — What Works and What Doesn't

### What DOES NOT work (don't try these)

| Approach | Why it fails |
|----------|-------------|
| **browser_cookie3** | Extracts Chrome cookies but server-side sessions don't transfer. ICPSR returns `session = {}`. |
| **Chrome `--remote-debugging-port=9222`** | macOS App Sandbox prevents Chrome from opening the port. `lsof` confirms nothing listening. |
| **Playwright persistent context with Chrome profile** | Copies cookies but session state doesn't transfer for SSO-authenticated sites. |
| **Browserbase cloud browser + Google SSO** | Google blocks automated login from cloud browsers (fingerprint detection). |
| **Browserbase + email/password login** | Only works if the site has native email/password auth. ICPSR uses Keycloak SSO — "Sign in with email" is hidden behind a button click, and if the account was created via Google SSO, there is no password. |
| **Direct `fetch()`/`curl` with extracted cookies** | 403 on API endpoints. Server validates session integrity beyond cookies. |

### What DOES work

| Approach | When to use | Notes |
|----------|-------------|-------|
| **claude-in-chrome MCP tools** | User has Chrome open and logged in | Navigate, click, accept terms, trigger downloads through the user's live session. The ONLY reliable approach for SSO-authenticated sites. |
| **Direct URL download (curl/wget)** | Public data on Dataverse, direct file URLs | No auth needed. Always try this first. |
| **Chrome DevTools console script** | User can paste JS into DevTools | Works when you need programmatic downloads within an authenticated session. Useful as a fallback if chrome MCP unavailable. |

### claude-in-chrome workflow for authenticated downloads

```
1. tabs_context_mcp → get existing tabs
2. navigate → go to the repository's datadocumentation page
3. find/javascript_tool → locate dataset rows, format buttons
4. computer (click) → click download button → format dropdown appears
5. computer (click) → select format (Stata recommended for social science)
6. If terms modal appears:
   a. computer (scroll) → scroll to bottom of modal
   b. computer (click) → click "Agree"
7. Wait for "Your Download Should Begin Shortly" page
8. Check ~/Downloads/ for the zip
9. Verify zip contains data files (not just codebooks): unzip -l | grep '.sav|.dta|.dat'
```

### Critical: always verify downloads contain data

```bash
# After ANY ICPSR download, check for actual data files:
unzip -l downloaded.zip | grep -iE '\.(sav|dta|dat|csv|tsv|por|sas7bdat|xpt) '

# If you only see .pdf, .txt, .html → codebook-only. Data is gated.
# Real data downloads show files like: 31622-0001-Data.dta (289 MB)
```

## Dataverse (easiest path)

Dataverse instances (Harvard, UNC, etc.) serve data directly. No auth, no terms modals, no institutional walls.

```bash
# UNC Dataverse example (Add Health):
curl -L -o wave1.tab "https://dataverse.unc.edu/api/access/datafile/{fileId}"

# Harvard Dataverse:
curl -L -o data.tab "https://dataverse.harvard.edu/api/access/datafile/{fileId}"
```

Always check Dataverse FIRST before trying ICPSR for any dataset.

## Probe Scripts: Don't Accumulate

After acquisition attempts (successful or failed), **delete probe scripts**. They accumulate fast (we generated 32 in one session) and add no value once the download succeeds or the dead end is documented. The lessons belong in this skill and in the project's access playbook, not in throwaway scripts.

## Anti-Patterns

1. **Don't retry the same wall with more code.** If ICPSR returns codebooks, writing a fancier downloader won't produce data files. The wall is access-tier, not technical.
2. **Don't trust "freely available" or "public-use" labels.** Always verify by checking whether data rows have download buttons AND sizes.
3. **Don't build Playwright/Puppeteer automation for SSO sites.** Google blocks cloud browsers. macOS blocks CDP ports. Session cookies don't transfer. Use the user's live Chrome session via claude-in-chrome.
4. **Don't download study-level zips from ICPSR.** They're always codebook-only. Use per-dataset downloads from the datadocumentation page.
5. **Don't accumulate probe scripts.** Document the lesson, delete the script.
