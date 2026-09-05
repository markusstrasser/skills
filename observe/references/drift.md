# Observe: drift

Read [transcript preparation](transcript-extraction.md), [analysis dispatch](analysis-dispatch.md), and [candidate lifecycle](candidate-lifecycle.md). The headless historical-context fence is required.

The SLOW, WIDE pass. Where `sessions` reads ~5 sessions over 1 day, `drift` reads 21 days across all
projects in one 1M-context shot to find what no single retro can see: recurrence counts,
proposed-but-never-built, rising friction, convention drift. Weekly via `/loop`, not daily. Prompt:
[drift-dispatch-prompt.md](drift-dispatch-prompt.md).

Slow *and* cheap because `observe_bulk` is 1M-capable: 3 weeks ≈ 200-600KB, one dispatch. The lever
is Flash-Lite + async, **not** the Batch API (not wired in `llm-dispatch.py`). The `claude_review`
Opus profile caps at 200K and is **not** a substitute.

Drift **leans on the git-commit operational context** to detect proposed-but-never-built (a fix
proposed early with no later landing commit) — build it, don't skip it. Use `--sessions 60`+ so the
window is not silently truncated; if extraction exceeds the size guard, narrow `--days` rather than
disabling the guard. Stage each finding with the **distinct-session count in evidence** so the
2+-recurrence gate is machine-checkable; findings at 2+ distinct sessions are promotion-eligible
immediately. Lead `drift-digest.md` with promotable findings.
