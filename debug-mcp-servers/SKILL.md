---
name: debug-mcp-servers
description: Debug why MCP servers aren't loading in Claude Code. Use this when user reports MCPs not appearing in /mcp list despite being configured.
model: haiku
---

# Debug MCP Servers Not Loading

When MCP servers are configured but don't appear in `/mcp`, follow this systematic debugging process.

## Step 1: Check Current MCP Configuration

```bash
claude mcp list
```

This shows which MCPs are actually loaded and their connection status.

## Step 2: Verify MCP Configuration Files

Check both scopes where MCPs can be configured:

### User Scope (global, all projects)
```bash
cat ~/.claude.json | jq '.mcpServers'
```

### Project Scope (current project only)
```bash
cat .mcp.json
```

**Key insight**: Project-scoped MCPs in `.mcp.json` require approval or explicit enabling.

## Step 3: Check Local Settings Override

**THIS IS THE MOST COMMON ISSUE:**

```bash
cat .claude/settings.local.json
```

If this file contains:
```json
{
  "enableAllProjectMcpServers": false
}
```

**This blocks ALL .mcp.json servers from loading!**

**Fix:**
```bash
# Edit the file to set it to true, or remove the file entirely
```

Alternative locations to check:
- `.claude/settings.json` (project settings)
- User-level settings that might override

## Step 4: Verify Claude Code State

```bash
cat ~/.claude.json | jq '.projects["'$(pwd)'"]'
```

Look for:
- `enabledMcpjsonServers` - should be `null` or contain your server names
- `disabledMcpjsonServers` - should not contain your servers
- `disabledMcpServers` - should not contain your servers

## Step 5: Test MCP Prerequisites

For each MCP that's not loading:

### HTTP/SSE MCPs
```bash
curl -I <mcp-url>
```

Should return a valid HTTP response (405 is fine for MCP endpoints).

### Stdio MCPs
Check the command exists:
```bash
which <command>
# Example: which uv, which npx, etc.
```

Check any required directories:
```bash
ls -la /path/to/mcp/directory
```

Verify environment variables are set:
```bash
echo $REQUIRED_ENV_VAR
```

## Step 6: Check Environment Variable Expansion

If `.mcp.json` uses `${VARIABLE}` syntax:

```bash
# Verify variables are loaded in your shell
env | grep -E 'OPENAI_API_KEY|ANTHROPIC_API_KEY|GOOGLE_API_KEY'
```

**Common issue**: Environment variables need to be loaded BEFORE Claude Code starts.

Check shell config files:
- `~/.zshenv` (loaded first, best for env vars)
- `~/.zshrc` (loaded for interactive shells)
- `~/.bashrc` / `~/.bash_profile` (for bash)

## Step 7: Reset Project Approvals

If project-scoped MCPs need re-approval:

```bash
claude mcp reset-project-choices
```

Then restart Claude Code and approve the servers when prompted.

## Step 8: Verify Specific MCP Config

```bash
claude mcp get <server-name>
```

Shows:
- Scope (user, project, local)
- Connection status
- Configuration details
- Command/URL being used

## Common Issues & Solutions

### Issue: MCPs in .mcp.json don't load
**Root cause**: `.claude/settings.local.json` has `"enableAllProjectMcpServers": false`
**Solution**: Change to `true` or remove the file

### Issue: Environment variables not expanding
**Root cause**: Variables not set when Claude Code launches
**Solution**: Add variables to `~/.zshenv`, restart terminal AND Claude Code

### Issue: Duplicate MCP in user + project scope
**Root cause**: Same MCP name in both `~/.claude.json` and `.mcp.json`
**Solution**: Remove from one scope:
```bash
claude mcp remove <name> --scope user
# or
claude mcp remove <name> --scope project
```

### Issue: MCP shows as configured but "connecting..." forever
**Root cause**:
- Command doesn't exist or can't execute
- Network issues (for remote MCPs)
- Missing environment variables
- Incorrect command syntax

**Solution**: Test the command manually:
```bash
# For stdio MCP
<command> <args>

# For HTTP MCP
curl -I <url>
```

## MCP Configuration Hierarchy

1. **Enterprise/Managed** (highest priority, if configured)
2. **User scope** (`~/.claude.json`) - available in all projects
3. **Project scope** (`.mcp.json`) - requires approval/enablement
4. **Local scope** (user settings for specific project)

Settings at more specific levels override broader ones.

## Key Learnings

1. **Always check `.claude/settings.local.json` first** - this is the #1 blocker
2. **Project-scope MCPs require explicit enabling** - not automatic
3. **Environment variables must be loaded before Claude Code starts**
4. **Use `claude mcp list` and `claude mcp get` to verify** - don't trust files alone
5. **Test prerequisites independently** - verify commands exist, URLs respond, env vars are set

## Testing Checklist

Before declaring MCPs "should work":

- [ ] Run `claude mcp list` to see actual state
- [ ] Run `claude mcp get <name>` for each MCP
- [ ] Check `.claude/settings.local.json` for blocking settings
- [ ] Test HTTP endpoints with `curl -I`
- [ ] Test commands exist with `which`
- [ ] Verify env vars with `echo $VAR`
- [ ] Check directories exist with `ls -la`
- [ ] Test command execution manually

## References

- [MCP Documentation](https://docs.claude.com/en/docs/claude-code/mcp)
- Use `claude mcp --help` for all available commands
- Check logs in Claude Code with `--debug` flag if needed
