<!-- Reference file for data-acquisition skill. Loaded on demand. -->

# curl_cffi — TLS Fingerprint Impersonation

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
