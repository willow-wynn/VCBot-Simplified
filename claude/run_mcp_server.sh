#!/bin/zsh

# VCBot MCP Server Wrapper
# Ensures proper working directory and environment

# Set working directory to the claude folder
cd /Users/wynndiaz/VCBot/claude

# Set PYTHONPATH to include VCBot directory
export PYTHONPATH="/Users/wynndiaz/VCBot:$PYTHONPATH"

# Log startup
echo "🚀 Starting VCBot MCP Server from wrapper..." >&2
echo "📁 Working directory: $(pwd)" >&2
echo "🐍 Python path: $PYTHONPATH" >&2

# Run the MCP server
exec /Users/wynndiaz/.pyenv/versions/3.12.3/bin/python mcp_server/server.py