<!-- Reference file for observe skill (architecture mode). Loaded on demand. -->

# Existing Infrastructure Cross-Reference (Phase 3a)

Before generating proposals, check what already exists. This prevents proposing things that are already built.

```bash
OBSERVE_PROJECT_ROOT="${OBSERVE_PROJECT_ROOT:-$HOME/Projects/agent-infra}"

# Existing skills
ls ~/Projects/skills/

# Existing hooks (count by event type)
python3 -c "import json; s=json.load(open('$HOME/.claude/settings.json')); [print(f'{k}: {sum(len(g[\"hooks\"]) for g in v)}') for k,v in s.get('hooks',{}).items()]"

# Meta backlog items
grep '^\- \[' "$OBSERVE_PROJECT_ROOT/CLAUDE.md" | head -20

# Improvement log (recent)
tail -50 "$OBSERVE_PROJECT_ROOT/improvement-log.md"

# Active pipelines
ls "$OBSERVE_PROJECT_ROOT/pipelines/"

# Session-retro findings DB — check if pattern is already tracked
uv run python3 "$OBSERVE_PROJECT_ROOT/scripts/finding-triage.py" list --all 2>/dev/null | head -30

# Pattern status — check what's already addressed
uv run python3 "$OBSERVE_PROJECT_ROOT/scripts/pattern-maintenance.py" status 2>/dev/null | head -30
```
