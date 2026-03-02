---
name: retro
description: End-of-session retrospective. Extracts failure modes, environment struggles, and tooling proposals.
user-invocable: true
argument-hint: '[project]'
---

Review what happened in this session:

1. What went wrong? Name specific failure modes (build-then-undo, token waste, sycophancy, search flooding, wrong assumptions).
2. Where did you struggle with the environment (paths, dependencies, APIs, permissions, hooks)?
3. What information would have saved time if you'd known it upfront?
4. What recurring pattern should become a hook, rule, or skill?

Read `improvement-log.md` in the meta project to check for existing entries before proposing new ones.

Output format:
- 3-5 bullet points, each with: **failure mode**, evidence (file/command/line), proposed fix
- If any finding matches an existing improvement-log entry, note "RECURRING: matches entry from YYYY-MM-DD"
- Be concise. No platitudes. Name the files, the commands, the exact mistake.
