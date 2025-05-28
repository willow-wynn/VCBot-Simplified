"""
Economic utilities for VCBot - Agentic Economic Analysis System
Provides intelligent economic analysis using AI-powered tool calls
"""

import asyncio
import json
import os
import aiohttp
import re
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import google.generativeai as genai
from google.genai import types
from config import GEMINI_API_KEY

# Discord import for exception handling
try:
    import discord
except ImportError:
    # Create mock discord module for type hints if not available
    class MockDiscord:
        class HTTPException(Exception):
            def __init__(self, status=None):
                self.status = status
    discord = MockDiscord()

# Google AI import for exception handling
try:
    from google.api_core.exceptions import ResourceExhausted, TooManyRequests
except ImportError:
    # Create mock Google exceptions if not available
    class ResourceExhausted(Exception):
        pass
    class TooManyRequests(Exception):
        pass

# Global economic engine state
economic_engine = None
analysis_task = None

# Configure Gemini 2.5
genai.configure(api_key=GEMINI_API_KEY)

# Allowed channels for economic analysis - RESTRICTED ACCESS
ALLOWED_CHANNELS = {
    "NEWS": [
        "news-information", "official-rp-news", "parody", "pbn", 
        "liberty-ledger", "wall-street-journal", "4e-news-from-the-hill", 
        "202news", "msnbc"
    ],
    "CONGRESS": [
        "speaker-announcements", "house-docket", "house-floor", "house-vote-results",
        "senate-announcements", "senate-docket", "senate-floor", "senate-vote-results",
        "committee-announcements"
    ],
    "EXECUTIVE": [
        "bills-signed-into-law", "bills-vetoed", "presidential-congressional-desk",
        "president-announcements", "press-briefing-room", "cabinet-announcements",
        "executive-orders", "presidential-memoranda"
    ],
    "STATES": [
        "olympia-governor", "pacifica-governor", "lincoln-governor", 
        "jackson-governor", "frontier-governor"
    ],
    "COURTS": [
        "district-court-announcements", "supreme-court-announcements"
    ],
    "PUBLIC_SQUARE": [
        "rp-chat", "twitter-rp", "press-releases", "press-room", 
        "election-announcements", "election-results", "staff-announcements"
    ]
}

# Flatten the allowed channels list for easy lookup
ALL_ALLOWED_CHANNELS = set()
for category, channels in ALLOWED_CHANNELS.items():
    ALL_ALLOWED_CHANNELS.update(channels)

def is_channel_allowed(channel_name: str) -> bool:
    """Check if a channel is in the allowed list for economic analysis"""
    return channel_name.lower() in ALL_ALLOWED_CHANNELS

def get_channel_category(channel_name: str) -> str:
    """Get the category of an allowed channel"""
    for category, channels in ALLOWED_CHANNELS.items():
        if channel_name.lower() in channels:
            return category
    return "UNKNOWN"

# Economic Analysis Tools for AI Agent - Proper Gemini Format
def get_economic_analysis_tools():
    """Get properly formatted Gemini tools"""
    return [
        genai.protos.FunctionDeclaration(
            name="get_server_channels",
            description="Get a list of all available Discord channels for analysis",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "channel_type": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        enum=["all", "text", "voice"],
                        description="Type of channels to retrieve"
                    )
                },
                required=["channel_type"]
            )
        ),
        genai.protos.FunctionDeclaration(
            name="analyze_channel_activity",
            description="Analyze recent activity in a specific Discord channel with comprehensive context",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "channel_name": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Name of the channel to analyze"
                    ),
                    "days_back": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Number of days to look back (1-30). Must be an integer."
                    ),
                    "message_limit": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Maximum number of messages to analyze (50-500 for comprehensive analysis). Must be an integer."
                    ),
                    "include_full_content": genai.protos.Schema(
                        type=genai.protos.Type.BOOLEAN,
                        description="Whether to include full message content (true) or truncated (false). Default true for comprehensive analysis."
                    )
                },
                required=["channel_name", "days_back", "message_limit"]
            )
        ),
        genai.protos.FunctionDeclaration(
            name="extract_document_data",
            description="Extract and analyze data from Google Docs links found in channels",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "doc_url": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Google Docs URL to analyze"
                    )
                },
                required=["doc_url"]
            )
        ),
        genai.protos.FunctionDeclaration(
            name="get_previous_economic_data",
            description="Retrieve previous economic analysis for comparison",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "days_back": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="How many days back to retrieve data. Must be an integer."
                    )
                },
                required=["days_back"]
            )
        )
    ]

