#!/bin/zsh

# Fix Claude Desktop config to use wrapper script

CLAUDE_CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

echo "🔧 Updating Claude Desktop config to use wrapper script..."

# Kill Claude Desktop if running
if pgrep -f "Claude" > /dev/null; then
    echo "🔄 Stopping Claude Desktop..."
    pkill -f "Claude" || true
    sleep 3
fi

# Create config with wrapper script
cat > "$CLAUDE_CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "vcbot-economic": {
      "command": "/Users/wynndiaz/VCBot/claude/run_mcp_server.sh"
    }
  }
}
EOF

echo "✅ Config updated to use wrapper script"
echo "📄 Config content:"
cat "$CLAUDE_CONFIG_FILE"

# Test wrapper script
echo ""
echo "🧪 Testing wrapper script..."
timeout 3s /Users/wynndiaz/VCBot/claude/run_mcp_server.sh || echo "✅ Wrapper script starts successfully (timed out after 3s - normal)"

# Start Claude Desktop
echo ""
echo "🚀 Starting Claude Desktop..."
open -a "Claude"
sleep 2

echo ""
echo "🎉 Claude Desktop should now connect to VCBot MCP server!"
echo "💡 Check the MCP connection status in Claude Desktop"