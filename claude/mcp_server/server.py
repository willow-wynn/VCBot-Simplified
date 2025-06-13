#!/usr/bin/env python3
"""
VCBot MCP Server - Full Implementation
Enables Claude Desktop to interact with Discord through standardized MCP protocol.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directory to path for VCBot imports
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent))

# FastMCP imports
from mcp.server.fastmcp import FastMCP

# Import VCBot modules directly
import config
import bill_utils
import economic_utils
import file_utils
from ai_tools import fetch_document_content

# Import tool modules
from tools.messaging import MessageTools
from tools.bills import BillTools
from tools.economy import EconomyTools
from tools.documents import DocumentTools
from tools.knowledge import KnowledgeTools

# Initialize MCP server
mcp = FastMCP(
    "VCBot-MCP",
    version="1.0.0",
    description="Model Context Protocol server for VCBot Discord integration"
)

# Initialize tool classes
try:
    print("🔧 Initializing tool classes...", file=sys.stderr)
    message_tools = MessageTools()
    print("✅ MessageTools initialized", file=sys.stderr)
    bill_tools = BillTools()
    print("✅ BillTools initialized", file=sys.stderr)
    economy_tools = EconomyTools()
    print("✅ EconomyTools initialized", file=sys.stderr)
    document_tools = DocumentTools()
    print("✅ DocumentTools initialized", file=sys.stderr)
    knowledge_tools = KnowledgeTools()
    print("✅ KnowledgeTools initialized", file=sys.stderr)
    print("🎉 All tool classes initialized successfully", file=sys.stderr)
except Exception as e:
    print(f"❌ Tool initialization failed: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise

# ==================== DISCORD MESSAGING TOOLS ====================

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
        channel_name: Name of Discord channel (e.g., "bot-helper", "official-rp-news")
        content: Message content (can be empty if only sending embed)
        embed_title: Optional embed title
        embed_description: Optional embed description
        embed_color: Optional embed color (hex value)
    
    Returns:
        Success status and message details
    """
    return await message_tools.send_message(
        channel_name, content, embed_title, embed_description, embed_color
    )

