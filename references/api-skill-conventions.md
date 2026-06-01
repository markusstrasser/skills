# API-Wrapping Skill Conventions

Rules for any skill or MCP tool that wraps an external HTTP API. Adapted from
[google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
(Apache-2.0) — a ~45-skill bundle whose *form* (not its bio data) is the reusable
asset. Steal the discipline; it's what makes an API wrapper agent-safe.

Apply when: writing a CLI script that calls an API, adding an MCP tool backend,
or reviewing one. These are checkable predicates — a reviewer can verify each.

## 1. Result limit is required, no silent default

Every search/list operation takes an explicit `limit` / `max_results` —
**required**, not defaulted. A silent cap (e.g. an API's implicit `pageSize=20`)
makes the agent believe it retrieved "all" results when it got the first page.
Force the caller to name the number.

- CLI: `parser.add_argument("--limit", type=int, required=True)`.
- MCP tool: accept `limit` and document the hard ceiling in the docstring; cap
  defensively (`min(limit, MAX)`).

## 2. Output to file / structured return — never dump to stdout

- **CLI scripts:** write results to a `--output` JSON file. stdout carries only
  a status line (`Success! Data written to: results.json`). API responses are
  large; raw stdout truncates in terminals and burns the agent's context. The
  agent then greps the file for the fields it needs.
- **MCP tools:** return structured `list[dict]` / `dict`; truncate long text
  fields (abstracts → ~300 chars) before returning.

## 3. Error body in the exception, not just the status code

On a non-retryable HTTP error, read the response body and include it
(truncated ~500 chars) in the raised exception or returned error dict. API
bodies say *why* ("Invalid parameter X", "unknown db") — that's what lets the
agent self-correct instead of blindly retrying. On 403, add a User-Agent hint.

```python
except httpx.HTTPStatusError as exc:
    body = exc.response.text[:500]
    raise RuntimeError(f"{API} {exc.response.status_code} for {path}: {body}") from exc
```

## 4. Rate limiting is code, not a comment

Look up the API's documented limit (default to 1 req/s if undocumented) and
**enforce it in code** with `time.monotonic()` — never `time.time()` (wall clock
jumps). Retry transient errors (429, 5xx) with exponential backoff + jitter;
honor `Retry-After`.

- **Single-process** (one MCP server, serial calls): an in-instance min-interval
  gate is enough.
- **Concurrent subagents sharing a host:** use a cross-process **file lock**
  (`fcntl.flock` on `/tmp/{ns}-{host}.lock`) so they collectively respect one
  limit. Reference impl: science-skills `scienceskillscommon/http_client.py`
  (`_RateLimiter`, `_parse_retry_after`, and `X-Throttling-Control` proactive
  backpressure — colours Green/Yellow/Red/Black → 0/1/5/30 s slowdown *before*
  hitting a hard 429).
- **FastMCP nuance:** sync tools run in a worker thread, so a blocking
  `time.sleep` limiter inside a sync backend does NOT block the event loop. Only
  `async def` tools need `asyncio.sleep`. Match the surrounding tools' sync/async
  style rather than mixing.

## 5. Reuse before reimplement

Before adding a backend, check whether an existing skill/tool already covers the
source. If it does, reference it — do not duplicate the wrapper. (Evidence:
research-mcp already had S2 + OpenAlex + bioRxiv; adding a redundant PubMed
*search* path was dropped in favour of one EuropePMC backend that returned
abstracts in a single call.)

## 6. Resolve-first

Accept human identifiers (gene symbol, DOI, free-text name) and resolve to the
API's canonical ID internally, in one documented step. Don't make the caller
pre-resolve.

## 7. Stdlib-first dependencies

Prefer `urllib`/`httpx` + `json` over heavyweight clients. The science-skills
bundle wraps 40+ APIs with zero third-party deps beyond the stdlib. Fewer deps =
fewer install failures when an agent runs the script cold.

---

**Anti-pattern this bundle warns against:** shipping every capability as a
file-writing CLI when the consumer is a long-lived MCP server. For MCP, prefer
typed tools returning structured data; the CLI-to-file pattern is for one-shot
scripts the agent runs via Bash. Pick the delivery model to match the consumer.