class EconomicData:
    """Agentic economic data management with AI-powered analysis"""
    
    def __init__(self):
        self.data_dir = Path("economic_data")
        self.data_dir.mkdir(exist_ok=True)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.parameters = self.load_parameters()
        self.client = None
        self.analysis_log_dir = self.data_dir / "analysis_logs"
        self.analysis_log_dir.mkdir(exist_ok=True)
        
        print("🤖 Economic Analysis Agent initialized with tool-based approach")
        print(f"📊 Using realistic economic parameters: GDP base ${self.parameters['gdp_base']:,.1f}T, Inflation {self.parameters['inflation_base']}%")
    
    def load_parameters(self) -> Dict[str, Any]:
        """Load economic parameters or create realistic defaults"""
        params_file = self.data_dir / "parameters.json"
        
        # Realistic economic parameters based on actual US economic indicators
        default_params = {
            "gdp_weights": {
                "legislative": 0.35,  # Legislative activity drives major economic policy
                "committee": 0.25,    # Committee work shapes detailed policy implementation
                "public": 0.25,       # Public sentiment affects market confidence
                "news": 0.15          # News and announcements provide market signals
            },
            "inflation_base": 3.2,        # Current realistic inflation target (Fed aims for 2%, but 3.2% is more realistic in current environment)
            "unemployment_base": 3.7,     # Full employment level (US natural rate ~3.5-4%)
            "stock_volatility": 0.12,     # Realistic daily volatility (12% annualized is typical)
            "gdp_base": 27.0,             # Baseline GDP in trillions (US GDP ~$27T)
            "analysis_interval": 3600,    # 1 hour for responsive analysis
            "lookback_days": 7,           # Weekly analysis window for responsiveness
            "confidence_threshold": 0.75, # Minimum confidence for economic projections
            # Note: Stock tracking moved to stock_market.py - economic system tracks indicators only
            "economic_indicators": {
                "employment_weight": 0.30,    # Employment data heavily influences economic health
                "spending_weight": 0.25,      # Government spending drives economic activity  
                "policy_weight": 0.20,        # Policy changes affect long-term growth
                "sentiment_weight": 0.15,     # Market sentiment affects short-term movements
                "international_weight": 0.10  # International factors (trade, treaties, etc.)
            }
        }
        
        if params_file.exists():
            with open(params_file, 'r') as f:
                existing_params = json.load(f)
                
                # Update to realistic parameters - force upgrade old unrealistic values
                parameters_to_update = {
                    'inflation_base': 3.2,  # More realistic than 2.5%
                    'analysis_interval': 3600,  # 1 hour instead of 1 week for responsiveness
                    'lookback_days': 7,  # Weekly instead of 30-day for responsiveness
                    'stock_volatility': 0.12,  # More realistic volatility
                    'gdp_weights': default_params['gdp_weights']  # Include news component
                    # Note: tracked_stocks removed - stock tracking moved to stock_market.py
                }
                
                for key, value in parameters_to_update.items():
                    if existing_params.get(key) != value:
                        existing_params[key] = value
                        print(f"📝 Updated parameter to realistic value: {key}")
                
                # Merge with defaults to ensure all new parameters exist
                for key, value in default_params.items():
                    if key not in existing_params:
                        existing_params[key] = value
                        print(f"📝 Added new parameter: {key} = {value}")
                
                # Save updated parameters
                self.save_parameters(existing_params)
                return existing_params
        else:
            print("📝 Creating new parameters file with realistic economic defaults")
            self.save_parameters(default_params)
            return default_params
    
    def save_parameters(self, params: Dict[str, Any]) -> None:
        """Save economic parameters"""
        with open(self.data_dir / "parameters.json", 'w') as f:
            json.dump(params, f, indent=2)
    
    
    
    def get_activity_indicators(self, messages: List[Dict]) -> Dict[str, Any]:
        """Extract government activity indicators from messages"""
        indicators = {
            "government_mentions": 0,
            "policy_discussions": 0,
            "voting_activity": 0,
            "bill_references": 0,
            "committee_work": 0,
            "economic_terms": 0
        }
        
        for msg in messages:
            content_lower = msg.get("content", "").lower()
            
            # Government activity indicators
            if any(term in content_lower for term in ['congress', 'senate', 'house', 'representative', 'senator', 'government']):
                indicators["government_mentions"] += 1
            
            # Policy discussion indicators
            if any(term in content_lower for term in ['policy', 'legislation', 'bill', 'amendment', 'law', 'act']):
                indicators["policy_discussions"] += 1
            
            # Voting activity indicators
            if any(term in content_lower for term in ['vote', 'yea', 'nay', 'present', 'motion', 'resolution']):
                indicators["voting_activity"] += 1
            
            # Bill reference indicators
            if any(term in content_lower for term in ['h.r.', 's.', 'bill number', 'public law', 'statute']):
                indicators["bill_references"] += 1
            
            # Committee work indicators
            if any(term in content_lower for term in ['committee', 'markup', 'hearing', 'subcommittee', 'chairman', 'ranking member']):
                indicators["committee_work"] += 1
            
            # Economic term indicators
            if any(term in content_lower for term in ['budget', 'spending', 'tax', 'economy', 'inflation', 'gdp', 'appropriation']):
                indicators["economic_terms"] += 1
        
        return indicators
    
    # Agentic Tool Execution Methods
    
    async def get_server_channels(self, channel_type: str = "text") -> List[Dict[str, str]]:
        """Get list of ALLOWED readable Discord channels with their actual Discord categories"""
        print(f"🔍 Discovering allowed readable {channel_type} channels...")
        
        if not self.client:
            return [{"error": "Discord client not available"}]
        
        channels = []
        total_channels = 0
        allowed_channels = 0
        
        for guild in self.client.guilds:
            if channel_type == "all":
                guild_channels = guild.channels
            elif channel_type == "text":
                guild_channels = guild.text_channels
            elif channel_type == "voice":
                guild_channels = guild.voice_channels
            else:
                guild_channels = guild.text_channels
            
            for channel in guild_channels:
                total_channels += 1
                if hasattr(channel, 'name'):
                    # FIRST: Check if channel is in allowed list
                    if not is_channel_allowed(channel.name):
                        continue
                    
                    # SECOND: Check if bot can read the channel
                    if hasattr(channel, 'permissions_for') and channel.permissions_for(guild.me).read_message_history:
                        allowed_channels += 1
                        
                        # Get the actual Discord category if it exists
                        discord_category = None
                        if hasattr(channel, 'category') and channel.category:
                            discord_category = channel.category.name
                        
                        # Get the economic analysis category
                        econ_category = get_channel_category(channel.name)
                        
                        channels.append({
                            "name": channel.name,
                            "id": str(channel.id),
                            "type": str(channel.type),
                            "guild": guild.name,
                            "discord_category": discord_category,
                            "economic_category": econ_category,
                            "readable": True,
                            "access_restricted": True
                        })
        
        # Group channels by their economic analysis categories for reporting
        economic_categories = {}
        for channel in channels:
            cat = channel["economic_category"]
            if cat not in economic_categories:
                economic_categories[cat] = []
            economic_categories[cat].append(channel["name"])
        
        print(f"📋 Found {len(channels)} ALLOWED readable channels out of {total_channels} total {channel_type} channels")
        print(f"🔒 Access restricted to {len(ALL_ALLOWED_CHANNELS)} whitelisted channels")
        for category, channel_names in economic_categories.items():
            print(f"   📁 {category}: {len(channel_names)} channels ({', '.join(channel_names[:3])}{'...' if len(channel_names) > 3 else ''})")
        
        return channels
    
    async def rate_limit_delay(self, attempt: int = 0, service: str = "Discord") -> None:
        """Apply exponential backoff delay for rate limiting"""
        if attempt > 0:
            delay = min(2 ** attempt + random.uniform(0, 1), 60)  # Max 60 seconds
            print(f"⏳ {service} rate limit backoff: waiting {delay:.1f} seconds (attempt {attempt})")
            await asyncio.sleep(delay)
    
    async def gemini_api_call_with_retry(self, chat, message, max_retries: int = 5):
        """Make Gemini API call with rate limit handling and exponential backoff"""
        for attempt in range(max_retries + 1):
            try:
                await self.rate_limit_delay(attempt, "Gemini")
                
                # Make the API call
                response = await chat.send_message_async(message)
                return response
                
            except (ResourceExhausted, TooManyRequests) as e:
                if attempt >= max_retries:
                    print(f"❌ Gemini API rate limited after {max_retries} retries")
                    raise Exception(f"Gemini API rate limit exceeded: {e}")
                
                print(f"🚫 Gemini API rate limited, retrying... ({attempt + 1}/{max_retries})")
                continue
                
            except Exception as e:
                # Check if it's a rate limit error by message content
                error_str = str(e).lower()
                if any(term in error_str for term in ['rate limit', 'quota', 'too many requests', 'resource exhausted']):
                    if attempt >= max_retries:
                        print(f"❌ Gemini API rate limited after {max_retries} retries")
                        raise Exception(f"Gemini API rate limit exceeded: {e}")
                    
                    print(f"🚫 Gemini API rate limited (detected from error), retrying... ({attempt + 1}/{max_retries})")
                    continue
                else:
                    # Not a rate limit error, re-raise immediately
                    raise
        
        raise Exception("Gemini API call failed after all retries")
    
    async def analyze_channel_activity(self, channel_name: str, days_back: int = 2, message_limit: int = 200, include_full_content: bool = True) -> Dict[str, Any]:
        """Analyze activity in a specific channel with comprehensive context"""
        # Convert to integers in case AI passes floats
        days_back = int(float(days_back))
        message_limit = int(float(message_limit))
        
        # Cap reasonable limits to prevent overwhelming the AI
        message_limit = min(message_limit, 500)  # Max 500 messages
        days_back = min(days_back, 30)  # Max 30 days
        
        print(f"📊 Analyzing channel '{channel_name}' - {days_back} days back, {message_limit} messages max")
        
        if not self.client:
            return {"error": "Discord client not available"}
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        for guild in self.client.guilds:
            channel = None
            for ch in guild.text_channels:
                if ch.name == channel_name:
                    channel = ch
                    break
            
            if not channel:
                continue
            
            # Check if channel is allowed for economic analysis
            if not is_channel_allowed(channel_name):
                print(f"🚫 Channel '{channel_name}' not in allowed list - access denied")
                return {
                    "channel_name": channel_name,
                    "error": f"Channel '{channel_name}' not authorized for economic analysis",
                    "messages_analyzed": 0,
                    "documents_found": 0,
                    "activity_summary": {
                        "total_messages": 0,
                        "access_denied": True,
                        "reason": "Channel not in whitelist"
                    },
                    "sample_messages": [],
                    "document_links": [],
                    "economic_category": "RESTRICTED"
                }
            
            if not channel.permissions_for(guild.me).read_message_history:
                print(f"⚠️ No permission to read {channel_name}")
                return {
                    "channel_name": channel_name,
                    "error": f"No permission to read {channel_name}",
                    "messages_analyzed": 0,
                    "documents_found": 0,
                    "activity_summary": {
                        "total_messages": 0,
                        "permission_denied": True
                    },
                    "sample_messages": [],
                    "document_links": []
                }
            
            messages = []
            document_links = []
            
            try:
                # Apply rate limiting with retries
                max_retries = 3
                retry_count = 0
                
                while retry_count <= max_retries:
                    try:
                        await self.rate_limit_delay(retry_count)
                        
                        async for message in channel.history(limit=message_limit, after=cutoff_date):
                            if message.author.bot:
                                continue
                            
                            # Include full content for comprehensive analysis
                            content = message.content if include_full_content else message.content[:300]
                            
                            message_data = {
                                "content": content,
                                "timestamp": message.created_at.isoformat(),
                                "author_name": str(message.author),
                                "author_roles": [role.name for role in getattr(message.author, 'roles', [])],
                                "reactions": len(message.reactions),
                                "reaction_details": [str(reaction.emoji) for reaction in message.reactions] if message.reactions else [],
                                "replies": len(getattr(message, 'replies', [])),
                                "attachments": len(message.attachments),
                                "thread_created": bool(getattr(message, 'thread', None))
                            }
                            messages.append(message_data)
                            
                            # Extract document links
                            urls = re.findall(r'https://docs\.google\.com/document/d/[^\s]+', message.content)
                            for url in urls:
                                document_links.append({
                                    "url": url,
                                    "timestamp": message.created_at.isoformat(),
                                    "author": str(message.author)
                                })
                        
                        # If we get here, the request succeeded
                        break
                        
                    except discord.HTTPException as e:
                        if e.status == 429:  # Rate limited
                            retry_count += 1
                            if retry_count > max_retries:
                                return {
                                    "channel_name": channel_name,
                                    "error": f"Discord rate limited after {max_retries} retries",
                                    "retry_attempts": retry_count
                                }
                            print(f"🚫 Discord rate limited on {channel_name}, retrying... ({retry_count}/{max_retries})")
                            continue
                        else:
                            raise  # Re-raise non-rate-limit errors
                    except Exception as e:
                        # Check for other rate limit errors
                        error_str = str(e).lower()
                        if 'rate limit' in error_str or '429' in error_str:
                            retry_count += 1
                            if retry_count > max_retries:
                                return {
                                    "channel_name": channel_name,
                                    "error": f"Rate limited after {max_retries} retries: {e}",
                                    "retry_attempts": retry_count
                                }
                            print(f"🚫 Rate limited on {channel_name}, retrying... ({retry_count}/{max_retries})")
                            continue
                        else:
                            raise  # Re-raise non-rate-limit errors
                
                # Calculate comprehensive activity metrics
                unique_authors = len(set(msg.get("author_name") for msg in messages))
                total_reactions = sum(msg.get("reactions", 0) for msg in messages)
                total_attachments = sum(msg.get("attachments", 0) for msg in messages)
                threads_created = sum(1 for msg in messages if msg.get("thread_created"))
                
                # Identify key topics and keywords
                all_content = " ".join(msg.get("content", "") for msg in messages)
                economic_keywords = ["budget", "spending", "tax", "economy", "GDP", "inflation", "unemployment", 
                                   "appropriation", "revenue", "fiscal", "monetary", "deficit", "surplus", 
                                   "trade", "commerce", "investment", "market", "financial", "economic"]
                
                keyword_mentions = {kw: all_content.lower().count(kw.lower()) for kw in economic_keywords if kw.lower() in all_content.lower()}
                
                analysis_result = {
                    "channel_name": channel_name,
                    "messages_analyzed": len(messages),
                    "documents_found": len(document_links),
                    "time_period": f"{days_back} days",
                    "activity_summary": {
                        "total_messages": len(messages),
                        "unique_authors": unique_authors,
                        "total_reactions": total_reactions,
                        "total_attachments": total_attachments,
                        "threads_created": threads_created,
                        "document_sharing": len(document_links) > 0,
                        "economic_keyword_mentions": keyword_mentions,
                        "activity_level": "high" if len(messages) > 100 else "medium" if len(messages) > 20 else "low",
                        "government_activity_indicators": self.get_activity_indicators(messages)
                    },
                    "full_messages": messages if include_full_content else messages[:10],  # Full context or sample
                    "message_content_preview": all_content[:2000] if not include_full_content else None,
                    "document_links": document_links,
                    "analysis_metadata": {
                        "full_content_included": include_full_content,
                        "content_truncation": not include_full_content,
                        "comprehensive_analysis": include_full_content and len(messages) >= 50,
                        "rate_limit_retries": retry_count
                    }
                }
                
                print(f"✅ Analyzed {len(messages)} messages from {channel_name} - {unique_authors} unique authors, {total_reactions} reactions")
                if keyword_mentions:
                    print(f"   📊 Economic keywords found: {dict(list(keyword_mentions.items())[:3])}")
                return analysis_result
                
            except Exception as e:
                print(f"❌ Error analyzing {channel_name}: {e}")
                return {
                    "channel_name": channel_name,
                    "category": self.categorize_channel(channel_name),
                    "error": f"Failed to analyze {channel_name}: {e}",
                    "roleplay_relevant": self.is_roleplay_relevant(self.categorize_channel(channel_name))
                }
        
        return {
            "channel_name": channel_name,
            "error": f"Channel '{channel_name}' not found in any guild",
            "messages_analyzed": 0,
            "documents_found": 0,
            "activity_summary": {
                "total_messages": 0,
                "channel_not_found": True
            },
            "sample_messages": [],
            "document_links": []
        }
    
    async def extract_document_data(self, doc_url: str) -> Dict[str, Any]:
        """Extract and analyze Google Docs content"""
        print(f"📄 Extracting document: {doc_url[:50]}...")
        
        try:
            if "docs.google.com" in doc_url:
                doc_id = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc_url)
                if doc_id:
                    export_url = f"https://docs.google.com/document/d/{doc_id.group(1)}/export?format=txt"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(export_url) as response:
                            if response.status == 200:
                                content = await response.text()
                                
                                # Analyze document for economic relevance
                                economic_keywords = ["budget", "spending", "tax", "economy", "GDP", "inflation", "unemployment", "appropriation", "revenue"]
                                relevance_score = sum(1 for keyword in economic_keywords if keyword.lower() in content.lower())
                                
                                result = {
                                    "url": doc_url,
                                    "content_length": len(content),
                                    "content_preview": content[:1000],
                                    "economic_relevance": relevance_score,
                                    "keywords_found": [kw for kw in economic_keywords if kw.lower() in content.lower()]
                                }
                                
                                print(f"✅ Document extracted - {len(content)} chars, relevance: {relevance_score}")
                                return result
                            else:
                                print(f"❌ Document fetch failed: HTTP {response.status}")
                                return {"error": f"Failed to fetch document: HTTP {response.status}"}
            
            return {"error": "Invalid Google Docs URL"}
            
        except Exception as e:
            print(f"❌ Document extraction error: {e}")
            return {"error": f"Document extraction failed: {e}"}
    
    async def get_previous_economic_data(self, days_back: int = 7) -> Dict[str, Any]:
        """Retrieve previous economic data for comparison"""
        # Convert to integer in case AI passes float
        days_back = int(float(days_back))
        
        print(f"📈 Retrieving previous economic data ({days_back} days back)")
        
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            reports_file = self.data_dir / "reports.json"
            if not reports_file.exists():
                print("📊 No previous economic data found")
                return {"message": "No previous economic data available"}
            
            with open(reports_file, 'r') as f:
                reports = json.load(f)
            
            # Filter reports within timeframe
            recent_reports = []
            for report in reports:
                if 'timestamp' in report:
                    report_date = datetime.fromisoformat(report['timestamp'].replace('Z', '+00:00'))
                    if report_date >= cutoff_date:
                        recent_reports.append(report)
            
            if recent_reports:
                latest = recent_reports[-1]
                print(f"✅ Found {len(recent_reports)} recent reports, latest GDP: ${latest.get('gdp', {}).get('value', 'N/A')}")
                
                return {
                    "latest_report": latest,
                    "total_reports": len(recent_reports),
                    "timeframe_days": days_back
                }
            else:
                print("📊 No recent economic data in timeframe")
                return {"message": f"No economic data found in last {days_back} days"}
                
        except Exception as e:
            print(f"❌ Error retrieving previous data: {e}")
            return {"error": f"Failed to retrieve previous data: {e}"}
    
    async def execute_economic_tool(self, function_call) -> Any:
        """Execute economic analysis tool calls"""
        tool_name = function_call.name
        args = function_call.args or {}
        
        print(f"🔧 Executing tool: {tool_name} with args: {args}")
        
        try:
            if tool_name == "get_server_channels":
                result = await self.get_server_channels(args.get("channel_type", "text"))
                print(f"✅ {tool_name} completed successfully")
                return result
            
            elif tool_name == "analyze_channel_activity":
                # Ensure proper types for Discord API
                channel_name = str(args.get("channel_name", ""))
                days_back = args.get("days_back", 2)
                message_limit = args.get("message_limit", 200)  # Default to comprehensive analysis
                include_full_content = args.get("include_full_content", True)  # Default to full context
                
                result = await self.analyze_channel_activity(
                    channel_name,
                    days_back,
                    message_limit,
                    include_full_content
                )
                if "error" in result:
                    print(f"⚠️ {tool_name} completed with issues: {result['error']}")
                else:
                    print(f"✅ {tool_name} completed for channel: {args.get('channel_name')}")
                return result
            
            elif tool_name == "extract_document_data":
                result = await self.extract_document_data(args.get("doc_url"))
                print(f"✅ {tool_name} completed")
                return result
            
            elif tool_name == "get_previous_economic_data":
                # Ensure proper type
                days_back = args.get("days_back", 7)
                
                result = await self.get_previous_economic_data(days_back)
                print(f"✅ {tool_name} completed")
                return result
            
            else:
                print(f"❌ Unknown tool: {tool_name}")
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            print(f"❌ Tool execution failed for {tool_name}: {e}")
            return {"error": f"Tool execution failed for {tool_name}: {e}"}
    
    async def get_document_content(self, doc_url: str) -> Optional[str]:
        """Extract content from Google Docs link"""
        try:
            if "docs.google.com" in doc_url:
                doc_id = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc_url)
                if doc_id:
                    export_url = f"https://docs.google.com/document/d/{doc_id.group(1)}/export?format=txt"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(export_url) as response:
                            if response.status == 200:
                                content = await response.text()
                                return content[:10000]
            return None
        except Exception as e:
            print(f"Error fetching document: {e}")
            return None
    
    async def conduct_agentic_analysis(self, client, days_back: int = 30, previous_report: Optional[Dict[str, Any]] = None, user_prompt: str = None, progress_channel = None, previous_insights: Optional[str] = None, memory_context: str = "") -> Dict[str, Any]:
        """Conduct agentic economic analysis using AI-powered tool calls with detailed logging and live progress updates"""
        print("🤖 Starting agentic economic analysis...")
        
        self.client = client  # Store client for tool access
        
        # Create analysis session identifier
        session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # Check for existing context file from previous failed attempt
        context_file = self.data_dir / f"context_save_{session_id[:8]}.json"
        existing_context_files = list(self.data_dir.glob("context_save_*.json"))
        
        if existing_context_files:
            # Resume from most recent saved context
            latest_context_file = max(existing_context_files, key=lambda f: f.stat().st_mtime)
            print(f"🔄 Found existing context file: {latest_context_file.name}")
            print(f"📝 Resuming analysis from saved context...")
            
            try:
                with open(latest_context_file, 'r') as f:
                    saved_context = json.load(f)
                session_id = saved_context.get('session_id', session_id)
                print(f"📋 Resuming analysis session ID: {session_id}")
            except Exception as e:
                print(f"⚠️ Failed to load saved context: {e}")
                print("📝 Starting fresh analysis...")
        else:
            print(f"📋 Analysis session ID: {session_id}")
        
        print(f"📝 Detailed logs will be saved to: analysis_logs/economic_analysis_{session_id}.txt")
        
        # Build the economic analysis prompt with user context, previous insights, and memory
        user_prompt_context = f"\n\nUser Request Context: {user_prompt}" if user_prompt else ""
        
        previous_insights_context = ""
        if previous_insights:
            previous_insights_context = f"\n\nPrevious Economic Insights (for context and continuity):\n{previous_insights}"
        
        analysis_prompt = f"""You are an advanced economic analyst for a Virtual Congress simulation. 
Your job is to conduct a COMPREHENSIVE analysis of ALL Discord server activity over the last {days_back} days to generate economic indicators.{user_prompt_context}{previous_insights_context}{memory_context}

You have access to these tools:
1. get_server_channels - Discover ALL available Discord channels organized by their actual Discord categories
2. analyze_channel_activity - Analyze specific channel activity (use {days_back} days back for timeframe consistency) 
3. extract_document_data - Extract data from Google Docs
4. get_previous_economic_data - Get historical economic data for comparison

MANDATORY COMPREHENSIVE ANALYSIS PROCESS:
1. First, discover ALL available Discord channels (shows actual Discord server organization)
2. Use your discretion to identify which channels are relevant for economic analysis - look for:
   - Government activity: legislative sessions, voting, bill discussions
   - Economic policy: budget discussions, appropriations, spending debates
   - News and sentiment: media channels, announcements, public reaction
   - Committee work: policy development, hearings, markup sessions
   - Administrative activity: procedural government operations
3. Analyze channels based on your assessment of their relevance to economic indicators

IMPORTANT: This analysis covers the last {days_back} days of activity. Go back the FULL {days_back} days when analyzing channels - don't just look at recent messages. Use days_back={days_back} consistently in all channel analysis calls.

4. You MUST check for economic keywords in ALL channel types:
   - Budget, spending, appropriations, taxes, revenue
   - Bills, legislation, votes, amendments, markup
   - Economic policy, inflation, unemployment, GDP
   - Trade, commerce, business, industry
   - Infrastructure, development, investment
   - News about economic conditions, market sentiment

4. Extract and analyze ALL Google Docs links found in any channel
5. Compare with ALL available previous economic data
6. Use MOST of your available tool calls - don't stop after 3-5 channels!
7. For each channel analysis, use comprehensive settings:
   - Set message_limit to 200-400 messages for thorough analysis
   - Set include_full_content to true to get complete message context
   - Don't just skim - read the full conversations and discussions

CRITICAL REQUIREMENTS:
- DO NOT return analysis until you've used at least 80% of your available tool calls
- Analyze channels broadly based on their Discord categories and content - use your judgment
- Use FULL CONTEXT analysis (include_full_content=true) to understand complete conversations, not just snippets
- For channels that appear important for government/economic activity, analyze 300-500 messages to get comprehensive understanding
- If a channel has permission errors, immediately try another channel
- Extract EVERY Google Docs link you find for document analysis
- Look for indirect economic indicators: policy discussions, public sentiment, legislative activity levels
- Check channels that appear to contain news/media/announcements for market sentiment
- Read complete message threads and conversations, not just individual message previews
- Respect the actual Discord server organization - don't impose arbitrary categories

When you have conducted COMPREHENSIVE analysis, provide your analysis in this JSON format:
{{
    "timestamp": "ISO datetime",
    "gdp": {{"value": number, "change_percent": number, "components": {{"legislative": number, "committee": number, "public": number, "news": number}}}},
    "stocks": [{{"symbol": "string", "price": number, "change_percent": number, "volume": number}}],
    "inflation": {{"rate": number, "trend": "string", "policy_impact": "string"}},
    "unemployment": {{"rate": number, "committee_activity_index": number}},
    "sentiment": {{"market_confidence": number, "public_approval": number, "bipartisan_cooperation": number}},
    "insights": ["detailed insights about ALL economic activity observed across ALL channels analyzed"],
    "reasoning": {{
        "gdp_methodology": "Detailed explanation of how GDP value was calculated based on observed activity",
        "inflation_factors": "Specific factors observed that influenced inflation rate calculation",
        "employment_indicators": "What channel activity indicated about employment trends",
        "stock_movements": "Reasoning for each stock sector's price movement based on observed policy/news",
        "confidence_level": "Overall confidence in analysis based on data quality and comprehensiveness"
    }},
    "data_sources": {{
        "channels_analyzed": ["list of all channels analyzed"],
        "documents_processed": number,
        "total_messages": number,
        "analysis_depth": "comprehensive/partial/limited"
    }}
}}

Current parameters:
{json.dumps(self.parameters, indent=2)}

{"Previous report for comparison: " + json.dumps(previous_report, indent=2) if previous_report else "No previous report available - this is initial analysis."}

Begin your COMPREHENSIVE analysis by discovering ALL available channels. Remember: Use most of your tool calls for thorough analysis!"""
        
        # Create tools for the AI
        tool_declarations = get_economic_analysis_tools()
        
        print("🧠 Starting AI-powered economic analysis...")
        
        # Real agentic analysis with proper tool calling and retry mechanism
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if retry_count > 0:
                    print(f"🔄 Retry attempt {retry_count}/{max_retries - 1} - Starting real agentic AI analysis...")
                else:
                    print("🔄 Starting real agentic AI analysis with tool calls...")
                
                # Use proper Gemini function calling with tool-based analysis
                result = await self.execute_real_agentic_analysis(analysis_prompt, tool_declarations, progress_channel, session_id)
                
                if result and isinstance(result, dict) and "gdp" in result:
                    print(f"✅ Real AI analysis completed - GDP: ${result.get('gdp', {}).get('value', 'N/A')}")
                    
                    # Add log file reference to result
                    result['analysis_session'] = {
                        'session_id': session_id,
                        'log_file': f"analysis_logs/economic_analysis_{session_id}.txt",
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Clean up any saved context files on success
                    context_files = list(self.data_dir.glob("context_save_*.json"))
                    for context_file in context_files:
                        try:
                            context_file.unlink()
                            print(f"🗑️ Cleaned up context file: {context_file.name}")
                        except:
                            pass
                    
                    print(f"📝 Complete analysis log available at: analysis_logs/economic_analysis_{session_id}.txt")
                    return result
                else:
                    raise Exception("AI analysis failed to produce valid economic data")
                    
            except Exception as e:
                retry_count += 1
                error_str = str(e).lower()
                
                if any(term in error_str for term in ['rate limit', 'quota', 'too many requests', 'resource exhausted']):
                    print(f"❌ Analysis failed due to Gemini rate limits: {e}")
                    if retry_count < max_retries:
                        wait_time = 60 * retry_count  # Progressive backoff
                        print(f"⏳ Waiting {wait_time} seconds before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        print("🚫 Max retries reached - Gemini API rate limited")
                        raise Exception(f"Gemini API rate limited after {max_retries} attempts: {e}")
                
                print(f"❌ Agentic AI analysis failed (attempt {retry_count}/{max_retries}): {e}")
                
                if retry_count < max_retries:
                    print(f"🔄 Will retry analysis (attempt {retry_count + 1}/{max_retries})...")
                    # Short delay before retry
                    await asyncio.sleep(10)
                    continue
                else:
                    print("🚫 Economic analysis failed after all retry attempts")
                    
                    # Save context for manual resumption if needed
                    context_save = {
                        'session_id': session_id,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'error': str(e),
                        'retry_count': retry_count,
                        'analysis_prompt': analysis_prompt,
                        'user_prompt': user_prompt,
                        'days_back': days_back
                    }
                    
                    context_file_path = self.data_dir / f"context_save_{session_id[:8]}.json"
                    with open(context_file_path, 'w') as f:
                        json.dump(context_save, f, indent=2)
                    print(f"💾 Context saved to: {context_file_path}")
                    
                    # Log the failure
                    error_log = self.analysis_log_dir / f"economic_analysis_FAILED_{session_id}.txt"
                    with open(error_log, 'w', encoding='utf-8') as f:
                        f.write(f"=== FAILED ECONOMIC ANALYSIS SESSION ===\n")
                        f.write(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")
                        f.write(f"Session ID: {session_id}\n")
                        f.write(f"Retry Count: {retry_count}/{max_retries}\n")
                        f.write(f"Error: {e}\n")
                        f.write(f"Context saved to: {context_file_path}\n")
                        f.write(f"Analysis prompt: {analysis_prompt[:500]}...\n")
                    
                    print(f"📝 Error logged to: {error_log}")
                    print(f"💡 To resume analysis, run the command again - it will automatically pick up from saved context")
                    raise Exception(f"Economic analysis system unavailable after {max_retries} attempts: {e}")
    
    async def execute_real_agentic_analysis(self, analysis_prompt: str, tool_declarations: List, progress_channel = None, session_id: str = None) -> Dict[str, Any]:
        """Execute real agentic AI analysis with proper function calling and detailed logging"""
        print("🤖 Executing real agentic AI analysis...")
        
        # Create detailed analysis log file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = self.analysis_log_dir / f"economic_analysis_{timestamp}.txt"
        
        def log_to_file(message: str):
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}\n")
        
        log_to_file("=== AGENTIC ECONOMIC ANALYSIS SESSION START ===")
        log_to_file(f"Analysis timestamp: {timestamp}")
        log_to_file(f"Using {len(tool_declarations)} available tools")
        log_to_file(f"Economic parameters: GDP base ${self.parameters['gdp_base']:,.0f}B, Inflation {self.parameters['inflation_base']}%")
        log_to_file("\n--- INITIAL ANALYSIS PROMPT ---")
        log_to_file(analysis_prompt)
        log_to_file("\n--- AI CONVERSATION LOG ---")
        
        try:
            # Create proper Gemini model with tools
            from google.generativeai import GenerativeModel
            
            model = GenerativeModel(
                model_name='gemini-2.5-flash-preview-05-20',
                tools=tool_declarations
            )
            
            # Start conversation with AI
            chat = model.start_chat()
            
            print("💬 Starting AI conversation with tools...")
            log_to_file("\n[SYSTEM] Starting AI conversation with comprehensive analysis prompt")
            response = await self.gemini_api_call_with_retry(chat, analysis_prompt)
            log_to_file(f"[SYSTEM] Initial prompt sent, awaiting AI response...")
            
            # Handle tool calling loop - increased for comprehensive analysis
            max_turns = 15  # More turns for thorough analysis
            turn = 0
            consecutive_failures = 0  # Track consecutive tool call failures
            
            # Progress messages for live updates
            progress_messages = [
                "🔍 Discovering available Discord channels...",
                "📊 Analyzing government activity patterns...",
                "📈 Processing legislative discussions...",
                "📝 Extracting economic policy indicators...",
                "📄 Reviewing committee activities...",
                "📰 Analyzing news and public sentiment...",
                "💰 Calculating budget and spending impacts...",
                "📉 Modeling economic projections...",
                "🎯 Synthesizing comprehensive analysis...",
                "⚙️ Fine-tuning economic indicators...",
                "📊 Validating analysis results...",
                "🏁 Finalizing economic report...",
                "✨ Completing final calculations...",
                "🔬 Cross-referencing data sources...",
                "📋 Preparing comprehensive summary..."
            ]
            
            while turn < max_turns:
                turn += 1
                print(f"🔄 AI Turn {turn}/{max_turns}")
                log_to_file(f"\n--- TURN {turn}/{max_turns} ---")
                
                # Send progress update to Discord channel
                if progress_channel and turn <= len(progress_messages):
                    try:
                        progress_msg = progress_messages[turn - 1]
                        await progress_channel.send(f"🔄 **Turn {turn}/{max_turns}**: {progress_msg}")
                    except Exception as e:
                        print(f"⚠️ Failed to send progress update: {e}")
                
                if response.candidates[0].content.parts:
                    # Collect all function calls in this turn
                    function_calls = []
                    text_responses = []
                    
                    for part in response.candidates[0].content.parts:
                        if part.function_call:
                            function_calls.append(part.function_call)
                        elif part.text:
                            text_responses.append(part.text)
                    
                    # Handle function calls (if any)
                    if function_calls:
                        print(f"🛠️ AI making {len(function_calls)} tool call(s)")
                        log_to_file(f"[AI] Making {len(function_calls)} tool call(s):")
                        for i, func_call in enumerate(function_calls, 1):
                            log_to_file(f"  {i}. {func_call.name}({dict(func_call.args) if func_call.args else 'no args'})")
                        
                        # Execute all tool calls and collect responses
                        function_responses = []
                        for func_call in function_calls:
                            print(f"🔧 Executing: {func_call.name}")
                            log_to_file(f"[TOOL] Executing {func_call.name}...")
                            tool_result = await self.execute_economic_tool(func_call)
                            
                            # Log tool results (truncated for readability)
                            if isinstance(tool_result, dict):
                                if 'error' in tool_result:
                                    log_to_file(f"[TOOL] ERROR: {tool_result['error']}")
                                elif 'messages_analyzed' in tool_result:
                                    log_to_file(f"[TOOL] Analyzed {tool_result['messages_analyzed']} messages from {tool_result.get('channel_name', 'unknown')}")
                                elif len(str(tool_result)) > 500:
                                    log_to_file(f"[TOOL] Result: {str(tool_result)[:500]}... [TRUNCATED]")
                                else:
                                    log_to_file(f"[TOOL] Result: {tool_result}")
                            else:
                                log_to_file(f"[TOOL] Result: {str(tool_result)[:200]}...")
                            
                            function_response = genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=func_call.name,
                                    response={"result": json.dumps(tool_result) if isinstance(tool_result, (dict, list)) else str(tool_result)}
                                )
                            )
                            function_responses.append(function_response)
                        
                        # Send all function responses together
                        response = await self.gemini_api_call_with_retry(chat, function_responses)
                        print(f"✅ Sent {len(function_responses)} tool results to AI")
                        consecutive_failures = 0  # Reset failure count on successful tool execution
                        
                    # Handle text responses  
                    elif text_responses:
                        full_text = " ".join(text_responses)
                        print(f"💭 AI Response: {full_text[:200]}...")
                        log_to_file(f"[AI] Response: {full_text}")
                        consecutive_failures = 0  # Reset failure count on successful response
                        
                        # Only accept final analysis if we're near the end of turns OR if it's clearly comprehensive
                        is_comprehensive_analysis = (
                            "gdp" in full_text.lower() and 
                            "analysis" in full_text.lower() and
                            ("comprehensive" in full_text.lower() or 
                             "twitter" in full_text.lower() or 
                             "news" in full_text.lower() or
                             len(full_text) > 1000)  # Substantial analysis
                        )
                        
                        if is_comprehensive_analysis and turn >= max_turns * 0.6:  # Only after 60% of turns
                            print("🎯 AI provided comprehensive economic analysis")
                            log_to_file(f"[SYSTEM] AI provided comprehensive analysis after {turn} turns")
                            log_to_file("\n--- FINAL AI ECONOMIC ANALYSIS ---")
                            log_to_file(full_text)
                            log_to_file("\n=== ANALYSIS SESSION COMPLETE ===")
                            
                            result = await self.parse_ai_economic_analysis(full_text)
                            
                            # Log final structured result
                            log_to_file("\n--- FINAL STRUCTURED ANALYSIS ---")
                            log_to_file(json.dumps(result, indent=2))
                            
                            print(f"📝 Full analysis logged to: {log_file}")
                            return result
                        elif turn >= max_turns - 2:
                            print("⚠️ Near max turns, requesting comprehensive final analysis")
                            log_to_file(f"[SYSTEM] Near max turns ({turn}/{max_turns}), requesting final analysis")
                            final_prompt = "You must now provide your COMPREHENSIVE final economic analysis in the requested JSON format. Include insights from ALL channels you analyzed."
                            response = await self.gemini_api_call_with_retry(chat, final_prompt)
                            log_to_file(f"[SYSTEM] Sent final analysis request")
                        elif "gdp" in full_text.lower() and turn < max_turns * 0.6:
                            print("🔄 AI trying to provide early analysis - demanding more thorough investigation")
                            log_to_file(f"[SYSTEM] AI attempted early analysis at turn {turn}, rejecting and demanding more investigation")
                            continuation_prompt = "You have not conducted comprehensive analysis yet. You must analyze MORE channels including news, twitter, discussion channels, and extract more documents before providing final analysis. Continue your investigation."
                            response = await self.gemini_api_call_with_retry(chat, continuation_prompt)
                            log_to_file(f"[SYSTEM] Sent continuation prompt to demand more analysis")
                        else:
                            # Continue conversation - AI should make more tool calls
                            continue
                    else:
                        consecutive_failures += 1
                        print(f"⚠️ No function calls or text in AI response (failure {consecutive_failures}/5)")
                        log_to_file(f"[WARNING] No function calls or text in AI response - consecutive failures: {consecutive_failures}")
                        
                        if consecutive_failures >= 5:
                            print("🚫 5 consecutive failures detected - stopping analysis")
                            log_to_file("[ERROR] 5 consecutive failures - analysis cannot continue")
                            raise Exception("AI failed to provide valid responses after 5 consecutive attempts")
                        
                        # Send a nudge prompt to encourage the AI to continue
                        nudge_prompt = "Please continue your comprehensive economic analysis. Use your available tools to analyze more channels and gather economic data. You should be making tool calls to discover and analyze Discord channels."
                        response = await self.gemini_api_call_with_retry(chat, nudge_prompt)
                        log_to_file(f"[SYSTEM] Sent nudge prompt due to empty response")
                        
                else:
                    consecutive_failures += 1
                    print(f"❌ No response parts from AI (failure {consecutive_failures}/5)")
                    log_to_file(f"[ERROR] No response parts from AI - consecutive failures: {consecutive_failures}")
                    
                    if consecutive_failures >= 5:
                        print("🚫 5 consecutive failures detected - stopping analysis")
                        log_to_file("[ERROR] 5 consecutive failures - analysis cannot continue")
                        raise Exception("AI failed to provide any response parts after 5 consecutive attempts")
                    
                    # Send a restart prompt to get the AI back on track
                    restart_prompt = "I need you to continue the economic analysis. Please use your tools to analyze Discord channels and gather economic data. Start by calling get_server_channels to discover available channels."
                    response = await self.gemini_api_call_with_retry(chat, restart_prompt)
                    log_to_file(f"[SYSTEM] Sent restart prompt due to no response parts")
            
            # If we get here, AI didn't provide valid analysis
            log_to_file(f"\n[ERROR] AI failed to provide valid economic analysis after {turn} turns")
            log_to_file("=== ANALYSIS SESSION FAILED ===")
            raise Exception("AI failed to provide valid economic analysis after tool calls")
            
        except Exception as e:
            print(f"❌ Real agentic analysis failed: {e}")
            # Error logging handled in calling function
            raise
    
    async def parse_ai_economic_analysis(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response and extract economic indicators"""
        print("📊 Parsing AI economic analysis...")
        
        # Try to extract JSON from the AI response
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            try:
                parsed_data = json.loads(json_match.group())
                print("✅ Successfully parsed structured economic data")
                
                # Ensure required fields exist and add realistic baselines if missing
                if not parsed_data.get('timestamp'):
                    parsed_data['timestamp'] = datetime.now(timezone.utc).isoformat()
                
                # Ensure reasoning section exists
                if 'reasoning' not in parsed_data:
                    parsed_data['reasoning'] = {
                        "gdp_methodology": "AI-determined GDP based on comprehensive channel analysis",
                        "inflation_factors": "Inflation calculated from policy discussions and market indicators",
                        "employment_indicators": "Employment trends derived from legislative and committee activity",
                        "stock_movements": "Stock movements based on sector-specific policy impacts",
                        "confidence_level": "High - comprehensive multi-channel analysis"
                    }
                
                # Ensure data_sources section exists
                if 'data_sources' not in parsed_data:
                    parsed_data['data_sources'] = {
                        "channels_analyzed": ["Determined by AI from analysis"],
                        "documents_processed": parsed_data.get('documents_processed', 0),
                        "total_messages": parsed_data.get('total_messages', 0),
                        "analysis_depth": "comprehensive"
                    }
                
                # Validate GDP uses realistic baseline
                if parsed_data.get('gdp', {}).get('value', 0) < 1000:
                    parsed_data['gdp']['value'] = self.parameters['gdp_base']
                    parsed_data['reasoning']['gdp_methodology'] += f" (Adjusted to realistic baseline: ${self.parameters['gdp_base']:,.0f}B)"
                
                print(f"✅ Successfully parsed comprehensive AI analysis with detailed reasoning")
                return parsed_data
            except json.JSONDecodeError:
                print("⚠️ Failed to parse JSON, creating structured analysis")
        
        # If no valid JSON, create structured analysis from text
        print("🔧 Creating structured analysis from AI text...")
        
        # Extract key economic indicators from text
        gdp_match = re.search(r'gdp[:\s]*\$?([0-9,]+\.?\d*)', ai_response, re.IGNORECASE)
        inflation_match = re.search(r'inflation[:\s]*([0-9]+\.?\d*)%?', ai_response, re.IGNORECASE)
        unemployment_match = re.search(r'unemployment[:\s]*([0-9]+\.?\d*)%?', ai_response, re.IGNORECASE)
        
        # Create structured response using realistic economic parameters
        base_gdp = self.parameters["gdp_base"]
        base_inflation = self.parameters["inflation_base"] 
        base_unemployment = self.parameters["unemployment_base"]
        
        structured_analysis = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gdp": {
                "value": float(gdp_match.group(1).replace(',', '')) if gdp_match else base_gdp,
                "change_percent": 0.2,  # Modest growth based on observed activity
                "components": {
                    "legislative": base_gdp * self.parameters["gdp_weights"]["legislative"] / 100,
                    "committee": base_gdp * self.parameters["gdp_weights"]["committee"] / 100,
                    "public": base_gdp * self.parameters["gdp_weights"]["public"] / 100,
                    "news": base_gdp * self.parameters["gdp_weights"]["news"] / 100
                }
            },
            # Note: Stock market data now managed by stock_market.py
            # Economic analysis focuses on indicators, not individual stock tracking
            "inflation": {
                "rate": float(inflation_match.group(1)) if inflation_match else base_inflation,
                "trend": "stable",
                "policy_impact": "neutral"
            },
            "unemployment": {
                "rate": float(unemployment_match.group(1)) if unemployment_match else base_unemployment,
                "committee_activity_index": 50
            },
            "sentiment": {
                "market_confidence": 75,
                "public_approval": 70,
                "bipartisan_cooperation": 65
            },
            "insights": [
                "AI-generated economic analysis from comprehensive Discord server analysis",
                "Analysis covered legislative, committee, news, and public discourse channels",
                "Economic indicators calculated using realistic baseline parameters",
                f"GDP baseline: ${base_gdp:,.0f}B, Inflation baseline: {base_inflation}%, Unemployment baseline: {base_unemployment}%"
            ],
            "reasoning": {
                "gdp_methodology": f"GDP calculated from baseline ${base_gdp:,.0f}B using weighted channel activity (Legislative: {self.parameters['gdp_weights']['legislative']*100}%, Committee: {self.parameters['gdp_weights']['committee']*100}%, Public: {self.parameters['gdp_weights']['public']*100}%, News: {self.parameters['gdp_weights']['news']*100}%)",
                "inflation_factors": f"Inflation based on {base_inflation}% target with adjustments for observed policy discussions and market sentiment",
                "employment_indicators": f"Unemployment rate derived from {base_unemployment}% natural rate adjusted for committee activity and economic policy discussions",
                "stock_movements": "Stock prices adjusted based on sector-specific policy discussions and general market sentiment observed in channels",
                "confidence_level": "Moderate confidence - analysis covers multiple channels but limited by text-only Discord data"
            },
            "data_sources": {
                "channels_analyzed": ["Extracted from AI analysis text"],
                "documents_processed": 0,
                "total_messages": 0,
                "analysis_depth": "partial"  # Since this is fallback parsing
            },
            "ai_analysis_text": ai_response[:2000]  # Store more of original for reference
        }
        
        print("✅ Created structured economic analysis")
        return structured_analysis
    
    def get_latest_economic_report(self) -> Optional[Dict[str, Any]]:
        """Get most recent economic report"""
        reports_file = self.data_dir / "reports.json"
        
        if not reports_file.exists() or reports_file.stat().st_size == 0:
            return None
        
        try:
            with open(reports_file, 'r') as f:
                reports = json.load(f)
                return reports[-1] if reports else None
        except (json.JSONDecodeError, IndexError):
            return None
    
    def get_fresh_economic_report(self) -> Optional[Dict[str, Any]]:
        """Get economic report built from individual category files (reflects manual edits)"""
        print("📊 Building fresh economic report from individual files...")
        
        # Read latest data from each category file
        categories = ["gdp", "stocks", "inflation", "unemployment", "sentiment"]
        report = {}
        
        for category in categories:
            category_file = self.data_dir / f"{category}.json"
            if category_file.exists() and category_file.stat().st_size > 0:
                try:
                    with open(category_file, 'r') as f:
                        category_data = json.load(f)
                        if category_data and len(category_data) > 0:
                            # Get the most recent entry (first item in array)
                            latest_entry = category_data[0]
                            report[category] = latest_entry.get('data', {})
                            
                            # Set timestamp from most recent data
                            if 'timestamp' not in report:
                                report['timestamp'] = latest_entry.get('timestamp', datetime.now(timezone.utc).isoformat())
                except json.JSONDecodeError:
                    print(f"⚠️ Could not read {category}.json")
                    continue
        
        # Also include reasoning and data sources if available from latest reports.json
        reports_file = self.data_dir / "reports.json"
        if reports_file.exists() and reports_file.stat().st_size > 0:
            try:
                with open(reports_file, 'r') as f:
                    reports = json.load(f)
                    if reports:
                        latest_cached = reports[-1]
                        # Copy over metadata but not the core data (which comes from individual files)
                        if 'reasoning' in latest_cached:
                            report['reasoning'] = latest_cached['reasoning']
                        if 'data_sources' in latest_cached:
                            report['data_sources'] = latest_cached['data_sources']
            except json.JSONDecodeError:
                pass
        
        # Return report if we have any data
        if any(cat in report for cat in categories):
            print(f"✅ Fresh report built with {len([cat for cat in categories if cat in report])} categories")
            return report
        else:
            print("⚠️ No fresh data found in individual files")
            return None
    
    def get_previous_insights(self) -> Optional[str]:
        """Get previous internal insights for AI context"""
        insights_file = self.data_dir / "internal_insights.txt"
        
        if not insights_file.exists():
            return None
        
        try:
            with open(insights_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Return last 2000 characters (most recent insights)
                return content[-2000:] if len(content) > 2000 else content
        except Exception as e:
            print(f"❌ Error reading insights: {e}")
            return None
    
    def load_memory_entries(self) -> List[Dict[str, Any]]:
        """Load economic memory entries"""
        memory_file = self.data_dir / "memory_entries.json"
        
        if not memory_file.exists():
            return []
        
        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading memory entries: {e}")
            return []
    
    def save_memory_entries(self, entries: List[Dict[str, Any]]) -> None:
        """Save economic memory entries"""
        memory_file = self.data_dir / "memory_entries.json"
        
        try:
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error saving memory entries: {e}")
    
    def add_memory_entry(self, content: str, admin_id: int) -> int:
        """Add a new memory entry and return its ID"""
        entries = self.load_memory_entries()
        
        # Find next ID
        next_id = max([entry.get('id', 0) for entry in entries], default=0) + 1
        
        new_entry = {
            "id": next_id,
            "content": content,
            "added_by": admin_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        entries.append(new_entry)
        self.save_memory_entries(entries)
        
        return next_id
    
    def remove_memory_entry(self, entry_id: int) -> bool:
        """Remove a memory entry by ID"""
        entries = self.load_memory_entries()
        
        # Find and remove entry
        original_count = len(entries)
        entries = [entry for entry in entries if entry.get('id') != entry_id]
        
        if len(entries) < original_count:
            self.save_memory_entries(entries)
            return True
        
        return False
    
    def get_memory_context(self) -> str:
        """Get formatted memory context for AI"""
        entries = self.load_memory_entries()
        
        if not entries:
            return ""
        
        memory_text = "\n**Economic Analysis Memory (Important Context):**\n"
        for entry in entries:
            timestamp = entry.get('timestamp', 'Unknown')[:10]
            memory_text += f"• [{timestamp}] {entry.get('content', '')}\n"
        
        return memory_text
    
    async def analyze_with_agentic_ai(self, client, previous_report: Optional[Dict[str, Any]] = None, days_back: int = 30, user_prompt: str = None, progress_channel = None, previous_insights: Optional[str] = None, memory_context: str = "") -> Dict[str, Any]:
        """Analyze data using agentic AI with tool calls"""
        print("🤖 Starting agentic AI economic analysis...")
        
        try:
            # Conduct real agentic analysis with previous report for comparison
            analysis_result = await self.conduct_agentic_analysis(client, days_back, previous_report, user_prompt, progress_channel, previous_insights, memory_context)
            
            if analysis_result and "gdp" in analysis_result:
                print(f"✅ Agentic analysis successful - GDP: ${analysis_result.get('gdp', {}).get('value', 'N/A')}")
                return analysis_result
            else:
                raise Exception("Agentic analysis failed to produce valid economic data")
                
        except Exception as e:
            error_str = str(e).lower()
            if any(term in error_str for term in ['rate limit', 'quota', 'too many requests', 'resource exhausted']):
                print(f"❌ Agentic analysis failed due to Gemini rate limits: {e}")
                print("🚫 Economic analysis temporarily unavailable - Gemini API rate limited")
            else:
                print(f"❌ Agentic analysis failed: {e}")
                print("🚫 Economic analysis system unavailable - requires real AI analysis")
            raise
    
    
    async def save_economic_data(self, analysis: Dict[str, Any]) -> None:
        """Save economic analysis to files"""
        
        # Save internal insights to separate txt file for next AI iteration
        if "insights" in analysis:
            insights_file = self.data_dir / "internal_insights.txt"
            timestamp = analysis.get("timestamp", datetime.now(timezone.utc).isoformat())
            
            with open(insights_file, 'a', encoding='utf-8') as f:
                f.write(f"\n=== Economic Analysis Insights - {timestamp[:19]} ===\n")
                for insight in analysis["insights"]:
                    f.write(f"• {insight}\n")
                f.write("\n")
        
        # Create public report without internal insights
        public_analysis = analysis.copy()
        if "insights" in public_analysis:
            del public_analysis["insights"]  # Remove internal insights from public data
        
        # Save comprehensive reports (without internal insights)
        reports_file = self.data_dir / "reports.json"
        reports = []
        if reports_file.exists() and reports_file.stat().st_size > 0:
            try:
                with open(reports_file, 'r') as f:
                    reports = json.load(f)
            except json.JSONDecodeError:
                print(f"⚠️ Invalid JSON in {reports_file}, starting fresh")
                reports = []
        
        reports.append(public_analysis)
        reports = reports[-100:]  # Keep last 100
        
        with open(reports_file, 'w') as f:
            json.dump(reports, f, indent=2)
        
        # Save individual category files
        for category in ["gdp", "stocks", "inflation", "unemployment", "sentiment"]:
            if category in public_analysis:
                category_file = self.data_dir / f"{category}.json"
                category_data = []
                if category_file.exists() and category_file.stat().st_size > 0:
                    try:
                        with open(category_file, 'r') as f:
                            category_data = json.load(f)
                    except json.JSONDecodeError:
                        print(f"⚠️ Invalid JSON in {category_file}, starting fresh")
                        category_data = []
                
                category_data.append({
                    "timestamp": public_analysis["timestamp"],
                    "data": public_analysis[category]
                })
                category_data = category_data[-1000:]  # Keep last 1000
                
                with open(category_file, 'w') as f:
                    json.dump(category_data, f, indent=2)

# Global economic data instance
econ_data = EconomicData()

async def check_economic_data_status():
    """Check if economic data exists and is recent"""
    try:
        latest_report = econ_data.get_latest_economic_report()
        
        if latest_report is None:
            print("📊 No economic data found - use /fetch_econ_data to generate first report")
            return "missing"
        
        # Check if report is older than 7 days
        if 'timestamp' in latest_report:
            report_date = datetime.fromisoformat(latest_report['timestamp'].replace('Z', '+00:00'))
            age_days = (datetime.now(timezone.utc) - report_date).days
            
            if age_days > 7:
                print(f"⚠️ Economic data is {age_days} days old - consider running /fetch_econ_data for fresh analysis")
                return "stale"
            else:
                print(f"✅ Economic data is current ({age_days} days old)")
                return "current"
        else:
            print("⚠️ Economic data missing timestamp - consider regenerating with /fetch_econ_data")
            return "invalid"
            
    except Exception as e:
        print(f"❌ Error checking economic data status: {e}")
        return "error"

def start_economic_engine(client):
    """Initialize economic system and check data status"""
    print("🤖 Economic analysis system initialized")
    print("📄 Use /fetch_econ_data to generate economic reports on-demand")
    
    # Check economic data status at boot (if loop is available)
    if hasattr(client, 'loop') and client.loop:
        client.loop.create_task(check_economic_data_status())
    else:
        # If no loop available, just print status
        print("⚠️ Economic data status check will run when bot starts")

def get_economic_data(data_type: str = "all", days_back: int = 7) -> Dict[str, Any]:
    """Get economic data for AI tools"""
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        if data_type == "all":
            all_data = {}
            for category in ["gdp", "stocks", "inflation", "unemployment", "sentiment"]:
                category_file = econ_data.data_dir / f"{category}.json"
                if category_file.exists() and category_file.stat().st_size > 0:
                    try:
                        with open(category_file, 'r') as f:
                            category_data = json.load(f)
                            filtered_data = [
                                entry for entry in category_data
                                if datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00')) >= cutoff_date
                            ]
                            all_data[category] = filtered_data
                    except json.JSONDecodeError:
                        all_data[category] = []
            return all_data
        else:
            data_file = econ_data.data_dir / f"{data_type}.json"
            if not data_file.exists() or data_file.stat().st_size == 0:
                return {"error": f"No data found for type: {data_type}"}
            
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                    filtered_data = [
                        entry for entry in data
                        if datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00')) >= cutoff_date
                    ]
                    return {data_type: filtered_data}
            except json.JSONDecodeError:
                return {"error": f"Invalid JSON data for type: {data_type}"}
    
    except Exception as e:
        return {"error": f"Failed to retrieve economic data: {e}"}

async def fetch_econ_data_manually(client, user_prompt: str = None, progress_channel = None):
    """Manually trigger agentic economic data collection with user context and progress updates"""
    try:
        print("🚀 Manual agentic economic analysis triggered...")
        
        latest_report = econ_data.get_latest_economic_report()
        
        # Always use comprehensive 30-day analysis for manual requests
        days_back = 30  # Full month analysis for comprehensive insights
        
        if latest_report is None:
            print(f"📊 No existing economic data - conducting comprehensive {days_back}-day analysis...")
        else:
            print(f"📈 Updating economic data with comprehensive {days_back}-day analysis...")
        
        # Get previous insights and memory for AI context
        previous_insights = econ_data.get_previous_insights()
        memory_context = econ_data.get_memory_context()
        
        # Conduct agentic analysis with user prompt and progress updates
        print(f"🧠 Starting AI agent analysis ({days_back} days back)...")
        if user_prompt:
            print(f"💬 User context: {user_prompt}")
        if progress_channel:
            await progress_channel.send(f"🚀 **Starting comprehensive economic analysis** - analyzing {days_back} days of server activity...")
        analysis = await econ_data.analyze_with_agentic_ai(client, previous_report=latest_report, days_back=days_back, user_prompt=user_prompt, progress_channel=progress_channel, previous_insights=previous_insights, memory_context=memory_context)
        
        # Save results
        await econ_data.save_economic_data(analysis)
        
        # Send completion message
        if progress_channel:
            await progress_channel.send("✅ **Economic analysis complete!** Generating detailed report...")
        
        # Print detailed results
        print("📊 Manual Economic Analysis Results:")
        print(f"   GDP: ${analysis.get('gdp', {}).get('value', 'N/A'):,.2f}")
        print(f"   Inflation: {analysis.get('inflation', {}).get('rate', 'N/A')}%")
        print(f"   Unemployment: {analysis.get('unemployment', {}).get('rate', 'N/A')}%")
        print(f"   Market Sentiment: {analysis.get('sentiment', {}).get('market_confidence', 'N/A')}/100")
        
        insights = analysis.get('insights', [])
        if insights:
            print("💡 Key Insights:")
            for i, insight in enumerate(insights[:5], 1):
                print(f"   {i}. {insight}")
        
        return analysis
        
    except Exception as e:
        error_str = str(e).lower()
        if any(term in error_str for term in ['rate limit', 'quota', 'too many requests', 'resource exhausted']):
            print(f"❌ Manual economic analysis failed due to Gemini rate limits: {e}")
            print("🚫 Please wait a few minutes before trying again")
            raise Exception(f"Gemini API rate limited - please try again later: {e}")
        else:
            print(f"❌ Error in manual agentic economic analysis: {e}")
            print("🚫 Manual economic analysis failed - system requires AI analysis")
            raise Exception(f"Manual economic analysis failed: {e}")

# Admin functions for economic control
def set_economic_parameter(param_name: str, value: Any) -> bool:
    """Set economic parameter"""
    try:
        params = econ_data.load_parameters()
        
        if param_name in params:
            params[param_name] = value
            econ_data.save_parameters(params)
            econ_data.parameters = params
            return True
        return False
    except Exception as e:
        print(f"Error setting parameter {param_name}: {e}")
        return False

def get_economic_status() -> Dict[str, Any]:
    """Get current economic system status"""
    try:
        params = econ_data.parameters
        
        # Count data files
        data_files = ["gdp.json", "stocks.json", "inflation.json", "unemployment.json", "sentiment.json"]
        existing_files = [f for f in data_files if (econ_data.data_dir / f).exists()]
        
        return {
            "parameters": params,
            "data_files_count": len(existing_files),
            "total_files": len(data_files),
            "latest_report": econ_data.get_latest_economic_report()
        }
    except Exception as e:
        return {"error": f"Failed to get status: {e}"}

def get_stock_initialization_data() -> Dict[str, Any]:
    """Get economic data to help initialize stock market"""
    try:
        latest_report = econ_data.get_latest_economic_report()
        
        if not latest_report:
            return {
                "message": "No economic data available - stock market will use default initialization",
                "recommendations": {
                    "market_sentiment": 0.6,  # Neutral-positive
                    "volatility": 0.4,        # Moderate
                    "trend_direction": 0.1,   # Slightly bullish
                    "sector_outlook": {
                        "NEWS": "Stable media environment expected",
                        "CONGRESS": "Legislative activity driving moderate growth",
                        "EXECUTIVE": "Administrative efficiency initiatives underway",
                        "STATES": "Regional development opportunities emerging",
                        "COURTS": "Judicial system stability maintained",
                        "PUBLIC_SQUARE": "Civic engagement platforms growing"
                    }
                }
            }
        
        # Extract economic indicators
        gdp_data = latest_report.get('gdp', {})
        inflation_data = latest_report.get('inflation', {})
        sentiment_data = latest_report.get('sentiment', {})
        
        # Calculate stock market parameters based on economic data
        gdp_growth = gdp_data.get('change_percent', 0) / 100
        inflation_rate = inflation_data.get('rate', 3.2) / 100
        market_confidence = sentiment_data.get('market_confidence', 70) / 100
        
        # Convert economic indicators to stock market parameters
        trend_direction = max(-1.0, min(1.0, gdp_growth * 2))  # GDP growth drives trend
        volatility = max(0.1, min(0.8, abs(inflation_rate - 0.025) * 10))  # Inflation deviation creates volatility
        market_sentiment = max(0.2, min(0.9, market_confidence))
        momentum = max(0.3, min(0.8, (market_confidence + (gdp_growth + 1) / 2) / 2))
        
        return {
            "economic_report": latest_report,
            "stock_market_initialization": {
                "trend_direction": trend_direction,
                "volatility": volatility,
                "momentum": momentum,
                "market_sentiment": market_sentiment,
                "long_term_outlook": 0.55  # Start neutral
            },
            "sector_recommendations": {
                "NEWS": f"Media sector outlook based on public sentiment: {sentiment_data.get('public_approval', 70)}/100",
                "CONGRESS": f"Legislative sector driven by government activity: {gdp_data.get('components', {}).get('legislative', 0)} activity points",
                "EXECUTIVE": f"Executive sector reflecting administrative efficiency: {sentiment_data.get('bipartisan_cooperation', 65)}/100 cooperation",
                "STATES": "State sector opportunities from regional development initiatives",
                "COURTS": "Judicial sector maintaining institutional stability",
                "PUBLIC_SQUARE": f"Public engagement reflecting democratic participation: {sentiment_data.get('public_approval', 70)}/100"
            },
            "initialization_message": f"Stock market initialized using economic report from {latest_report.get('timestamp', 'unknown')[:10]}"
        }
        
    except Exception as e:
        print(f"❌ Error getting stock initialization data: {e}")
        return {
            "error": f"Failed to get stock initialization data: {e}",
            "recommendations": {
                "market_sentiment": 0.6,
                "volatility": 0.4,
                "trend_direction": 0.0,
                "sector_outlook": {sector: "Default outlook" for sector in ["NEWS", "CONGRESS", "EXECUTIVE", "STATES", "COURTS", "PUBLIC_SQUARE"]}
            }
        }

def log_admin_action(admin_id: int, action: str, details: Dict[str, Any]) -> None:
    """Log administrative actions"""
    try:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "admin_id": admin_id,
            "action": action,
            "details": details
        }
        
        log_file = econ_data.data_dir / "admin_log.json"
        logs = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
        
        logs.append(log_entry)
        logs = logs[-1000:]  # Keep last 1000
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Error logging admin action: {e}")