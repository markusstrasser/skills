<!-- Reference file for data-acquisition skill. Loaded on demand. -->

# Plain requests/curl — Always Try First

```python
import requests
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 ..."}, timeout=120, stream=True)
```

The simplest approach. Works ~80% of the time. Always try before reaching for heavier tools.
