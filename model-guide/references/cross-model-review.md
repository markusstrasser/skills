# Cross-model review pattern

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L398-413, L415-419.

## Cross-Model Review Pattern

Use independent parallel reviews, then synthesize yourself:

```text
Opus 5.5 (max for architecture): architectural/professional judgment and implementation critique.
GPT-6 Astra: terminal/tool/process critique and structured failure search (hard).
GPT-6 Luna: mechanical / bulk (low).
GPT-6 Astra + reasoning.mode=pro: quantitative or high-irreversibility decisions.
Grok 4.7 high (Cursor opt-in, or Grok Build headless in the repo): repo-grounded premise falsification after live preflight.
Ground truth: tests, git, databases, source documents, primary web pages.
```

**Phase-0 before any model COMPARISON / bakeoff:** `grep ~/Projects/evals/DECISIONS.md` for the question FIRST — it may be settled, and a fresh n=1 probe must not steer a default an eval already decided. (2026-06-13: a 4-model review bakeoff re-ran the settled `cross-lab-review-margin` question, and an `/execute` edit got written contradicting its verdict — Phase-0 dedup caught it only after the fact.)

That verdict, calibrated: the cross-lab-vs-same-lab MARGIN is **≈0** — a second DIVERSE pass earns its keep via *count-delta* (it finds what the first missed), but the second reviewer being a different LAB buys ~nothing over a same-lab second instance, and it still hallucinates facts (a MiniMax-M3 pass verified ~25%, confident HIGH fabrications — ground any reviewer's asserted facts, weight its reasoning). The real martingale to avoid is a model reviewing its OWN output (same instance) as the *sole* adversarial pass.

## Validation Checklists

Post-output verification lists — All Outputs + per-model (Opus 5.5, Fable 5, Sonnet 5, GPT-5.6 Sol/Terra/Luna [historical: Fable 5 and GPT-5.6 retired 2026-09-25, Pareto-frontier prune],
GLM-5.2, Grok 4.7): [references/validation-checklists.md](validation-checklists.md).
Consult after receiving output from a routed model, not at routing time.
