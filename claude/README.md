# VCBot MCP Integration

This directory contains the Model Context Protocol (MCP) server implementation for VCBot, enabling Claude Desktop to interact with your Discord bot through a standardized protocol.

## Overview

The MCP server acts as a bridge between Claude Desktop and VCBot, exposing comprehensive Discord functionality. This allows Claude to:

- 🔍 **Search and analyze bills** - Full-text search of legislative corpus with PDF access
- 📊 **Access economic data** - Real-time economic indicators and stock market information
- 💬 **Discord integration** - Send messages, read channel history, reply to messages
- 📚 **Knowledge base access** - Query rules, constitution, and procedural documents
- 🎯 **Administrative tools** - Execute bot commands and manage economic parameters
- 📝 **Document processing** - Fetch and analyze Google Docs for policy impact

## Architecture

```
Claude Desktop <--[MCP Protocol]--> MCP Server <--[Direct Import]--> VCBot
                                         |                              |
                                         v                              v
                                  Discord REST API                Discord Server
                                  (for messaging)                 (38 channels)
```

## 🚀 Quick Setup (Automated)

### Option 1: Automated Setup

```bash
cd /Users/wynndiaz/VCBot/claude
python setup.py
```

This will:
- ✅ Install all dependencies
- ✅ Create environment template
- ✅ Test the MCP server
- ✅ Configure Claude Desktop automatically
- ✅ Provide next steps

### Option 2: Manual Setup

If you prefer manual control:

## Available Tools

### Bill Management
- **search_bills** - Search legislative corpus by keywords
- **get_bill_details** - Get detailed information about specific bills
- **analyze_bill_impact** - Generate economic impact analysis

### Economic Data
- **get_economic_summary** - Current economic indicators
- **get_stock_market_overview** - Real-time market data
- **get_economic_report** - Comprehensive economic analysis

### Discord Integration
- **send_discord_message** - Send messages to channels
- **get_channel_history** - Fetch recent messages
- **list_available_channels** - See accessible channels

### Knowledge Base
- **get_knowledge_base_info** - List available documents
- **get_knowledge_file** - Access specific knowledge files

## Example Usage in Claude

Once configured, you can ask Claude things like:

- "Search for bills about healthcare reform"
- "What's the current economic situation?"
- "Check the latest messages in house-floor"
- "Analyze the economic impact of the Tax Reform Act"
- "Send a message to bot-helper channel"

## Implementation Approach

The MCP server uses a **wrapper approach**:

1. **Direct Imports** - Reuses existing VCBot modules (bill_utils, economic_utils, etc.)
2. **Minimal Code** - No duplication of bot logic
3. **REST API** - For Discord operations requiring live bot connection
4. **File Access** - Direct access to bot's data files

## File Structure

```
claude/
├── README.md                    # This file
├── MCP_ARCHITECTURE.md         # Detailed architecture documentation
├── MCP_IMPLEMENTATION_GUIDE.md # Step-by-step implementation guide
├── example_server.py           # Minimal working example
└── mcp_server/                 # Full implementation (to be created)
    ├── server.py               # Main MCP server
    ├── tools/                  # Tool implementations
    └── resources/              # Resource providers
```

## Next Steps

1. **Expand Tools** - Add more bot functionality
2. **Discord REST API** - Implement actual message sending
3. **Authentication** - Add security for admin commands
4. **Caching** - Improve performance with smart caching
5. **Error Handling** - Robust error messages
6. **Testing** - Comprehensive test suite

## Security Considerations

- ✅ Channel access restrictions enforced
- ✅ Rate limiting for API calls
- ✅ Input validation on all tools
- ✅ Admin commands require authentication
- ✅ No direct database access

## Development

### Adding New Tools

```python
@mcp.tool()
async def my_new_tool(param1: str, param2: int = 5) -> dict:
    """
    Tool description shown in Claude.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
    """
    # Implementation
    return {"result": "success"}
```

### Testing Tools

```bash
# Test individual tool
python -c "
import asyncio
from example_server import search_bills
result = asyncio.run(search_bills('tax', 3))
print(result)
"
```

## Troubleshooting

### Common Issues

1. **Module Import Errors**
   - Ensure you're in the `/claude` directory
   - Check PYTHONPATH includes parent directory

2. **Claude Can't Find Server**
   - Verify path in claude_desktop_config.json
   - Restart Claude Desktop after config changes

3. **Tools Not Working**
   - Check bot dependencies are installed
   - Verify environment variables are set
   - Check file permissions

### Debug Mode

```python
# Add to server.py for debugging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [VCBot Documentation](../README.md)

## Contributing

When adding new features:

1. Follow existing patterns
2. Add comprehensive docstrings
3. Include error handling
4. Update this README
5. Test with MCP Inspector

---

Built with ❤️ for Virtual Congress