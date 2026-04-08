<!-- Reference file for data-acquisition skill. Loaded on demand. -->

# Playwright (local) — Headless Browser

**When:** Simple sites without bot detection. Rendering JS locally. Testing.

**Gotchas on macOS:**
- Chrome `--remote-debugging-port=9222` does NOT work — macOS App Sandbox blocks it
- Persistent context with Chrome profile copies cookies but NOT server-side sessions
- Use Playwright's own Chromium, not system Chrome, for automation
