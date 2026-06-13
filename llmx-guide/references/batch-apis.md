# Batch & Async-Cheap Tiers — the 50%-off lane for embarrassingly-parallel jobs

For bulk, non-interactive jobs (corpus extraction, re-embedding, eval sweeps) the right
tool is a **batch API**, not a bigger thread pool. All three frontier providers offer a
~50% discount for accepting async (24h-window) delivery. Verified against provider docs
2026-06-13 (web-grounded; re-check before a large spend — these specs move).

## What llmx wraps today

| Path | Provider | Status |
|------|----------|--------|
| `llmx batch {submit,status,get,list,cancel}` | **Gemini only** | ✅ wired — JSONL in, 50% off |
| `--flex` (per-call, best-effort 50% off) | Gemini | ✅ wired (variable latency, sheds load w/ 503s; pair `--fallback`) |
| OpenAI Batch API | OpenAI | ❌ not in llmx — use the OpenAI SDK / REST directly |
| Anthropic Message Batches | Anthropic | ❌ not in llmx — use the Anthropic SDK directly |

`llmx batch submit <file.jsonl>` is the whole production path for any Gemini bulk job.
Gemini Batch can read input from **GCS** (1 GB file) or inline; GCS is the path for
corpus-scale chunk fan-out (thousands of requests).

## Provider batch specs (2026-06, verified)

| | OpenAI Batch | Anthropic Message Batches | Gemini Batch (Developer API) |
|---|---|---|---|
| Discount | 50% (in+out) | 50% (in+out) | 50% (in+out) |
| Turnaround | target 24h window, best-effort | **most <1h**, hard 24h deadline | most <24h after start; up to **72h queue** before expiry |
| Max requests/batch | 50,000 / JSONL file | **100,000** | **200,000** |
| Max input size | 200 MB | 256 MB | 1 GB (GCS input) |
| Structured output | ✅ (`response_format` json_schema per line) | ✅ (normal Messages body; **`fallbacks` rejected**) | ✅ (`responseSchema`; not on batch "unsupported" list) |
| Result match | by `custom_id` | by `custom_id` (order NOT guaranteed); results kept 29d | by request order |
| Extra | per-org **batch token-queue** limit (separate from RPM) | batch + prompt-cache discounts **stack** | higher rate limit than realtime; no explicit/RAG cache in batch |

Anthropic has the best typical turnaround (<1h) and can stack with prompt caching; Gemini
has the largest job size + is the only one wrapped in llmx. For a Gemini-model job, `llmx
batch` is the answer and nothing else is needed.

## Transport reality (corrects a common stale belief)

- **The free Gemini CLI (`gemini`) was retired 2026-05-31 and is uninstalled.** It is NOT
  the transport for anything.
- **`-p google` goes DIRECT to the paid Gemini Developer API** (`GEMINI_API_KEY`). There is
  no CLI in the path — the only subprocess is the `llmx` binary itself. (So "gemini-cli
  OAuth corruption under concurrency" is a dead concern — there is no gemini-cli.)
- **`agy` (Antigravity CLI) is NOT an llmx transport** — it can't pin a model in headless
  mode. It's an interactive CLI only; ignore it for programmatic dispatch.
- Practical concurrency cap on the per-call CLI path is the `llmx` process-spawn tax +
  provider rate limits — which is exactly why bulk work should go through `llmx batch`,
  not a wider `ThreadPoolExecutor`.

## Gemini model naming (verified ai.google.dev 2026-06-13)

- **There is no `gemini-3.1-flash` text model.** The 3.1 generation shipped Pro, Flash-Lite,
  and Flash-Image — no plain Flash. The Flash *text* line skips 3.1:
  `gemini-3-flash-preview` → `gemini-3.5-flash`.
- Current lineup: **latest Flash = `gemini-3.5-flash`**, latest Pro = `gemini-3.1-pro`
  (Flash carries a higher number than Pro — counterintuitive but real). **Pro is RETIRED as a
  routing option (2026-06-13) — do not route batch jobs there; flash-3.5 dominates.**
- Batch-eligible routing IDs: `gemini-3.5-flash`, `gemini-3-flash-preview`, `gemini-3.1-flash-lite`.
  (`gemini-3.1-pro` is also batch-eligible but is not a routing option — see model-guide.)
