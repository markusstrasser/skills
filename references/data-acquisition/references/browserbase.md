<!-- Reference file for data-acquisition skill. Loaded on demand. -->

# Browserbase — Cloud Browser

Full cloud Chromium via Playwright CDP. Keys: `BROWSERBASE_API_KEY` + `BROWSERBASE_PROJECT_ID` in `.env.local`. Use for complex multi-step JS flows on non-authenticated sites. NOT for SSO/Google-login (Google blocks cloud browsers). Install: `uv add playwright && playwright install chromium`. See Browserbase docs for connection boilerplate.
