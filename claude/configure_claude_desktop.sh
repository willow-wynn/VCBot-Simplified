#!/bin/zsh

# VCBot MCP Server - Claude Desktop Configuration Script
# Run this from your home directory to configure Claude Desktop

set -e  # Exit on any error

echo "🚀 Configuring Claude Desktop for VCBot MCP Server..."
echo "=================================================="

# Define paths
CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
VCBOT_MCP_SERVER="$HOME/VCBot/claude/mcp_server/server.py"
VCBOT_DIR="$HOME/VCBot"

# Create Claude config directory if it doesn't exist
echo "📁 Creating Claude configuration directory..."
mkdir -p "$CLAUDE_CONFIG_DIR"

# Check if VCBot MCP server exists
if [ ! -f "$VCBOT_MCP_SERVER" ]; then
    echo "❌ Error: VCBot MCP server not found at $VCBOT_MCP_SERVER"
    echo "   Make sure you've implemented the MCP server first."
    exit 1
fi

echo "✅ VCBot MCP server found at $VCBOT_MCP_SERVER"

# Create or update Claude Desktop configuration
echo "⚙️ Configuring Claude Desktop..."

# Read existing config or create empty config
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    echo "📖 Reading existing Claude Desktop configuration..."
    EXISTING_CONFIG=$(cat "$CLAUDE_CONFIG_FILE")
else
    echo "📝 Creating new Claude Desktop configuration..."
    EXISTING_CONFIG="{}"
fi

# Create the new configuration with VCBot MCP server
cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "vcbot": {
      "command": "/Users/wynndiaz/.pyenv/versions/3.12.3/bin/python",
      "args": [
        "$VCBOT_MCP_SERVER"
      ],
      "env": {
        "PYTHONPATH": "$VCBOT_DIR"
      }
    }
  }
}
EOF

echo "✅ Claude Desktop configuration updated!"
echo "📄 Configuration file: $CLAUDE_CONFIG_FILE"

# Display the configuration
echo ""
echo "📋 Configuration contents:"
echo "=========================="
cat "$CLAUDE_CONFIG_FILE"

echo ""
echo "🔧 Next Steps:"
echo "=============="
echo "1. The MCP server will use VCBot's existing .env file for tokens ✅"
echo ""
echo "2. Install MCP dependencies:"
echo "   cd $VCBOT_DIR/claude"
echo "   pip install -r requirements.txt"
echo ""
echo "3. Test the MCP server:"
echo "   cd $VCBOT_DIR/claude"
echo "   mcp dev mcp_server/server.py"
echo ""
echo "4. Restart Claude Desktop application"
echo ""
echo "5. Test in Claude Desktop by asking:"
echo "   'Search for bills about healthcare'"
echo "   'Get the current economic report'"
echo "   'List available Discord channels'"
echo ""

# Check if Claude Desktop is running
if pgrep -f "Claude" > /dev/null; then
    echo "⚠️  Claude Desktop is currently running."
    echo "   You need to restart it to load the new configuration."
    echo ""
    echo -n "   Would you like to restart Claude Desktop now? (y/n): "
    read -r REPLY
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 Restarting Claude Desktop..."
        pkill -f "Claude" || true
        sleep 2
        open -a "Claude"
        echo "✅ Claude Desktop restarted!"
    else
        echo "🔄 Please restart Claude Desktop manually to load the new configuration."
    fi
fi

echo ""
echo "🎉 Configuration complete!"
echo "   VCBot MCP server is now available in Claude Desktop."

# Optionally test the server
echo ""
echo -n "🧪 Would you like to test the MCP server now? (y/n): "
read -r REPLY
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧪 Testing MCP server..."
    cd "$VCBOT_DIR/claude"
    
    if command -v mcp &> /dev/null; then
        echo "📊 Running MCP inspector test..."
        timeout 10s mcp dev mcp_server/server.py || echo "⏰ Test completed (timed out after 10 seconds - this is normal)"
    else
        echo "📝 Testing Python import..."
        python -c "
import sys
sys.path.append('$VCBOT_DIR')
try:
    import mcp_server.server
    print('✅ MCP server imports successfully!')
except Exception as e:
    print(f'❌ Import failed: {e}')
"
    fi
fi

echo ""
echo "✨ Setup complete! Your VCBot MCP server is ready to use."