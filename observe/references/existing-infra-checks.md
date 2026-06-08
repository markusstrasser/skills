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

# Findings / patterns are tracked inline in the improvement-log (the
# finding-triage.py + pattern-maintenance.py DBs were retired — see
# vetoed-decisions.md). Grep the log for the pattern before proposing it:
grep -in "<pattern keyword>" "$OBSERVE_PROJECT_ROOT/improvement-log.md" | head -30

# Orphaned generators already flagged (don't propose deleting what the ratchet
# already surfaces):
just -f "$OBSERVE_PROJECT_ROOT/justfile" orphan-check 2>/dev/null | head -20
```
