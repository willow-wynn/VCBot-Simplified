#!/bin/zsh

echo "🔄 Force resetting Claude Desktop MCP configuration..."

# Kill Claude Desktop
pkill -f "Claude" || echo "Claude not running"
sleep 2

# Clear MCP logs
rm -f ~/Library/Logs/Claude/mcp-server-vcbot.log
echo "🗑️ Cleared old MCP logs"

# Create a completely clean config
CLAUDE_CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

cat > "$CLAUDE_CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "vcbot-simple": {
      "command": "/Users/wynndiaz/.pyenv/versions/3.12.3/bin/python",
      "args": [
        "/Users/wynndiaz/VCBot/claude/simple_server.py"
      ],
      "cwd": "/Users/wynndiaz/VCBot",
      "env": {
        "PYTHONPATH": "/Users/wynndiaz/VCBot"
      }
    }
  }
}
EOF

echo "✅ Created clean Claude Desktop config"
echo "📄 Config: $CLAUDE_CONFIG_FILE"
echo ""
echo "🚀 Starting Claude Desktop..."
open -a "Claude"
echo ""
echo "⏳ Wait 5 seconds then test with: 'Hello world'"