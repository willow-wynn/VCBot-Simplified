# MCP Server Implementation Guide for VCBot

## Quick Start Example

Here's a minimal working MCP server that integrates with VCBot:

### 1. Basic Server Structure (`claude/mcp_server/server.py`)

```python
#!/usr/bin/env python3
"""
VCBot MCP Server - Enables Claude Desktop to interact with Discord
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directory to path for VCBot imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# FastMCP imports
from mcp.server.fastmcp import FastMCP

# Import VCBot modules directly
import config
import bill_utils
import economic_utils
import file_utils
from ai_tools import fetch_google_doc_content

# Initialize MCP server
mcp = FastMCP("VCBot-MCP", version="1.0.0")

# Store Discord client reference (will be set when needed)
discord_client = None

# ==================== TOOLS ====================

# === Messaging Tools ===

@mcp.tool()
async def send_discord_message(
    channel_name: str,
    content: str,
    embed_title: Optional[str] = None,
    embed_description: Optional[str] = None,
    embed_color: Optional[int] = 0x2ecc71
) -> Dict[str, Any]:
    """
    Send a message to a Discord channel.
    
    Args:
        channel_name: Name of the Discord channel (e.g., "bot-helper", "official-rp-news")
        content: Message content (can be empty if only sending embed)
        embed_title: Optional embed title
        embed_description: Optional embed description
        embed_color: Optional embed color (hex value)
    
    Returns:
        Success status and message ID
    """
    # For now, return a mock response
    # In real implementation, this would use Discord REST API or bot connection
    return {
        "success": True,
        "message": f"Would send to #{channel_name}: {content}",
        "embed": {"title": embed_title, "description": embed_description} if embed_title else None
    }

@mcp.tool()
async def get_channel_history(
    channel_name: str,
    limit: int = 20,
    search_term: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch recent messages from a Discord channel.
    
    Args:
        channel_name: Name of the Discord channel
        limit: Number of messages to fetch (max 50)
        search_term: Optional search term to filter messages
    
    Returns:
        List of messages with author, content, and timestamp
    """
    # Validate limit
    limit = min(limit, 50)
    
    # Mock implementation
    return [
        {
            "author": "ExampleUser",
            "content": f"Example message from {channel_name}",
            "timestamp": "2024-01-01T12:00:00Z",
            "id": "123456789"
        }
    ]

# === Bill Management Tools ===

@mcp.tool()
async def search_bills(
    query: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search for bills in the legislative corpus.
    
    Args:
        query: Search terms (keywords work best, e.g., "healthcare", "tax credit")
        limit: Maximum number of results (max 10)
    
    Returns:
        List of bills with title, summary, and relevance score
    """
    # Use existing bill search functionality
    limit = min(limit, 10)
    results = bill_utils.search_bills_keyword(query, limit)
    
    # Format results for MCP
    formatted_results = []
    for result in results:
        formatted_results.append({
            "title": result.get("title", result.get("filename", "Unknown")),
            "filename": result.get("filename", ""),
            "score": result.get("score", 0),
            "summary": result.get("summary", "No summary available"),
            "pdf_available": (config.BILL_PDF_DIR / f"{result.get('filename', '')}.pdf").exists()
        })
    
    return formatted_results

@mcp.tool()
async def get_bill_details(
    bill_title: str,
    include_full_text: bool = False
) -> Dict[str, Any]:
    """
    Get detailed information about a specific bill.
    
    Args:
        bill_title: Title or filename of the bill
        include_full_text: Whether to include the full bill text
    
    Returns:
        Detailed bill information including metadata and optionally full text
    """
    # Search for the bill first
    results = bill_utils.search_bills_keyword(bill_title, 1)
    
    if not results:
        return {"error": "Bill not found"}
    
    bill = results[0]
    filename = bill.get("filename", "")
    
    # Get bill metadata
    json_path = config.BILL_JSON_DIR / f"{filename}.json"
    metadata = {}
    if json_path.exists():
        with open(json_path, 'r') as f:
            metadata = json.load(f)
    
    # Prepare response
    response = {
        "title": bill.get("title", filename),
        "filename": filename,
        "metadata": metadata,
        "pdf_exists": (config.BILL_PDF_DIR / f"{filename}.pdf").exists(),
        "text_exists": (config.BILL_TEXT_DIR / f"{filename}.txt").exists()
    }
    
    # Include full text if requested
    if include_full_text:
        text_path = config.BILL_TEXT_DIR / f"{filename}.txt"
        if text_path.exists():
            with open(text_path, 'r') as f:
                response["full_text"] = f.read()
    
    return response

# === Economic Tools ===

@mcp.tool()
async def get_economic_report() -> Dict[str, Any]:
    """
    Get the current economic report with all indicators.
    
    Returns:
        Comprehensive economic data including GDP, inflation, unemployment, and market sentiment
    """
    # Use existing economic reporting
    report = economic_utils.get_fresh_economic_report()
    
    # Add some formatting for better readability
    return {
        "summary": {
            "gdp_growth": f"{report['gdp']['quarterly_growth_percent']}%",
            "inflation_rate": f"{report['inflation']['yoy_percent']}%",
            "unemployment_rate": f"{report['unemployment']['rate_percent']}%",
            "market_confidence": f"{report['sentiment']['confidence_percent']}%"
        },
        "full_report": report,
        "last_updated": report.get("metadata", {}).get("last_updated", "Unknown")
    }

@mcp.tool()
async def get_stock_market_overview() -> Dict[str, Any]:
    """
    Get current stock market overview with sector performance.
    
    Returns:
        Market parameters, sector performance, and top movers
    """
    try:
        # Check if stock market module is available
        import stock_market
        market = stock_market.get_stock_market()
        
        if not market:
            return {"error": "Stock market not initialized"}
        
        # Get market data
        overview = {
            "market_status": "open" if market.is_market_open() else "closed",
            "parameters": {
                "trend": market.market_params.get("trend_direction", 0),
                "volatility": market.market_params.get("volatility", 0),
                "sentiment": market.market_params.get("market_sentiment", 0)
            },
            "sectors": {},
            "last_update": market.last_update.isoformat() if market.last_update else "Never"
        }
        
        # Get sector performance
        for sector_name, stocks in market.sectors.items():
            sector_prices = []
            for symbol in stocks:
                price_data = market.get_stock_price(symbol)
                if price_data and "error" not in price_data:
                    sector_prices.append(price_data["current"])
            
            if sector_prices:
                avg_price = sum(sector_prices) / len(sector_prices)
                overview["sectors"][sector_name] = {
                    "average_price": round(avg_price, 2),
                    "stock_count": len(stocks),
                    "stocks": stocks
                }
        
        return overview
        
    except ImportError:
        return {"error": "Stock market module not available"}

# === Document Tools ===

@mcp.tool()
async def fetch_google_doc(
    doc_url: str,
    extract_sections: bool = False
) -> Dict[str, Any]:
    """
    Fetch and parse a Google Doc.
    
    Args:
        doc_url: Google Docs URL
        extract_sections: Whether to extract document sections
    
    Returns:
        Document content and metadata
    """
    try:
        # Use existing Google Docs fetcher
        content = await fetch_google_doc_content(doc_url)
        
        response = {
            "url": doc_url,
            "content": content,
            "length": len(content),
            "doc_id": doc_url.split('/d/')[1].split('/')[0] if '/d/' in doc_url else None
        }
        
        # Extract sections if requested
        if extract_sections and content:
            sections = []
            lines = content.split('\n')
            current_section = None
            
            for line in lines:
                if line.strip() and (line.isupper() or line.startswith('#')):
                    if current_section:
                        sections.append(current_section)
                    current_section = {"title": line.strip(), "content": []}
                elif current_section:
                    current_section["content"].append(line)
            
            if current_section:
                sections.append(current_section)
            
            response["sections"] = sections
        
        return response
        
    except Exception as e:
        return {"error": f"Failed to fetch document: {str(e)}"}

# === Knowledge Base Tools ===

@mcp.tool()
async def get_knowledge_file(
    file_name: str
) -> Dict[str, Any]:
    """
    Access knowledge base files (rules, constitution, etc).
    
    Args:
        file_name: Name of knowledge file ("rules", "constitution", "house_rules", "senate_rules")
    
    Returns:
        File content and metadata
    """
    try:
        content = file_utils.read_knowledge_file(file_name)
        
        if "Error" in content:
            return {"error": content}
        
        return {
            "file_name": file_name,
            "content": content,
            "length": len(content),
            "available_files": ["rules", "constitution", "house_rules", "senate_rules"]
        }
        
    except Exception as e:
        return {"error": f"Failed to read knowledge file: {str(e)}"}

# ==================== RESOURCES ====================

@mcp.resource("knowledge://list")
async def list_knowledge_files() -> str:
    """List all available knowledge base files."""
    files = {
        "rules": "Virtual Congress general rules and procedures",
        "constitution": "Virtual Congress Constitution",
        "house_rules": "House of Representatives specific rules",
        "senate_rules": "Senate specific rules"
    }
    return json.dumps(files, indent=2)

@mcp.resource("bills://recent")
async def get_recent_bills() -> str:
    """Get list of recently added bills."""
    # Get recent bills from the JSON directory
    json_files = sorted(
        config.BILL_JSON_DIR.glob("*.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )[:10]  # Last 10 bills
    
    bills = []
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                bills.append({
                    "title": data.get("title", json_file.stem),
                    "filename": json_file.stem,
                    "modified": json_file.stat().st_mtime
                })
        except:
            continue
    
    return json.dumps(bills, indent=2)

@mcp.resource("economy://current")
async def get_current_economy() -> str:
    """Get current economic indicators as a resource."""
    report = economic_utils.get_fresh_economic_report()
    return json.dumps(report, indent=2)

# ==================== PROMPTS ====================

@mcp.prompt()
async def analyze_bill_impact(
    bill_title: str
) -> List[Dict[str, str]]:
    """
    Generate a prompt for analyzing a bill's potential impact.
    
    Args:
        bill_title: Title of the bill to analyze
        
    Returns:
        Prompt messages for economic impact analysis
    """
    # Get bill details
    bill_details = await get_bill_details(bill_title, include_full_text=True)
    
    if "error" in bill_details:
        return [{"role": "user", "content": f"Error: Could not find bill '{bill_title}'"}]
    
    # Get current economic data
    econ_report = await get_economic_report()
    
    # Build analysis prompt
    messages = [
        {
            "role": "system",
            "content": "You are an expert policy analyst evaluating legislative proposals for Virtual Congress."
        },
        {
            "role": "user",
            "content": f"""Please analyze the following bill for its potential economic and policy impacts:

**Bill Title:** {bill_details['title']}

**Bill Text:**
{bill_details.get('full_text', 'Text not available')}

**Current Economic Context:**
- GDP Growth: {econ_report['summary']['gdp_growth']}
- Inflation Rate: {econ_report['summary']['inflation_rate']}
- Unemployment: {econ_report['summary']['unemployment_rate']}
- Market Confidence: {econ_report['summary']['market_confidence']}

Please provide:
1. Summary of the bill's main provisions
2. Potential economic impacts (positive and negative)
3. Affected sectors and constituencies
4. Implementation challenges
5. Overall recommendation"""
        }
    ]
    
    return messages

@mcp.prompt()
async def draft_discord_announcement(
    topic: str,
    channel: str = "official-rp-news"
) -> List[Dict[str, str]]:
    """
    Generate a prompt for drafting Discord announcements.
    
    Args:
        topic: Topic of the announcement
        channel: Target Discord channel
        
    Returns:
        Prompt messages for announcement drafting
    """
    # Get recent messages from the channel for context
    recent_messages = await get_channel_history(channel, limit=5)
    
    messages = [
        {
            "role": "system",
            "content": f"You are drafting an official announcement for the Virtual Congress Discord server, specifically for the #{channel} channel."
        },
        {
            "role": "user",
            "content": f"""Draft a professional announcement about: {topic}

Channel context - Recent messages:
{json.dumps(recent_messages, indent=2)}

Guidelines:
- Keep it concise and professional
- Use appropriate Discord formatting (bold, italics, etc)
- Include relevant mentions (@everyone, @here, roles) if needed
- Add appropriate emojis for visual appeal
- Structure with clear sections if needed"""
        }
    ]
    
    return messages

# ==================== MAIN ====================

if __name__ == "__main__":
    # Run the MCP server
    import mcp
    mcp.run()
```

