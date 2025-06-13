# MCP Server Architecture for VCBot

## Overview

This document outlines the architecture for integrating VCBot with an MCP (Model Context Protocol) server, enabling Claude Desktop to interact with Discord through a standardized protocol.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude Desktop │────▶│   MCP Server     │────▶│  Discord Bot    │
│                 │◀────│  (FastMCP)       │◀────│  (VCBot)        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                         │
        │                        │                         ▼
        │                        │                 ┌───────────────┐
        │                        │                 │   Discord     │
        │                        └─────────────────│   Server      │
        │                                          └───────────────┘
        │
        └─── stdio/sse transport
```

## Directory Structure

```
/claude/
├── MCP_ARCHITECTURE.md       # This document
├── mcp_server/
│   ├── __init__.py
│   ├── server.py            # Main MCP server implementation
│   ├── discord_client.py    # Discord bot client wrapper
│   ├── tools/              # MCP tool implementations
│   │   ├── __init__.py
│   │   ├── messaging.py    # Discord messaging tools
│   │   ├── bills.py        # Bill search/fetch tools
│   │   ├── documents.py    # Document handling tools
│   │   ├── economy.py      # Economic system tools
│   │   └── stocks.py       # Stock market tools
│   └── resources/          # MCP resource providers
│       ├── __init__.py
│       ├── channels.py     # Channel history resources
│       └── knowledge.py    # Knowledge base resources
├── requirements.txt        # Python dependencies
├── config/
│   └── claude_desktop_config.json  # Claude Desktop configuration
└── README.md              # Setup and usage instructions
```

## Core Components

### 1. MCP Server (`server.py`)

The main server using FastMCP framework:

```python
from mcp.server.fastmcp import FastMCP
from discord_client import DiscordBotClient

# Initialize MCP server
mcp = FastMCP("VCBot-MCP")

# Initialize Discord client wrapper
discord_client = DiscordBotClient()
```

### 2. Discord Client Wrapper (`discord_client.py`)

A wrapper around the existing VCBot that provides a clean interface for MCP:

```python
class DiscordBotClient:
    """Wrapper around VCBot for MCP integration"""
    
    def __init__(self):
        self.bot_process = None
        self.api_client = None  # REST API client for Discord
        
    async def send_message(self, channel_id: str, content: str):
        """Send message to Discord channel"""
        
    async def search_bills(self, query: str, limit: int = 5):
        """Search bills using existing bot functionality"""
        
    async def get_economic_data(self):
        """Fetch current economic data"""
```

## MCP Tools

### 1. Messaging Tools (`tools/messaging.py`)

```python
@mcp.tool()
async def send_discord_message(
    channel_id: str,
    content: str,
    embed: dict = None
) -> dict:
    """Send a message to a Discord channel"""
    
@mcp.tool()
async def get_channel_history(
    channel_id: str,
    limit: int = 50,
    search_query: str = None
) -> list:
    """Fetch channel message history"""
    
@mcp.tool()
async def reply_to_message(
    message_id: str,
    channel_id: str,
    content: str
) -> dict:
    """Reply to a specific Discord message"""
```

### 2. Bill Management Tools (`tools/bills.py`)

```python
@mcp.tool()
async def search_bills(
    query: str,
    limit: int = 5,
    search_type: str = "keyword"
) -> list:
    """Search legislative bills"""
    
@mcp.tool()
async def get_bill_details(
    bill_name: str,
    include_pdf: bool = False
) -> dict:
    """Get detailed information about a bill"""
    
@mcp.tool()
async def add_bill(
    google_docs_link: str
) -> dict:
    """Add a new bill to the corpus"""
```

### 3. Document Tools (`tools/documents.py`)

```python
@mcp.tool()
async def fetch_document(
    url: str,
    extract_type: str = "full"
) -> dict:
    """Fetch and parse Google Docs or other documents"""
    
@mcp.tool()
async def analyze_document_impact(
    document_url: str,
    analysis_type: str = "economic"
) -> dict:
    """Analyze document for economic or policy impact"""
```

### 4. Economic Tools (`tools/economy.py`)

```python
@mcp.tool()
async def get_economic_report() -> dict:
    """Get current economic indicators and analysis"""
    
@mcp.tool()
async def trigger_economic_analysis(
    force_update: bool = False
) -> dict:
    """Trigger a new economic analysis"""
    
@mcp.tool()
async def set_economic_parameter(
    parameter: str,
    value: float,
    admin_key: str = None
) -> dict:
    """Set economic parameter (admin only)"""
```

### 5. Stock Market Tools (`tools/stocks.py`)

```python
@mcp.tool()
async def get_stock_price(
    symbol: str,
    include_history: bool = False
) -> dict:
    """Get current stock price and info"""
    
@mcp.tool()
async def get_market_overview() -> dict:
    """Get overall market status and sector performance"""
    
@mcp.tool()
async def execute_trade(
    user_id: str,
    action: str,  # "buy" or "sell"
    symbol: str,
    quantity: int
) -> dict:
    """Execute a stock trade for a user"""
```

## MCP Resources

### 1. Channel Resources (`resources/channels.py`)

```python
@mcp.resource("discord://channels")
async def list_available_channels() -> dict:
    """List all available Discord channels"""
    
@mcp.resource("discord://channels/{channel_id}/history")
async def get_channel_resource(channel_id: str) -> str:
    """Get channel history as a resource"""
```

### 2. Knowledge Resources (`resources/knowledge.py`)

```python
@mcp.resource("knowledge://{file_name}")
async def get_knowledge_file(file_name: str) -> str:
    """Access knowledge base files"""
    
