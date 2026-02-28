#!/usr/bin/env bash
# Add an MCP server to a project's .mcp.json
# Usage: add-mcp.sh <project-dir> <preset>
# Presets: chrome-devtools, exa, anki, context7, svelte
set -euo pipefail

PROJECT_DIR="${1:?Usage: add-mcp.sh <project-dir> <preset>}"
PRESET="${2:?Usage: add-mcp.sh <project-dir> <preset>}"
MCP_FILE="$PROJECT_DIR/.mcp.json"

# Initialize .mcp.json if missing
if [[ ! -f "$MCP_FILE" ]]; then
  echo '{"mcpServers":{}}' > "$MCP_FILE"
fi

# Check if jq is available
if ! command -v jq &>/dev/null; then
  echo "Error: jq required. Install with: brew install jq" >&2
  exit 1
fi

case "$PRESET" in
  chrome-devtools)
    jq '.mcpServers["chrome-devtools"] = {"type":"stdio","command":"npx","args":["chrome-devtools-mcp@latest"]}' \
      "$MCP_FILE" > "$MCP_FILE.tmp" && mv "$MCP_FILE.tmp" "$MCP_FILE"
    ;;
  exa)
    jq '.mcpServers["exa"] = {"type":"http","url":"https://mcp.exa.ai/mcp"}' \
      "$MCP_FILE" > "$MCP_FILE.tmp" && mv "$MCP_FILE.tmp" "$MCP_FILE"
    ;;
  anki)
    jq '.mcpServers["anki"] = {"command":"npx","args":["-y","@ankimcp/anki-mcp-server","--stdio"],"env":{"ANKI_CONNECT_URL":"http://localhost:8765"}}' \
      "$MCP_FILE" > "$MCP_FILE.tmp" && mv "$MCP_FILE.tmp" "$MCP_FILE"
    ;;
  context7)
    jq '.mcpServers["context7"] = {"command":"npx","args":["-y","@upstash/context7-mcp"]}' \
      "$MCP_FILE" > "$MCP_FILE.tmp" && mv "$MCP_FILE.tmp" "$MCP_FILE"
    ;;
  svelte)
    jq '.mcpServers["svelte"] = {"type":"http","url":"https://mcp.svelte.dev/mcp"}' \
      "$MCP_FILE" > "$MCP_FILE.tmp" && mv "$MCP_FILE.tmp" "$MCP_FILE"
    ;;
  *)
    echo "Unknown preset: $PRESET" >&2
    echo "Available: chrome-devtools, exa, anki, context7, svelte" >&2
    exit 1
    ;;
esac

echo "Added $PRESET to $MCP_FILE"