### 2. Requirements File (`claude/requirements.txt`)

```
mcp[cli]>=1.0.0
fastmcp>=2.0.0
discord.py>=2.3.0
aiohttp>=3.9.0
python-dotenv>=1.0.0
```

### 3. Claude Desktop Configuration (`claude/config/claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "vcbot": {
      "command": "python",
      "args": [
        "-m",
        "mcp_server.server"
      ],
      "cwd": "/Users/wynndiaz/VCBot/claude",
      "env": {
        "PYTHONPATH": "/Users/wynndiaz/VCBot",
        "DISCORD_TOKEN": "${DISCORD_TOKEN}",
        "GEMINI_API_KEY": "${GEMINI_API_KEY}"
      }
    }
  }
}
```

### 4. Setup Instructions (`claude/README.md`)

```markdown
# VCBot MCP Server Setup

## Installation

1. **Install Python dependencies:**
   ```bash
   cd /Users/wynndiaz/VCBot/claude
   pip install -r requirements.txt
   ```

2. **Configure Claude Desktop:**
   - Copy the configuration from `config/claude_desktop_config.json`
   - Add it to your Claude Desktop settings at:
     `~/Library/Application Support/Claude/claude_desktop_config.json`

3. **Set environment variables:**
   Create a `.env` file in the claude directory:
   ```
   DISCORD_TOKEN=your_discord_token
   GEMINI_API_KEY=your_gemini_api_key
   ```

