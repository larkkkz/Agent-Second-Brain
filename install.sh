#!/usr/bin/env bash
# One-paste installer for second-brain-mcp (macOS/Linux).
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/larkkkz/Agent-Second-Brain/main/install.sh) [config_path] [vault_path]
set -euo pipefail

REPO_URL="https://github.com/larkkkz/Agent-Second-Brain"
CONFIG="${1:-$HOME/.claude.json}"
VAULT="${2:-${SECOND_BRAIN_VAULT:-$HOME/SecondBrain}}"

echo "second-brain-mcp installer"
echo "Config file: $CONFIG"
echo "Vault location: $VAULT"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found — installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to update your MCP client's config. Please install Python 3 and re-run." >&2
  exit 1
fi

if [ -f "$CONFIG" ]; then
  cp "$CONFIG" "$CONFIG.bak-secondbrain-$(date +%s)"
  echo "Backed up existing config."
fi

python3 - "$CONFIG" "$REPO_URL" "$VAULT" <<'PY'
import json
import os
import sys

config_path, repo_url, vault = sys.argv[1], sys.argv[2], sys.argv[3]

if os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
    data = {}

servers = data.get("mcpServers", {})
servers["second-brain"] = {
    "type": "stdio",
    "command": "uvx",
    "args": ["--from", f"git+{repo_url}", "second-brain-mcp"],
    "env": {"SECOND_BRAIN_VAULT": vault},
}
data["mcpServers"] = servers

with open(config_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"Registered 'second-brain' MCP server in {config_path}")
PY

echo ""
echo "Done. Restart your MCP client (e.g. Claude Code), then approve the 'second-brain' server"
echo "the first time it's used (run /mcp in Claude Code to approve it)."
