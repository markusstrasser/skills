<!-- Reference file for evolution-forensics skill. Loaded on demand. -->

# Commit Classification (Phase 1b)

Classify each commit:

| Type | Signal | Example |
|------|--------|---------|
| **FIX** | fix, repair, correct, patch, resolve | `[hooks] Fix trap swallowing exit 2` |
| **FIX-OF-FIX** | Fixes a file touched by a FIX within 3 days | Same file, two fixes, short gap |
| **REVERT** | revert, undo, drop, remove, retire | `[infra] Drop finding-triage DB` |
| **FEATURE** | New capability, wiring, integration | `[api] Wire rate-limit refresh` |
| **RULE** | CLAUDE.md, rules/, hooks, improvement-log | `[rules] Extend probe-before-build` |
| **RESEARCH** | research/, decisions/ | `[research] Agent scaffolding landscape` |
| **CHORE** | Docs, formatting, deps | `[docs] Regenerate codebase map` |

Extract per commit: scope, type, files_changed, churn (lines +/-), Session-ID (if present).
