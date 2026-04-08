<!-- Reference file for data-acquisition skill. Loaded on demand. -->

# claude-in-chrome — User's Live Chrome Session

**What:** MCP tools that control the user's actual Chrome browser via the Claude extension. Only way to use existing authenticated sessions (SSO, Google login, institutional access).

**When:** ANY site requiring login — ICPSR, NCES, bank portals, institutional archives. This is the ONLY approach that works for SSO-authenticated sessions.

## Workflow

```
1. mcp__claude-in-chrome__tabs_context_mcp  → get tab IDs (ALWAYS first)
2. mcp__claude-in-chrome__navigate          → go to URL
3. mcp__claude-in-chrome__find              → locate elements by description
4. mcp__claude-in-chrome__computer          → click, type, scroll, screenshot
5. mcp__claude-in-chrome__javascript_tool   → run JS in page context
6. mcp__claude-in-chrome__get_page_text     → extract page content
```

## Key Patterns

- Wait after navigation: `computer(action="wait", duration=3)`
- Screenshot before clicking: `computer(action="screenshot")` to see what's there
- JS for data extraction: `javascript_tool` for reading DOM programmatically
- `find` for natural language element location: `find(query="download button")`

## When to Ask the Human for Help

- **CAPTCHA or visual challenge** — you can't solve these. Ask the user to complete it, then resume.
- **MFA / 2FA prompt** — the user must enter their code. Wait for them.
- **Login required and user isn't logged in** — don't try to enter credentials. Tell the user to log in manually in Chrome, then continue.
- **Site asks for terms acceptance / license agreement** — the user must review and accept. Don't click "I agree" on their behalf for legal agreements.
- **Download leads to a file picker / OS dialog** — you can't interact with OS-level dialogs. Ask the user to handle it.
- **Repeated failures after 2-3 attempts** — stop, explain what you tried, ask for guidance.

## Downloads

- Clicked downloads go to the user's Chrome Downloads folder (usually `~/Downloads/`)
- After triggering a download, wait a few seconds, then check `~/Downloads/` for the new file
- Move/copy the file to the project data directory — don't leave it in Downloads
- Always verify: `file <downloaded>` to check type, `head -5` to check for HTML traps

## JS Gotchas

- `await` in `javascript_tool` requires wrapping: `(async () => { ... })()`
- Return values containing URLs with query strings may show as `[BLOCKED: Cookie/query string data]` — simplify queries to avoid returning raw URLs
- Don't trigger `alert()`, `confirm()`, or `prompt()` — browser dialogs block the extension completely. Use `console.log()` + `read_console_messages` instead.
