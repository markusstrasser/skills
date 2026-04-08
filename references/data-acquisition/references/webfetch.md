<!-- Reference file for data-acquisition skill. Loaded on demand. -->

# WebFetch — Quick Page Grabs (Claude Code built-in)

**What:** Claude Code's built-in `WebFetch` tool. Fetches a URL and returns content. No authentication, no JS rendering.

**When:** Quick checks — is this URL alive? What does this page say? Grab a JSON API response. Check if a download link works before building a full pipeline.

**Limitations:** No cookies/auth, no JS rendering, may be blocked by Cloudflare. Falls back gracefully — use it as a fast probe before reaching for heavier tools.
