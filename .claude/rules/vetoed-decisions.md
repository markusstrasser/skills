# Vetoed Decisions

Agents: check this list before proposing or re-implementing anything listed here.
These decisions were made deliberately and should not be re-derived.

- Do NOT add effort frontmatter to skills that don't need it — only reasoning-heavy skills get `effort: high`. Default is fine for most.
- Do NOT use `--stream` flag with Gemini CLI in skills — forces API fallback, CLI transport is free.
- Do NOT use `--fallback` in llmx calls — model should be the model. Diagnose failures, don't mask with downgrade.
