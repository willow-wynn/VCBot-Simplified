#!/usr/bin/env python3
"""
Minimal example MCP server for VCBot
This demonstrates the basic structure and key tools.
"""

import os
import sys
from pathlib import Path

# Add parent directory to Python path for VCBot imports
sys.path.append(str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
import bill_utils
import economic_utils
import config

# Create MCP server instance
mcp = FastMCP(
    "VCBot-MCP",
    version="0.1.0",
    description="MCP server for VCBot Discord integration"
)

# ===== Simple Tools =====

@mcp.tool()
async def search_bills(query: str, limit: int = 5) -> dict:
    """
    Search for bills containing specific keywords.
    
    Args:
        query: Search terms (e.g., 'healthcare', 'tax reform')
        limit: Maximum results to return (default: 5, max: 10)
    
    Returns:
        Dictionary with search results and metadata
    """
    # Enforce limit
    limit = min(limit, 10)
    
    # Use existing bill search
    results = bill_utils.search_bills_keyword(query, limit)
    
    return {
        "query": query,
        "count": len(results),
        "results": results
    }

@mcp.tool()
async def get_economic_summary() -> dict:
    """
    Get a summary of current economic indicators.
    
    Returns:
        Current economic data including GDP, inflation, unemployment
    """
    report = economic_utils.econ_data.get_fresh_economic_report()
    
    # Extract key metrics
    summary = {
        "gdp": {
            "current": report["gdp"]["current_gdp"],
            "growth": report["gdp"]["quarterly_growth_percent"]
        },
        "inflation": {
            "rate": report["inflation"]["yoy_percent"],
            "fed_rate": report["inflation"]["federal_funds_rate"]
        },
        "unemployment": {
            "rate": report["unemployment"]["rate_percent"],
            "claims": report["unemployment"]["jobless_claims"]
        },
        "sentiment": {
            "confidence": report["sentiment"]["confidence_percent"],
            "anxiety": report["sentiment"]["anxiety_index_percent"]
        }
    }
    
    return summary

@mcp.tool()
async def list_available_channels() -> dict:
    """
    List Discord channels the bot can access.
    
    Returns:
        Dictionary of channel categories and names
    """
    # These would come from config in real implementation
    channels = {
        "bot_channels": ["bot-helper"],
        "news_channels": ["official-rp-news", "virtual-congress-chat"],
        "congress_channels": ["house-floor", "senate-floor", "committee-announcements"],
        "executive_channels": ["presidential-announcements", "bills-signed-into-law"]
    }
    
    return channels

@mcp.tool()
async def get_knowledge_base_info() -> dict:
    """
    Get information about available knowledge base files.
    
    Returns:
        List of available knowledge files and their descriptions
    """
    knowledge_files = {
        "rules": "General Virtual Congress rules and procedures",
        "constitution": "The Virtual Congress Constitution",
        "house_rules": "House of Representatives specific rules",
        "senate_rules": "Senate specific rules"
    }
    
    # Check which files actually exist
    available = {}
    for key, description in knowledge_files.items():
        file_path = config.KNOWLEDGE_DIR / f"{key}.txt"
        if file_path.exists():
            available[key] = {
                "description": description,
                "size": file_path.stat().st_size,
                "exists": True
            }
    
    return available

# ===== Resources =====

@mcp.resource("vcbot://status")
async def get_bot_status() -> str:
    """Get current bot configuration and status."""
    status = {
        "bot_id": config.BOT_ID,
        "guild_id": config.GUILD_ID,
        "channels": {
            "records": config.RECORDS_CHANNEL,
            "news": config.NEWS_CHANNEL,
            "clerk": config.CLERK_CHANNEL
        },
        "data_directories": {
            "bills_text": str(config.BILL_TEXT_DIR),
            "bills_pdf": str(config.BILL_PDF_DIR),
            "knowledge": str(config.KNOWLEDGE_DIR)
        }
    }
    
    import json
    return json.dumps(status, indent=2)

# ===== Prompts =====

@mcp.prompt()
async def help_with_vcbot() -> list:
    """Get help with using VCBot features."""
    return [
        {
            "role": "system",
            "content": "You are a helpful assistant for VCBot, a Discord bot for Virtual Congress."
        },
        {
            "role": "user",
            "content": """What would you like help with? I can assist you with:

1. **Bill Search** - Finding and analyzing legislation
2. **Economic Reports** - Understanding current economic indicators
3. **Discord Integration** - Sending messages and managing channels
4. **Knowledge Base** - Accessing rules and constitutional documents

Just ask me about any of these features!"""
        }
    ]

# ===== Main Entry Point =====

def main():
    """Run the MCP server."""
    import asyncio
    
    # Print startup message
    print("🚀 Starting VCBot MCP Server...")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🔌 FastMCP server initialized")
    
    # Run the server
    mcp.run()

if __name__ == "__main__":
    main()