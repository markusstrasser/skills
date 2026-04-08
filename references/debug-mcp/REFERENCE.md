# MCP Debugging Reference - Key Learnings

## The One Thing That Broke Everything

**`.claude/settings.local.json`** with `"enableAllProjectMcpServers": false`

This single setting blocks ALL `.mcp.json` servers from loading, regardless of any other configuration.

## Why This Was Hard to Find

1. **Hidden location**: Not in the obvious places (`.mcp.json`, `~/.claude.json`)
2. **Non-obvious name**: "settings.local.json" vs "local-settings.json"
3. **Boolean default**: Setting exists but defaults to false when present
4. **No clear error**: MCPs just silently don't load
5. **CLI commands lie**: `claude mcp get` shows "Connected" but `/mcp` doesn't list them

## The Debugging Journey

### What Didn't Work
- ❌ Checking `.mcp.json` - it was correct
- ❌ Restarting Claude Code - didn't help
- ❌ Resetting project choices - wasn't the issue
- ❌ Checking environment variables - they were loaded
- ❌ Testing prerequisites - everything was installed
- ❌ Checking JSON syntax - was valid

### What Finally Worked
- ✅ Actually running `claude mcp get <name>` - showed MCPs were configured
- ✅ Checking `~/.claude.json` project-specific settings
- ✅ Finding `.claude/settings.local.json`
- ✅ Discovering `"enableAllProjectMcpServers": false`

## MCP Scope Confusion

### Three Different Scopes
1. **User scope** (`~/.claude.json` → `mcpServers`)
   - Available in ALL projects
   - No approval needed
   - Shows up immediately

2. **Project scope** (`.mcp.json` at project root)
   - Shared with team (version controlled)
   - Requires approval OR `enableAllProjectMcpServers: true`
   - Can be blocked by local settings

3. **Local scope** (`.claude/settings.local.json`)
   - Personal overrides for specific project
   - NOT version controlled
   - Highest priority for this project

## The Type Field Gotcha

In `.mcp.json`, the `type` field must be:
- `"stdio"` - for local commands (NOT "local")
- `"http"` - for remote HTTP servers
- `"sse"` - for Server-Sent Events (deprecated)

## Environment Variable Expansion

```json
{
  "env": {
    "KEY": "${VAR_NAME}"           // Expands VAR_NAME
    "KEY": "${VAR_NAME:-default}"  // With fallback
  }
}
```

**Critical**: Variables must be set BEFORE Claude Code starts.

Best practice: Add to `~/.zshenv` (not `~/.zshrc`) because `.zshenv` is loaded for all shells, including non-interactive ones.

## Testing Commands

```bash
# See what's actually loaded
claude mcp list

# Get details for specific MCP
claude mcp get <name>

# Check project settings
cat .claude/settings.local.json

# Check user MCPs
cat ~/.claude.json | jq '.mcpServers'

# Check project MCPs
cat .mcp.json

# Check project-specific config in user file
cat ~/.claude.json | jq '.projects["'$(pwd)'"]'

# Reset approvals
claude mcp reset-project-choices
```

## The Complete Fix

1. Edit `.claude/settings.local.json`:
   ```json
   {
     "enableAllProjectMcpServers": true
   }
   ```

2. Restart Claude Code

3. (Optional) Remove duplicate MCPs from user scope if they exist in project scope

## Lessons Learned

1. **CLI truth vs UI truth**: `claude mcp get` shows configuration, `/mcp` shows what's actually loaded
2. **Local settings override everything**: `.claude/settings.local.json` has final say
3. **Test prerequisites independently**: Don't assume, verify each component
4. **Hidden gotchas in obvious places**: The answer was in plain sight but easy to miss
5. **Environment variables are tricky**: Must be loaded in the right shell config file at the right time

## Future Self Reminder

When MCPs don't load:
1. Check `.claude/settings.local.json` FIRST
2. Run `claude mcp get <name>` to verify config
3. Compare with `/mcp` output to see what's actually loaded
4. Check project-specific settings in `~/.claude.json`
5. Only then check the other stuff
