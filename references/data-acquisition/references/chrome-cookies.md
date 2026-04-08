# Chrome Cookie Extraction (macOS)

**Module:** `~/Projects/selve/scripts/tools/chrome_cookies.py`

Extracts cookies directly from Chrome/Chromium/Brave's encrypted SQLite database on macOS. No browser extensions, no API keys, no OAuth. Works while Chrome is running.

## When to Use

- Site uses cookie-based auth (not SSO/Keycloak) — Twitter/X, Instagram, Pinterest
- You need `requests.Session` headers for direct API calls
- You want to avoid yt-dlp's `--cookies-from-browser` overhead for non-video requests

## When NOT to Use

- SSO/Keycloak sites (session is server-side, cookie alone doesn't work)
- Google accounts (fingerprints cloud environments)
- Sites you're not logged into in Chrome

## API

```python
from scripts.tools.chrome_cookies import get_cookies, get_session_headers

# Basic: get decrypted cookie values
cookies = get_cookies("instagram.com", names=["sessionid", "csrftoken"])
# → {"sessionid": "456643034%3A...", "csrftoken": "aLx3fn..."}

# Auto-detect profile (tries all, picks best match)
cookies = get_cookies("pinterest.com")  # profile=None is default

# Explicit profile
cookies = get_cookies("x.com", ["ct0", "auth_token"], profile="Profile 2")

# Build ready-to-use HTTP headers (includes CSRF, app IDs, bearer tokens)
headers = get_session_headers("instagram.com", ["sessionid", "csrftoken"])
# → {"Cookie": "...", "User-Agent": "...", "X-CSRFToken": "...", "X-IG-App-ID": "..."}

session = requests.Session()
session.headers.update(headers)
resp = session.get("https://i.instagram.com/api/v1/...")
```

## CLI

```bash
# Auto-detect profile, extract specific cookies
uv run python scripts/tools/chrome_cookies.py instagram.com sessionid csrftoken

# All cookies for a domain
uv run python scripts/tools/chrome_cookies.py pinterest.com

# As HTTP headers (for curl piping)
uv run python scripts/tools/chrome_cookies.py --headers instagram.com sessionid csrftoken

# JSON output
uv run python scripts/tools/chrome_cookies.py --json instagram.com sessionid

# List profiles
uv run python scripts/tools/chrome_cookies.py --list-profiles

# Explicit profile + browser
uv run python scripts/tools/chrome_cookies.py --profile "Profile 2" --browser brave x.com ct0
```

## Platform-Specific Headers

`get_session_headers()` auto-adds platform headers:

| Domain | Extra headers |
|--------|--------------|
| x.com / twitter.com | `Authorization: Bearer <public token>`, `x-csrf-token`, `x-twitter-auth-type` |
| instagram.com | `X-CSRFToken`, `X-IG-App-ID: 936619743392459` |

## How It Works

1. Read Chrome's encryption password from macOS Keychain (`security find-generic-password`)
2. PBKDF2 key derivation (salt="saltysalt", 1003 iterations, SHA1, 16 bytes)
3. Query Cookies SQLite DB (copies to temp file if Chrome has it locked)
4. AES-128-CBC decrypt with 16-space IV, strip v10/v11 prefix
5. Handle Chrome 130+ format (32-byte SHA256 prefix in plaintext)

## Gotchas

- **macOS only** — uses `security` CLI + Keychain. Linux/Windows need different approaches.
- **Profile auto-detect** scans all profiles and picks the one with most matching cookies. Explicit `--profile` is faster.
- **Cookies expire.** If extraction succeeds but API calls fail with 401/403, the session may have expired — re-login in Chrome.
- **x.com ↔ twitter.com fallback** is automatic (both domains are tried).
