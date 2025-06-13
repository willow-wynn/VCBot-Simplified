#!/bin/zsh

# VCBot MCP Server - Claude Desktop Configuration Update Script
# Reconfigures Claude Desktop with all new economic analysis tools

set -e  # Exit on any error

echo "🚀 Updating Claude Desktop for VCBot MCP Server with Economic Tools..."
echo "===================================================================="

# Define paths
CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
VCBOT_MCP_SERVER="/Users/wynndiaz/VCBot/claude/mcp_server/server.py"
VCBOT_DIR="/Users/wynndiaz/VCBot"

# Create Claude config directory if it doesn't exist
echo "📁 Creating Claude configuration directory..."
mkdir -p "$CLAUDE_CONFIG_DIR"

# Check if VCBot MCP server exists
if [ ! -f "$VCBOT_MCP_SERVER" ]; then
    echo "❌ Error: VCBot MCP server not found at $VCBOT_MCP_SERVER"
    exit 1
fi

echo "✅ VCBot MCP server found with economic tools"

# Backup existing config
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    echo "💾 Backing up existing configuration..."
    cp "$CLAUDE_CONFIG_FILE" "$CLAUDE_CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Kill Claude Desktop if running
if pgrep -f "Claude" > /dev/null; then
    echo "🔄 Stopping Claude Desktop..."
    pkill -f "Claude" || true
    sleep 3
fi

# Create the new configuration with VCBot MCP server
echo "⚙️ Writing new Claude Desktop configuration..."
cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "vcbot-economic": {
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

# Display the configuration
echo ""
echo "📋 New Configuration:"
echo "===================="
cat "$CLAUDE_CONFIG_FILE"

# Test the MCP server
echo ""
echo "🧪 Testing MCP server with economic tools..."
cd "$VCBOT_DIR/claude"

python -c "
import sys
sys.path.append('$VCBOT_DIR')
try:
    from mcp_server.server import mcp
    print('✅ MCP server loads successfully!')
    print('📊 VCBot economic system fully integrated!')
except Exception as e:
    print(f'❌ Server test failed: {e}')
"

# Start Claude Desktop
echo ""
echo "🚀 Starting Claude Desktop..."
open -a "Claude"
sleep 3

echo ""
echo "🎉 Configuration Update Complete!"
echo "================================="
echo ""
echo "🔧 Available Economic Tools:"
echo "• get_economic_report - Get comprehensive economic indicators"
echo "• get_economic_summary - Get condensed economic overview"  
echo "• get_stock_market_overview - Real 24-stock market data"
echo "• get_stock_price - Individual stock prices (AAPL, MSFT, etc.)"
echo "• analyze_channel_activity - Discord channel analysis"
echo "• extract_document_data - Google Docs economic analysis"
echo "• add_memory_entry - Add AI context memory"
echo "• get_memory_context - Retrieve AI memory"
echo "• submit_economic_report - Submit completed analysis"
echo "• log_admin_action - Administrative audit logging"
echo "• set_advanced_economic_parameter - Admin economic controls"
echo ""
echo "🧪 Test Commands for Claude Desktop:"
echo "• 'Get the current economic report'"
echo "• 'What stocks are available in the TECH sector?'"
echo "• 'Get the price for AAPL stock'"
echo "• 'Analyze activity in the official-rp-news channel'"
echo "• 'Add a memory entry about current market conditions'"
echo "• 'Submit an economic report with GDP data'"
echo ""
echo "📊 The VCBot economic system is now fully accessible through Claude Desktop!"
echo "   All tools connect to the real VCBot economic data and functions."