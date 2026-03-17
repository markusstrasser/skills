---
name: browse
description: Persistent headless browser daemon for web interaction, QA, and scraping. Wraps gstack's browse binary (Playwright-based, Bun-compiled). Use for automated QA workflows, web testing, screenshot verification, and interactive page exploration. Replaces stateless MCP browser calls for multi-step workflows.
argument-hint: [URL to navigate to, or "status" to check daemon]
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# Browse — Persistent Browser Daemon

## Setup

```bash
B="$HOME/Projects/gstack-fork/browse/dist/browse"
```

Verify daemon is running: `$B status`. If not running, it auto-starts on first command.

Install Playwright browsers (first time only): `cd ~/Projects/gstack-fork/browse && bunx playwright install chromium`

## Core Workflow

### 1. Navigate
```bash
$B goto "https://example.com"
```

### 2. Snapshot (get interactive refs)
```bash
$B snapshot -i          # interactive: shows @e1, @e2... refs for clickable elements
$B snapshot -D          # diff against previous snapshot (detect changes)
$B snapshot -a          # annotated screenshot with ref labels
$B snapshot -C          # find non-ARIA clickable elements (@c refs)
```

The `-i` flag is key: it generates `@e1`, `@e2`... references that map to Playwright Locators. These refs persist until the next snapshot.

### 3. Interact via refs
```bash
$B click @e3            # click element
$B fill @e4 "value"     # fill input
$B hover @e1            # hover
$B select @e2 "option"  # select dropdown
```

### 4. Inspect
```bash
$B text                 # full page text
$B links                # all links
$B forms                # form elements
$B accessibility        # accessibility tree
$B js "document.title"  # run JS
$B console              # read console logs
$B network              # network requests
```

### 5. Visual evidence
```bash
$B screenshot path.png              # full page
$B screenshot --viewport page.png   # viewport only
$B screenshot @e1 element.png       # specific element
$B pdf output.pdf                   # save as PDF
```

## QA Workflow Pattern

For finding and verifying bugs:

```
1. $B goto <url>
2. $B snapshot -i                    # get interactive map
3. $B click @eN                      # interact
4. $B snapshot -D                    # diff: what changed?
5. $B screenshot evidence.png        # capture evidence
6. Repeat 3-5 for each interaction path
```

**Verification rule:** Every bug finding must be reproduced twice. Run the interaction sequence again to confirm. Screenshot both runs.

## Multi-Tab Workflows
```bash
$B newtab "https://other-page.com"  # open new tab
$B tabs                              # list open tabs
$B tab 2                             # switch to tab 2
$B closetab                          # close current tab
```

## Authentication
```bash
# Import cookies from browser
$B cookie-import-browser chrome --domain example.com

# Or from JSON file
$B cookie-import cookies.json

# Set individual cookies/headers
$B cookie "session=abc123"
$B header "Authorization: Bearer token"
```

## Server Management
```bash
$B status                # check if daemon running
$B stop                  # stop daemon
$B restart               # restart daemon
$B viewport 1920x1080    # set viewport size
$B useragent "..."       # set user agent
```

## Comparison
```bash
$B diff "https://v1.example.com" "https://v2.example.com"
```

## Multi-Step Chains

For complex sequences, pipe JSON to `chain`:
```bash
echo '[{"goto":"url"},{"snapshot":"-i"},{"click":"@e1"}]' | $B chain
```

## Key Differences from MCP Browser Tools

| Feature | `browse` daemon | `mcp__claude-in-chrome__*` |
|---------|----------------|---------------------------|
| State | Persistent (daemon) | Stateless per call |
| Refs | @e1 system (Locators) | Tab IDs + selectors |
| Accessibility | Built-in tree | Separate tool |
| Diffs | `snapshot -D` | Manual comparison |
| Auth | Cookie import from browser | Requires manual setup |
| Speed | Sub-100ms after first call | MCP overhead per call |

**When to use which:** Use `browse` for multi-step QA workflows, automated testing, and anything needing state across interactions. Use MCP browser tools for quick one-off page reads where daemon overhead isn't worth it.

$ARGUMENTS