## Testing

1. **Test with MCP Inspector:**
   ```bash
   cd /Users/wynndiaz/VCBot/claude
   mcp dev mcp_server/server.py
   ```

2. **Test individual tools:**
   ```python
   python -m mcp_server.server
   ```

## Usage in Claude Desktop

Once configured, you can use commands like:

- "Search for bills about healthcare"
- "Get the current economic report"
- "Check what's happening in the house-floor channel"
- "Analyze the impact of the Tax Reform Act"

## Available Tools

### Messaging
- `send_discord_message` - Send messages to Discord channels
- `get_channel_history` - Fetch recent channel messages

### Bills
- `search_bills` - Search legislative corpus
- `get_bill_details` - Get detailed bill information

### Economy
- `get_economic_report` - Current economic indicators
- `get_stock_market_overview` - Stock market status

### Documents
- `fetch_google_doc` - Fetch Google Docs content
- `get_knowledge_file` - Access knowledge base

## Troubleshooting

1. **Server won't start:**
   - Check Python path in configuration
   - Verify all dependencies are installed
   - Check environment variables

2. **Can't find VCBot modules:**
   - Ensure PYTHONPATH is set correctly
   - Verify you're in the right directory

3. **Discord operations fail:**
   - Check DISCORD_TOKEN is valid
   - Verify bot has necessary permissions
