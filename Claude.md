# Skills — Claude Code Instructions

18 active skills + 33 hooks for Claude Code agent infrastructure.

## Structure

```
skills/
├── Claude.md              # This file
├── README.md              # Public docs
├── hooks/                 # 33 shared hooks (referenced by path from settings.json)
├── archive/               # Superseded skill versions
└── [skill-name]/          # Each skill: SKILL.md + optional companion files
    └── SKILL.md           # Frontmatter (name, description, triggers) + instructions
```

## Skill Authoring

Required: `SKILL.md` with YAML frontmatter (`name`, `description`). Description must include trigger words.

- Keep `SKILL.md` focused. Move reference material to companion files (DOMAINS.md, REFERENCE.md).
- Use `allowed-tools` in frontmatter for read-only skills.
- Test: start Claude Code and ask questions matching your trigger words.

## Conventions

- Skills are copied (not symlinked) into projects via SessionStart hooks.
- Hooks are referenced by absolute path from `~/.claude/settings.json` or project settings.
- `archive/` holds old versions that were rewritten, not deleted content.
- No build step, no dependencies — skills are plain markdown.