@mcp.tool()
async def get_channel_history(
    channel_name: str,
    limit: int = 20,
    search_term: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch recent messages from a Discord channel.
    
    Args:
        channel_name: Name of Discord channel
        limit: Number of messages to fetch (max 50)
        search_term: Optional search term to filter messages
    
    Returns:
        List of messages with author, content, and timestamp
    """
    return await message_tools.get_channel_history(channel_name, limit, search_term)

@mcp.tool()
async def reply_to_message(
    message_id: str,
    channel_name: str,
    content: str
) -> Dict[str, Any]:
    """
    Reply to a specific Discord message.
    
    Args:
        message_id: ID of message to reply to
        channel_name: Channel containing the message
        content: Reply content
    
    Returns:
        Success status and reply details
    """
    return await message_tools.reply_to_message(message_id, channel_name, content)

# ==================== BILL MANAGEMENT TOOLS ====================

@mcp.tool()
async def search_bills(
    query: str,
    limit: int = 5,
    search_type: str = "keyword"
) -> List[Dict[str, Any]]:
    """
    Search for bills in the legislative corpus.
    
    Args:
        query: Search terms (keywords work best, e.g., "healthcare", "tax credit")
        limit: Maximum number of results (max 10)
        search_type: Type of search ("keyword", "title", "content")
    
    Returns:
        List of bills with title, summary, and relevance score
    """
    return await bill_tools.search_bills(query, limit, search_type)

@mcp.tool()
async def get_bill_details(
    bill_title: str,
    include_full_text: bool = False,
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Get detailed information about a specific bill.
    
    Args:
        bill_title: Title or filename of the bill
        include_full_text: Whether to include the full bill text
        include_metadata: Whether to include bill metadata
    
    Returns:
        Detailed bill information including metadata and optionally full text
    """
    return await bill_tools.get_bill_details(bill_title, include_full_text, include_metadata)

@mcp.tool()
async def get_bill_pdf(
    bill_title: str
) -> Dict[str, Any]:
    """
    Get PDF file information for a bill.
    
    Args:
        bill_title: Title or filename of the bill
    
    Returns:
        PDF file path and availability information
    """
    return await bill_tools.get_bill_pdf(bill_title)

@mcp.tool()
async def add_bill_from_url(
    google_docs_url: str,
    bill_title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a new bill from a Google Docs URL.
    
    Args:
        google_docs_url: Google Docs URL containing the bill
        bill_title: Optional title override
    
    Returns:
        Success status and bill information
    """
    return await bill_tools.add_bill_from_url(google_docs_url, bill_title)

# ==================== ECONOMIC ANALYSIS TOOLS ====================

@mcp.tool()
async def get_economic_report() -> Dict[str, Any]:
    """
    Get comprehensive economic report with all indicators.
    
    Returns:
        Complete economic data including GDP, inflation, unemployment, market sentiment
    """
    return await economy_tools.get_economic_report()

@mcp.tool()
async def get_economic_summary() -> Dict[str, Any]:
    """
    Get condensed economic summary with key metrics.
    
    Returns:
        Key economic indicators in summary format
    """
    return await economy_tools.get_economic_summary()

@mcp.tool()
async def trigger_economic_analysis(
    force_update: bool = False
) -> Dict[str, Any]:
    """
    Trigger a new economic analysis cycle.
    
    Args:
        force_update: Force fresh data collection
    
    Returns:
        Analysis results and status
    """
    return await economy_tools.trigger_economic_analysis(force_update)

@mcp.tool()
async def get_stock_market_overview() -> Dict[str, Any]:
    """
    Get current stock market overview with sector performance.
    
    Returns:
        Market parameters, sector performance, and individual stock data
    """
    return await economy_tools.get_stock_market_overview()

@mcp.tool()
async def get_stock_price(
    symbol: str,
    include_history: bool = False
) -> Dict[str, Any]:
    """
    Get current price and information for a specific stock.
    
    Args:
        symbol: Stock symbol (e.g., "AAPL", "MSFT", "GOOGL")
        include_history: Include 48-hour price history
    
    Returns:
        Stock price, company info, and optionally price history
    """
    return await economy_tools.get_stock_price(symbol, include_history)

@mcp.tool()
async def execute_stock_trade(
    user_id: str,
    action: str,
    symbol: str,
    quantity: int,
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a stock trade for a user (requires authentication).
    
    Args:
        user_id: Discord user ID
        action: "buy" or "sell"
        symbol: Stock symbol
        quantity: Number of shares
        auth_token: Authentication token for trading
    
    Returns:
        Trade execution results and updated portfolio
    """
    return await economy_tools.execute_stock_trade(user_id, action, symbol, quantity, auth_token)

@mcp.tool()
async def get_user_portfolio(
    user_id: str,
    include_history: bool = False
) -> Dict[str, Any]:
    """
    Get user's stock portfolio and net worth.
    
    Args:
        user_id: Discord user ID
        include_history: Include portfolio performance history
    
    Returns:
        Portfolio holdings, cash balance, and total net worth
    """
    return await economy_tools.get_user_portfolio(user_id, include_history)

# ==================== AGENTIC ECONOMIC ANALYSIS TOOLS ====================

@mcp.tool()
async def get_server_channels(
    channel_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get available Discord channels for economic analysis.
    
    Args:
        channel_type: Optional filter by channel type ("NEWS", "CONGRESS", "EXECUTIVE", etc.)
    
    Returns:
        List of authorized channels for economic analysis
    """
    return await economy_tools.get_server_channels(channel_type)

@mcp.tool()
async def analyze_channel_activity(
    channel_name: str,
    days_back: int = 7,
    message_limit: int = 100,
    include_full_content: bool = False
) -> Dict[str, Any]:
    """
    Analyze Discord channel activity for economic insights.
    
    Args:
        channel_name: Name of Discord channel to analyze
        days_back: Number of days to look back (max 30)
        message_limit: Maximum messages to analyze (max 500)
        include_full_content: Whether to include full message content
    
    Returns:
        Channel activity analysis with economic keywords and insights
    """
    return await economy_tools.analyze_channel_activity(
        channel_name, days_back, message_limit, include_full_content
    )

@mcp.tool()
async def extract_document_data(
    doc_url: str
) -> Dict[str, Any]:
    """
    Extract and analyze Google Docs content for economic relevance.
    
    Args:
        doc_url: Google Docs URL to analyze
    
    Returns:
        Document content with economic relevance scoring and keyword extraction
    """
    return await economy_tools.extract_document_data(doc_url)

@mcp.tool()
async def get_previous_economic_data(
    days_back: int = 30
) -> Dict[str, Any]:
    """
    Retrieve historical economic reports for trend analysis.
    
    Args:
        days_back: Number of days of historical data to retrieve
    
    Returns:
        Historical economic data for trend analysis
    """
    return await economy_tools.get_previous_economic_data(days_back)

@mcp.tool()
async def trigger_comprehensive_economic_analysis(
    user_prompt: Optional[str] = None,
    force_update: bool = False,
    days_back: int = 30
) -> Dict[str, Any]:
    """
    Trigger comprehensive agentic economic analysis.
    
    Args:
        user_prompt: Optional custom analysis prompt
        force_update: Force fresh data collection
        days_back: Analysis period in days
    
    Returns:
        Analysis trigger status and session information
    """
    return await economy_tools.trigger_comprehensive_economic_analysis(
        user_prompt, force_update, days_back
    )

@mcp.tool()
async def get_stock_initialization_data() -> Dict[str, Any]:
    """
    Get stock market initialization parameters from economic data.
    
    Returns:
        Market parameters calculated from current economic indicators
    """
    return await economy_tools.get_stock_initialization_data()

@mcp.tool()
async def submit_daily_stock_initialization(
    market_parameters: Dict[str, float],
    invisible_factors: Dict[str, float],
    daily_stock_prices: Dict[str, Dict[str, float]],
    sector_outlook: Dict[str, str],
    reasoning: Dict[str, str]
) -> Dict[str, Any]:
    """
    Submit daily stock market initialization with AI-analyzed parameters.
    
    Args:
        market_parameters: Dict with keys: trend_direction, volatility, momentum, market_sentiment, long_term_outlook
        invisible_factors: Dict with keys: institutional_flow, liquidity_factor, news_velocity, sector_rotation, risk_appetite
        daily_stock_prices: Dict of stock symbols with their daily data:
            - Each stock should have: open_price, range_low, range_high, sector_factor
            - Example: {"AAPL": {"open_price": 170.50, "range_low": 169.0, "range_high": 172.0, "sector_factor": 0.95}}
        sector_outlook: Dict of sector names (ENERGY, TECH, etc.) with outlook descriptions
        reasoning: Dict with analysis reasoning (economic_assessment, parameter_justification, discord_impact, market_outlook)
    
    Returns:
        Success status and applied parameters
    
    Example:
        market_parameters = {
            "trend_direction": -0.3,
            "volatility": 0.8, 
            "momentum": 0.2,
            "market_sentiment": 0.35,
            "long_term_outlook": 0.4
        }
        
        daily_stock_prices = {
            "AAPL": {"open_price": 170.50, "range_low": 165.0, "range_high": 176.0, "sector_factor": 0.95},
            "MSFT": {"open_price": 260.0, "range_low": 252.0, "range_high": 268.0, "sector_factor": 0.97},
            # ... all 24 stocks
        }
    """
    return await economy_tools.submit_daily_stock_initialization(
        market_parameters, invisible_factors, daily_stock_prices, sector_outlook, reasoning
    )

# ==================== MEMORY & CONTEXT MANAGEMENT ====================

@mcp.tool()
async def add_memory_entry(
    content: str,
    admin_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add memory entry for AI context continuity.
    
    Args:
        content: Memory content to store
        admin_id: Optional admin ID for tracking
    
    Returns:
        Memory entry ID and storage confirmation
    """
    return await economy_tools.add_memory_entry(content, admin_id)

@mcp.tool()
async def remove_memory_entry(
    entry_id: str
) -> Dict[str, Any]:
    """
    Remove memory entry by ID.
    
    Args:
        entry_id: Memory entry ID to remove
    
    Returns:
        Removal confirmation and status
    """
    return await economy_tools.remove_memory_entry(entry_id)

@mcp.tool()
async def get_memory_context() -> Dict[str, Any]:
    """
    Get formatted memory context for AI analysis.
    
    Returns:
        Complete memory context for AI continuity
    """
    return await economy_tools.get_memory_context()

# ==================== ADVANCED ADMINISTRATIVE TOOLS ====================

@mcp.tool()
async def get_economic_status() -> Dict[str, Any]:
    """
    Get comprehensive economic system status.
    
    Returns:
        Complete system status including data health and last updates
    """
    return await economy_tools.get_economic_status()

@mcp.tool()
async def log_admin_action(
    admin_id: str,
    action: str,
    details: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log administrative action for audit trail.
    
    Args:
        admin_id: Administrator user ID
        action: Action being performed
        details: Optional action details
    
    Returns:
        Logging confirmation and audit trail entry
    """
    return await economy_tools.log_admin_action(admin_id, action, details)

@mcp.tool()
async def set_advanced_economic_parameter(
    parameter: str,
    value: float,
    admin_id: str,
    admin_token: str
) -> Dict[str, Any]:
    """
    Set economic parameter with enhanced admin controls.
    
    Args:
        parameter: Parameter name to modify
        value: New parameter value
        admin_id: Administrator user ID
        admin_token: Admin authentication token
    
    Returns:
        Parameter update confirmation with audit logging
    """
    return await economy_tools.set_advanced_economic_parameter(
        parameter, value, admin_id, admin_token
    )

# ==================== ECONOMIC REPORT SUBMISSION ====================

@mcp.tool()
async def submit_economic_report(
    report_data: Dict[str, Any],
    analysis_type: str = "comprehensive",
    submit_to_discord: bool = True,
    target_channel: str = "official-rp-news"
) -> Dict[str, Any]:
    """
    Submit completed economic analysis report.
    
    Args:
        report_data: Complete economic report data with GDP, inflation, unemployment, sentiment
        analysis_type: Type of analysis ("comprehensive", "quick", "emergency")
        submit_to_discord: Whether to submit to Discord automatically
        target_channel: Target Discord channel for submission
    
    Returns:
        Submission confirmation and report processing status
    """
    return await economy_tools.submit_economic_report(
        report_data, analysis_type, submit_to_discord, target_channel
    )

# ==================== DOCUMENT PROCESSING TOOLS ====================

@mcp.tool()
async def fetch_google_doc(
    doc_url: str,
    extract_sections: bool = False,
    analyze_content: bool = False
) -> Dict[str, Any]:
    """
    Fetch and parse a Google Doc.
    
    Args:
        doc_url: Google Docs URL
        extract_sections: Whether to extract document sections
        analyze_content: Whether to perform content analysis
    
    Returns:
        Document content, metadata, and optional analysis
    """
    return await document_tools.fetch_google_doc(doc_url, extract_sections, analyze_content)

@mcp.tool()
async def analyze_document_impact(
    doc_url: str,
    analysis_type: str = "economic",
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze document for policy or economic impact.
    
    Args:
        doc_url: Document URL to analyze
        analysis_type: "economic", "policy", "legislative", or "general"
        context: Additional context for analysis
    
    Returns:
        Detailed impact analysis and recommendations
    """
    return await document_tools.analyze_document_impact(doc_url, analysis_type, context)

# ==================== KNOWLEDGE BASE TOOLS ====================

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
    return await knowledge_tools.get_knowledge_file(file_name)

@mcp.tool()
async def search_knowledge_base(
    query: str,
    file_filter: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Search across knowledge base files.
    
    Args:
        query: Search terms
        file_filter: Optional list of specific files to search
    
    Returns:
        Search results with file sources and relevant excerpts
    """
    return await knowledge_tools.search_knowledge_base(query, file_filter)

@mcp.tool()
async def list_knowledge_files() -> Dict[str, Any]:
    """
    List all available knowledge base files.
    
    Returns:
        Available files with descriptions and metadata
    """
    return await knowledge_tools.list_knowledge_files()

# ==================== ADMINISTRATIVE TOOLS ====================

@mcp.tool()
async def set_economic_parameter(
    parameter: str,
    value: float,
    admin_token: str
) -> Dict[str, Any]:
    """
    Set economic parameter (admin only).
    
    Args:
        parameter: Parameter name (e.g., "inflation_rate", "gdp_growth")
        value: New parameter value
        admin_token: Admin authentication token
    
    Returns:
        Success status and updated parameter info
    """
    return await economy_tools.set_economic_parameter(parameter, value, admin_token)

@mcp.tool()
async def get_bot_status() -> Dict[str, Any]:
    """
    Get VCBot system status and configuration.
    
    Returns:
        Bot configuration, system status, and available features
    """
    status = {
        "bot_id": config.BOT_ID,
        "guild_id": config.GUILD_ID,
        "channels": {
            "records": config.RECORDS_CHANNEL,
            "news": config.NEWS_CHANNEL,
            "clerk": config.CLERK_CHANNEL,
            "bot_helper": config.BOT_HELPER_CHANNEL
        },
        "data_directories": {
            "bills_text": str(config.BILL_TEXT_DIR),
            "bills_pdf": str(config.BILL_PDF_DIR),
            "knowledge": str(config.KNOWLEDGE_DIR),
            "economic_data": "economic_data/",
            "stock_data": "stock_data/"
        },
        "features": {
            "bill_search": True,
            "economic_analysis": True,
            "stock_market": True,
            "knowledge_base": True,
            "discord_integration": True
        }
    }
    
    return status

# ==================== RESOURCES ====================

@mcp.resource("vcbot://channels")
async def list_available_channels() -> str:
    """List all available Discord channels."""
    channels = {
        "bot_channels": ["bot-helper"],
        "news_channels": [
            "official-rp-news", "parody", "pbn", "liberty-ledger", 
            "wall-street-journal", "4e-news-from-the-hill", "202news", "msnbc"
        ],
        "congress_channels": [
            "house-floor", "senate-floor", "house-docket", "senate-docket",
            "house-vote-results", "senate-vote-results", "committee-announcements",
            "speaker-announcements", "senate-announcements"
        ],
        "executive_channels": [
            "bills-signed-into-law", "bills-vetoed", "presidential-congressional-desk",
            "president-announcements", "press-briefing-room", "cabinet-announcements",
            "executive-orders", "presidential-memoranda"
        ],
        "public_channels": [
            "rp-chat", "twitter-rp", "press-releases", "press-room", "election-announcements"
        ]
    }
    
    return json.dumps(channels, indent=2)

@mcp.resource("vcbot://bills/recent")
async def get_recent_bills() -> str:
    """Get list of recently added bills."""
    json_files = sorted(
        config.BILL_JSON_DIR.glob("*.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )[:15]
    
    bills = []
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                bills.append({
                    "title": data.get("title", json_file.stem),
                    "filename": json_file.stem,
                    "modified": json_file.stat().st_mtime,
                    "summary": data.get("summary", "")[:200] + "..." if data.get("summary", "") else ""
                })
        except:
            continue
    
    return json.dumps(bills, indent=2)

@mcp.resource("vcbot://economy/current")
async def get_current_economy() -> str:
    """Get current economic indicators as a resource."""
    report = economic_utils.econ_data.get_fresh_economic_report()
    return json.dumps(report, indent=2)

@mcp.resource("vcbot://stocks/market")
async def get_market_resource() -> str:
    """Get current market data as a resource."""
    try:
        import stock_market
        market = stock_market.get_stock_market()
        
        if not market:
            return json.dumps({"error": "Stock market not initialized"})
        
        data = {
            "status": "open" if market.is_market_open() else "closed",
            "parameters": market.market_params,
            "sectors": list(market.sectors.keys()),
            "total_stocks": sum(len(stocks) for stocks in market.sectors.values()),
            "last_update": market.last_update.isoformat() if market.last_update else None
        }
        
        return json.dumps(data, indent=2)
        
    except ImportError:
        return json.dumps({"error": "Stock market module not available"})

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
        Prompt messages for comprehensive bill analysis
    """
    # Get bill details
    bill_details = await get_bill_details(bill_title, include_full_text=True)
    
    if "error" in bill_details:
        return [{"role": "user", "content": f"Error: Could not find bill '{bill_title}'"}]
    
    # Get current economic data
    econ_report = await get_economic_summary()
    
    # Build comprehensive analysis prompt
    messages = [
        {
            "role": "system",
            "content": "You are an expert policy analyst for Virtual Congress, specializing in legislative impact assessment and economic analysis."
        },
        {
            "role": "user",
            "content": f"""Please conduct a comprehensive analysis of the following legislation:

**BILL INFORMATION**
Title: {bill_details['title']}
Filename: {bill_details.get('filename', 'N/A')}

**BILL TEXT**
{bill_details.get('full_text', 'Full text not available')}

**CURRENT ECONOMIC CONTEXT**
- GDP Growth: {econ_report['gdp']['growth']}%
- Inflation Rate: {econ_report['inflation']['rate']}%
- Federal Funds Rate: {econ_report['inflation']['fed_rate']}%
- Unemployment: {econ_report['unemployment']['rate']}%
- Market Confidence: {econ_report['sentiment']['confidence']}%
- Anxiety Index: {econ_report['sentiment']['anxiety']}%

**ANALYSIS REQUIREMENTS**
Please provide a detailed analysis covering:

1. **Executive Summary**
   - Brief overview of the bill's purpose and scope
   - Key stakeholders and affected parties

2. **Economic Impact Assessment**
   - Direct fiscal implications (costs, revenue impacts)
   - Indirect economic effects on markets and sectors
   - Impact on inflation, employment, and economic growth
   - Analysis in context of current economic conditions

3. **Sector-Specific Analysis**
   - Which economic sectors will be most affected
   - Impact on major stocks/companies (AAPL, MSFT, JPM, XOM, etc.)
   - Regional economic implications

4. **Implementation Analysis**
   - Required resources and timeline
   - Potential implementation challenges
   - Regulatory and administrative requirements

5. **Political Feasibility**
   - Likelihood of passage in current political climate
   - Potential opposition and support coalitions
   - Amendment possibilities

6. **Risk Assessment**
   - Potential unintended consequences
   - Economic risks and uncertainties
   - Long-term sustainability concerns

7. **Recommendations**
   - Overall recommendation (support/oppose/modify)
   - Suggested amendments or improvements
   - Monitoring and evaluation framework

Please format your analysis professionally and cite specific provisions of the bill where relevant."""
        }
    ]
    
    return messages

@mcp.prompt()
async def draft_discord_announcement(
    topic: str,
    channel: str = "official-rp-news",
    tone: str = "professional"
) -> List[Dict[str, str]]:
    """
    Generate a prompt for drafting Discord announcements.
    
    Args:
        topic: Topic of the announcement
        channel: Target Discord channel
        tone: Tone of the announcement ("professional", "casual", "urgent")
        
    Returns:
        Prompt messages for announcement drafting
    """
    # Get recent messages from channel for context
    recent_messages = await get_channel_history(channel, limit=5)
    
    messages = [
        {
            "role": "system",
            "content": f"You are drafting an official announcement for Virtual Congress Discord server, specifically for the #{channel} channel. Maintain the established tone and formatting conventions of the server."
        },
        {
            "role": "user",
            "content": f"""Draft a {tone} announcement about: {topic}

**Channel:** #{channel}
**Tone:** {tone}

**Recent Channel Context:**
{json.dumps(recent_messages, indent=2)}

**Formatting Guidelines:**
- Use Discord markdown (bold, italics, code blocks)
- Include relevant emojis for visual appeal
- Use appropriate mentions (@everyone, @here, role mentions) sparingly
- Structure with clear sections if the announcement is complex
- Keep it concise but informative
- Match the communication style of recent messages

**Content Requirements:**
- Clear, actionable information
- Relevant dates and deadlines if applicable
- Contact information or next steps
- Professional but engaging tone

Please draft the announcement following these guidelines."""
        }
    ]
    
    return messages

@mcp.prompt()
async def economic_briefing() -> List[Dict[str, str]]:
    """
    Generate a prompt for creating an economic briefing.
    
    Returns:
        Prompt messages for economic analysis
    """
    # Get current economic data
    econ_report = await get_economic_report()
    stock_overview = await get_stock_market_overview()
    
    messages = [
        {
            "role": "system",
            "content": "You are the chief economic advisor for Virtual Congress, preparing a briefing for government leaders."
        },
        {
            "role": "user",
            "content": f"""Prepare a comprehensive economic briefing based on the latest data:

**ECONOMIC INDICATORS**
{json.dumps(econ_report, indent=2)}

**STOCK MARKET DATA**
{json.dumps(stock_overview, indent=2)}

**BRIEFING REQUIREMENTS**
Create a professional briefing document that includes:

1. **Executive Summary**
   - Current economic state in 2-3 sentences
   - Key trends and concerns

2. **Detailed Analysis**
   - GDP and growth trends
   - Inflation analysis and monetary policy implications
   - Labor market conditions
   - Market sentiment and confidence levels

3. **Sector Performance**
   - Stock market performance by sector
   - Notable gains/losses in major companies
   - Economic drivers behind sector performance

4. **Policy Implications**
   - Recommended policy responses
   - Areas requiring government attention
   - Potential legislative priorities

5. **Risk Assessment**
   - Economic risks on the horizon
   - Market volatility concerns
   - External factors to monitor

6. **Recommendations**
   - Immediate actions needed
   - Medium-term strategic priorities
   - Monitoring and review schedule

Format this as a professional government briefing document."""
        }
    ]
    
    return messages

# ==================== MAIN ENTRY POINT ====================

def main():
    """Run the MCP server."""
    try:
        print("🚀 Starting VCBot MCP Server...", file=sys.stderr)
        print(f"📁 Working directory: {os.getcwd()}", file=sys.stderr)
        print("🔌 VCBot economic tools loaded", file=sys.stderr)
        print("📋 Resources and prompts available", file=sys.stderr)
        print("📝 Ready for Claude Desktop connection", file=sys.stderr)
        
        # Run the server
        mcp.run()
    except Exception as e:
        print(f"❌ Server crashed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise

if __name__ == "__main__":
    main()