```

## Key Implementation Details

### 1. Direct Import Strategy

The MCP server directly imports VCBot modules rather than creating a separate implementation:

```python
# Import existing VCBot functionality
import bill_utils
import economic_utils
import file_utils
```

This ensures:
- No code duplication
- Consistent behavior
- Easy maintenance

### 2. Async Discord Operations

For Discord operations that require the bot to be online:

```python
class DiscordAPIClient:
    """REST API client for Discord operations"""
    
    def __init__(self, token: str):
        self.token = token
        self.session = aiohttp.ClientSession()
    
    async def send_message(self, channel_id: str, content: str):
        """Send message via Discord REST API"""
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {"Authorization": f"Bot {self.token}"}
        data = {"content": content}
        
        async with self.session.post(url, headers=headers, json=data) as resp:
            return await resp.json()
```

### 3. Error Handling

```python
def handle_mcp_errors(func):
    """Decorator for consistent error handling"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return {
                "error": str(e),
                "type": type(e).__name__,
                "function": func.__name__
            }
    return wrapper
```

### 4. Resource Caching

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=100)
def get_cached_bill_data(filename: str) -> dict:
    """Cache bill data to reduce file I/O"""
    # Implementation
```

## Testing the Integration

### 1. Unit Tests (`claude/tests/test_tools.py`)

```python
import pytest
from mcp_server.server import search_bills, get_economic_report

async def test_bill_search():
    """Test bill search functionality"""
    results = await search_bills("healthcare", limit=3)
    assert isinstance(results, list)
    assert len(results) <= 3

async def test_economic_report():
    """Test economic report generation"""
    report = await get_economic_report()
    assert "summary" in report
    assert "gdp_growth" in report["summary"]
```

### 2. Integration Tests

```python
async def test_full_workflow():
    """Test a complete workflow"""
    # Search for a bill
    bills = await search_bills("tax", limit=1)
    assert bills
    
    # Get bill details
    details = await get_bill_details(bills[0]["title"])
    assert "metadata" in details
    
    # Analyze impact
    prompt = await analyze_bill_impact(bills[0]["title"])
    assert prompt
```

## Security Best Practices

### 1. Input Validation

```python
ALLOWED_CHANNELS = {
    "bot-helper", "official-rp-news", "house-floor", 
    "senate-floor", "virtual-congress-chat"
}

def validate_channel(channel_name: str) -> bool:
    """Validate channel access"""
    return channel_name in ALLOWED_CHANNELS
```

### 2. Rate Limiting

```python
from collections import defaultdict
from time import time

rate_limits = defaultdict(lambda: {"count": 0, "reset": time()})

def check_rate_limit(user_id: str, limit: int = 10, window: int = 60):
    """Simple rate limiting implementation"""
    now = time()
    user_limits = rate_limits[user_id]
    
    if now > user_limits["reset"]:
        user_limits["count"] = 0
        user_limits["reset"] = now + window
    
    if user_limits["count"] >= limit:
        return False
    
    user_limits["count"] += 1
    return True
```

## Next Steps

1. **Implement Discord REST API client** for actual message sending
2. **Add authentication** for admin commands
3. **Implement caching** for frequently accessed data
4. **Add comprehensive logging** for debugging
5. **Create batch operations** for efficiency
6. **Build automated tests** for all tools

This implementation guide provides a solid foundation for building the MCP server integration with VCBot, allowing Claude Desktop to interact seamlessly with your Discord bot's functionality.