@mcp.resource("knowledge://")
async def list_knowledge_files() -> dict:
    """List available knowledge files"""
```

## Integration Strategy

### 1. Minimal Bot Modifications

The MCP server acts as a **wrapper** around the existing bot:
- No changes required to core bot functionality
- MCP server communicates with bot through:
  - Direct function imports (for stateless operations)
  - REST API calls (for Discord operations)
  - Shared data files (for economic/stock data)

### 2. Communication Methods

#### Option A: Direct Integration (Recommended)
```python
# Import bot modules directly
import sys
sys.path.append('..')  # Add parent directory to path
from bill_utils import search_bills_keyword
from economic_utils import get_fresh_economic_report
```

#### Option B: REST API Bridge
```python
# Create lightweight FastAPI bridge in bot.py
from fastapi import FastAPI
api = FastAPI()

@api.get("/bills/search")
async def api_search_bills(query: str, limit: int = 5):
    return search_bills_keyword(query, limit)
```

#### Option C: Inter-Process Communication
```python
# Use Redis or similar for async communication
import redis
r = redis.Redis()

# MCP server publishes commands
r.publish('bot:command', json.dumps({
    'action': 'search_bills',
    'params': {'query': 'healthcare'}
}))
```

### 3. Authentication & Security

```python
# Environment variables
MCP_AUTH_TOKEN = os.getenv('MCP_AUTH_TOKEN')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_TOKEN')

# Admin verification
def verify_admin_access(user_id: str, admin_key: str) -> bool:
    """Verify admin permissions for sensitive operations"""
```

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "vcbot": {
      "command": "python",
      "args": [
        "/Users/wynndiaz/VCBot/claude/mcp_server/server.py"
      ],
      "env": {
        "DISCORD_TOKEN": "${DISCORD_TOKEN}",
        "GEMINI_API_KEY": "${GEMINI_API_KEY}",
        "MCP_AUTH_TOKEN": "${MCP_AUTH_TOKEN}"
      }
    }
  }
}
```

## Key Features

### 1. Real-Time Discord Integration
- Send messages to any authorized channel
- Fetch channel history with search
- Reply to specific messages
- Handle embeds and attachments

### 2. Comprehensive Bill Management
- Search bills by keyword
- Fetch bill details and PDFs
- Add new bills from Google Docs
- Track bill references

### 3. Economic Analysis Access
- Get current economic indicators
- Trigger new analyses
- View market sentiment
- Access historical data

### 4. Stock Market Operations
- Get real-time stock prices
- View market overview
- Execute trades (with auth)
- Access portfolio data

### 5. Document Processing
- Fetch Google Docs content
- Analyze policy documents
- Extract economic impacts
- Parse structured data

## Security Considerations

### 1. Channel Restrictions
```python
ALLOWED_CHANNELS = [
    'bot-helper',
    'official-rp-news',
    'house-floor',
    'senate-floor',
    # ... other authorized channels
]

def validate_channel_access(channel_id: str) -> bool:
    """Ensure MCP can only access authorized channels"""
```

### 2. Rate Limiting
```python
from functools import lru_cache
from datetime import datetime, timedelta

rate_limits = {}

def check_rate_limit(user_id: str, action: str) -> bool:
    """Implement rate limiting for API calls"""
```

### 3. Input Validation
```python
def sanitize_discord_content(content: str) -> str:
    """Sanitize content before sending to Discord"""
    # Remove @everyone, @here
    # Validate message length
    # Escape special characters
```

## Testing Strategy

### 1. Local Testing
```bash
# Test with MCP Inspector
mcp dev claude/mcp_server/server.py

# Test individual tools
python -m pytest claude/tests/test_tools.py
```

### 2. Integration Testing
```python
# Test file: claude/tests/test_integration.py
async def test_discord_message_flow():
    """Test complete message send/receive flow"""
    
async def test_bill_search_and_fetch():
    """Test bill search and PDF retrieval"""
```

## Deployment Options

### 1. Local Development
- Run MCP server alongside bot
- Use stdio transport
- Direct file access

### 2. Production Deployment
- Separate MCP server process
- Use HTTP+SSE transport
- Redis for async communication
- Docker containerization

## Future Enhancements

### 1. Advanced Features
- Voice channel integration
- Reaction handling
- Thread management
- Scheduled message support

### 2. AI Enhancements
- Prompt templates for common tasks
- Context-aware responses
- Multi-step workflows
- Batch operations

### 3. Monitoring
- Request logging
- Performance metrics
- Error tracking
- Usage analytics

## Benefits

1. **Unified Interface**: Claude can access all bot functionality through standardized MCP protocol
2. **Separation of Concerns**: MCP server isolated from bot core logic
3. **Extensibility**: Easy to add new tools and resources
4. **Security**: Controlled access through MCP authentication
5. **Testing**: Easier to test individual components
6. **Documentation**: Self-documenting through MCP tool descriptions

## Implementation Priority

### Phase 1: Core Functionality
1. Basic messaging tools
2. Bill search capabilities
3. Knowledge base access

### Phase 2: Economic Integration
1. Economic report access
2. Stock market data
3. Trading operations

### Phase 3: Advanced Features
1. Document analysis
2. Multi-channel operations
3. Workflow automation

This architecture provides a clean, secure, and extensible way to integrate VCBot with Claude Desktop through MCP, enabling powerful Discord automation capabilities while maintaining the simplicity of the existing bot design.