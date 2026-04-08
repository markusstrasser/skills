<!-- Reference file for data-acquisition skill. Loaded on demand. -->

# Scrapfly — Anti-Bot API

Paid API for Cloudflare/JS-rendered/bot-detected sites. Key: `SCRAPFLY_KEY` in `.env.local`.
When: SSL failures + Cloudflare + bot detection that curl_cffi can't beat.

```python
from scrapfly import ScrapflyClient, ScrapeConfig
client = ScrapflyClient(os.environ.get("SCRAPFLY_KEY", ""))
result = client.scrape(ScrapeConfig(url=url, asp=True, render_js=True, country="us"))
# result.content has the HTML
```

Install: `uv add scrapfly-sdk`. Cost: ~$0.001-0.01/request, `asp=True` costs more.
