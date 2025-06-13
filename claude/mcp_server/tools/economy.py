"""
Economic analysis and stock market tools for MCP server
"""

import json
import sys
import time
import os
import aiohttp
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

import economic_utils
import config
from .standalone_economy import standalone_economy
# import economic_engine  # Skip due to Discord dependencies  
# import economic_admin   # Skip due to Discord dependencies
# import econ_memory_commands  # Skip due to Discord dependencies - using econ_data instead

class EconomyTools:
    """Tools for economic analysis and stock market operations"""
    
    def __init__(self):
        self.stock_market = None
        self.trading_system = None
        self.discord_token = os.getenv('DISCORD_TOKEN')
        self.guild_id = os.getenv('GUILD')
        self.base_url = "https://discord.com/api/v10"
        self.session = None
        self._initialize_systems()
    
    def _initialize_systems(self):
        """Initialize stock market and trading systems if available"""
        try:
            import stock_market
            import stock_trading
            self.stock_market = stock_market.get_stock_market()
            self.trading_system = stock_trading.get_stock_trading_system()
        except ImportError:
            pass
    
    async def _get_session(self):
        """Get or create aiohttp session for Discord API"""
        if self.session is None:
            headers = {
                "Authorization": f"Bot {self.discord_token}",
                "Content-Type": "application/json"
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def _get_channel_id(self, channel_name: str) -> Optional[str]:
        """Get channel ID from channel name by searching guild channels"""
        if not self.guild_id:
            return None
        
        session = await self._get_session()
        try:
            url = f"{self.base_url}/guilds/{self.guild_id}/channels"
            async with session.get(url) as response:
                if response.status == 200:
                    channels = await response.json()
                    for channel in channels:
                        if channel.get('name') == channel_name:
                            return channel.get('id')
        except Exception:
            pass
        return None
    
    async def _fetch_channel_messages(self, channel_id: str, days_back: int, message_limit: int) -> List[Dict[str, Any]]:
        """Fetch messages from a Discord channel"""
        session = await self._get_session()
        messages = []
        
        # Calculate timestamp for filtering
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        try:
            url = f"{self.base_url}/channels/{channel_id}/messages"
            params = {"limit": min(message_limit, 100)}  # Discord API limit
            
            while len(messages) < message_limit:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        break
                    
                    batch = await response.json()
                    if not batch:
                        break
                    
                    for msg in batch:
                        # Parse timestamp
                        timestamp_str = msg.get('timestamp', '')
                        try:
                            msg_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if msg_time < cutoff_time:
                                return messages  # Stop if we've gone too far back
                        except:
                            continue
                        
                        # Add to messages
                        messages.append({
                            'id': msg.get('id'),
                            'content': msg.get('content', ''),
                            'author': msg.get('author', {}).get('username', 'Unknown'),
                            'timestamp': timestamp_str,
                            'channel': channel_id
                        })
                        
                        if len(messages) >= message_limit:
                            break
                    
                    # Set up for next batch
                    if len(batch) == 100:  # Full batch, might be more
                        params['before'] = batch[-1]['id']
                    else:
                        break  # Partial batch, no more messages
                        
        except Exception as e:
            print(f"Error fetching messages: {e}")
        
        return messages
    
    async def cleanup(self):
        """Close aiohttp session if open"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_economic_report(self) -> Dict[str, Any]:
        """Get comprehensive economic report with all indicators"""
        
        try:
            report = standalone_economy.get_fresh_economic_report()
            
            # Add metadata
            enhanced_report = {
                "status": "success",
                "last_updated": report.get("metadata", {}).get("last_updated", "Unknown"),
                "data": report,
                "summary": {
                    "gdp_current": f"${report['gdp']['current_gdp']:,.1f}T",
                    "gdp_growth": f"{report['gdp']['quarterly_growth_percent']}%",
                    "inflation_rate": f"{report['inflation']['yoy_percent']}%",
                    "fed_funds_rate": f"{report['inflation']['federal_funds_rate']}%",
                    "unemployment_rate": f"{report['unemployment']['rate_percent']}%",
                    "market_confidence": f"{report['sentiment']['confidence_percent']}%",
                    "anxiety_index": f"{report['sentiment']['anxiety_index_percent']}%"
                }
            }
            
            return enhanced_report
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get economic report: {str(e)}"
            }
    
    async def get_economic_summary(self) -> Dict[str, Any]:
        """Get condensed economic summary with key metrics"""
        
        try:
            report = standalone_economy.get_fresh_economic_report()
            
            summary = {
                "status": "success",
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
                },
                "last_updated": report.get("metadata", {}).get("last_updated", "Unknown")
            }
            
            return summary
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get economic summary: {str(e)}"
            }
    
    async def trigger_economic_analysis(self, force_update: bool = False) -> Dict[str, Any]:
        """Trigger a new economic analysis cycle"""
        
        try:
            # This would trigger the economic analysis system
            # For now, return a mock response
            return {
                "status": "success",
                "message": "Economic analysis triggered successfully",
                "force_update": force_update,
                "estimated_completion": "5-10 minutes",
                "note": "This is a mock response. In production, this would trigger the actual economic analysis system."
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to trigger economic analysis: {str(e)}"
            }
    
    async def get_stock_market_overview(self) -> Dict[str, Any]:
        """Get current stock market overview with sector performance"""
        
        try:
            # Use standalone economy to get stock market data
            market_data = standalone_economy.get_stock_market_data()
            if not market_data:
                return {
                    "status": "error",
                    "error": "Stock market data not available"
                }
            
            overview = {
                "status": "success",
                "market_status": "simulated",  # Market is always simulated
                "parameters": market_data.get("market_params", {}),
                "last_update": market_data.get("last_updated", "Unknown"),
                "sectors": {},
                "total_stocks": 0,
                "available_sectors": []
            }
            
            # Get sector performance from market data
            categories = market_data.get("categories", {})
            for sector_name, category_data in categories.items():
                stocks = category_data.get("stocks", [])
                stock_symbols = [stock.get("symbol") for stock in stocks]
                
                sector_data = {
                    "stocks": stock_symbols,
                    "stock_count": len(stock_symbols),
                    "prices": {},
                    "average_price": 0,
                    "total_value": 0
                }
                
                sector_prices = []
                for stock in stocks:
                    symbol = stock.get("symbol")
                    price = stock.get("price", 0)
                    if symbol and price:
                        sector_data["prices"][symbol] = price
                        sector_prices.append(price)
                
                if sector_prices:
                    sector_data["average_price"] = round(sum(sector_prices) / len(sector_prices), 2)
                    sector_data["total_value"] = round(sum(sector_prices), 2)
                
                overview["sectors"][sector_name] = sector_data
            
            # Update totals
            overview["total_stocks"] = sum(len(cat.get("stocks", [])) for cat in categories.values())
            overview["available_sectors"] = list(categories.keys())
            
            return overview
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get stock market overview: {str(e)}"
            }
    
    async def get_stock_price(self, symbol: str, include_history: bool = False) -> Dict[str, Any]:
        """Get current price and information for a specific stock"""
        
        try:
            # Use standalone economy to get stock price
            price_data = standalone_economy.get_stock_price(symbol)
            
            if not price_data or "error" in price_data:
                return {
                    "status": "error",
                    "symbol": symbol,
                    "error": price_data.get("error", "Stock not found") if price_data else "Stock data not available"
                }
            
            result = {
                "status": "success",
                "symbol": symbol,
                "current_price": price_data["current"],
                "company_name": price_data.get("company_name", "Unknown"),
                "sector": price_data.get("sector", "Unknown"),
                "industry": price_data.get("industry", "Unknown"),
                "daily_range_low": price_data.get("daily_range_low", 0),
                "daily_range_high": price_data.get("daily_range_high", 0),
                "sector_factor": price_data.get("sector_factor", 1.0),
                "last_updated": price_data.get("last_updated", "Unknown")
            }
            
            # Add price history if requested
            if include_history:
                try:
                    history_data = standalone_economy.get_stock_history()
                    if history_data and symbol in history_data:
                        result["price_history"] = history_data[symbol]
                    else:
                        result["history_note"] = "Price history not available for this stock"
                except:
                    result["history_error"] = "Failed to retrieve price history"
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "symbol": symbol,
                "error": f"Failed to get stock price: {str(e)}"
            }
    
    async def execute_stock_trade(
        self,
        user_id: str,
        action: str,
        symbol: str,
        quantity: int,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a stock trade for a user (requires authentication)"""
        
        if not self.trading_system:
            return {
                "status": "error",
                "error": "Trading system not available"
            }
        
        # Validate action
        if action not in ["buy", "sell"]:
            return {
                "status": "error",
                "error": "Invalid action. Must be 'buy' or 'sell'",
                "action": action
            }
        
        # Validate quantity
        if quantity <= 0 or quantity > 1000:
            return {
                "status": "error",
                "error": "Invalid quantity. Must be between 1 and 1000",
                "quantity": quantity
            }
        
        # TODO: Implement authentication check
        if not auth_token:
            return {
                "status": "error",
                "error": "Authentication token required for trading operations"
            }
        
        try:
            # Execute the trade
            if action == "buy":
                result = await self.trading_system.buy_stock(user_id, symbol, quantity)
            else:
                result = await self.trading_system.sell_stock(user_id, symbol, quantity)
            
            return {
                "status": "success" if result["success"] else "error",
                "user_id": user_id,
                "action": action,
                "symbol": symbol,
                "quantity": quantity,
                "trade_result": result
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to execute trade: {str(e)}",
                "user_id": user_id,
                "action": action,
                "symbol": symbol,
                "quantity": quantity
            }
    
    async def get_user_portfolio(self, user_id: str, include_history: bool = False) -> Dict[str, Any]:
        """Get user's stock portfolio and net worth"""
        
        if not self.trading_system:
            return {
                "status": "error",
                "error": "Trading system not available"
            }
        
        try:
            portfolio_data = await self.trading_system.get_portfolio(user_id)
            
            result = {
                "status": "success",
                "user_id": user_id,
                "portfolio": portfolio_data,
                "last_updated": "2024-01-01T12:00:00Z"  # Would use actual timestamp
            }
            
            # Add portfolio history if requested
            if include_history:
                # TODO: Implement portfolio history tracking
                result["portfolio_history"] = {
                    "note": "Portfolio history tracking not yet implemented"
                }
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "user_id": user_id,
                "error": f"Failed to get portfolio: {str(e)}"
            }
    
    async def set_economic_parameter(
        self,
        parameter: str,
        value: float,
        admin_token: str
    ) -> Dict[str, Any]:
        """Set economic parameter (admin only)"""
        
        # TODO: Implement proper admin authentication
        if not admin_token or admin_token != "admin_token_placeholder":
            return {
                "status": "error",
                "error": "Invalid admin token"
            }
        
        # Validate parameter name
        valid_parameters = [
            "inflation_rate", "gdp_growth", "unemployment_rate",
            "federal_funds_rate", "market_confidence", "anxiety_index"
        ]
        
        if parameter not in valid_parameters:
            return {
                "status": "error",
                "error": f"Invalid parameter. Valid options: {', '.join(valid_parameters)}",
                "parameter": parameter
            }
        
        try:
            # TODO: Implement actual parameter setting
            return {
                "status": "success",
                "parameter": parameter,
                "old_value": "unknown",  # Would get actual old value
                "new_value": value,
                "message": f"Parameter '{parameter}' set to {value}",
                "note": "This is a mock response. In production, this would update the actual economic parameters."
            }
            
        except Exception as e:
            return {
                "status": "error",
                "parameter": parameter,
                "value": value,
                "error": f"Failed to set parameter: {str(e)}"
            }
    
    async def get_market_sectors(self) -> Dict[str, Any]:
        """Get list of all market sectors and their stocks"""
        
        if not self.stock_market:
            return {
                "status": "error",
                "error": "Stock market system not available"
            }
        
        try:
            sectors_data = {}
            
            for sector_name, stock_symbols in self.stock_market.sectors.items():
                sector_info = {
                    "name": sector_name,
                    "stock_count": len(stock_symbols),
                    "stocks": []
                }
                
                for symbol in stock_symbols:
                    try:
                        stock_info = self.stock_market.get_stock_info(symbol)
                        sector_info["stocks"].append({
                            "symbol": symbol,
                            "company_name": stock_info.get("company_name", "Unknown"),
                            "industry": stock_info.get("industry", "Unknown")
                        })
                    except:
                        sector_info["stocks"].append({
                            "symbol": symbol,
                            "company_name": "Unknown",
                            "industry": "Unknown"
                        })
                
                sectors_data[sector_name] = sector_info
            
            return {
                "status": "success",
                "total_sectors": len(sectors_data),
                "total_stocks": sum(len(self.stock_market.sectors[s]) for s in self.stock_market.sectors),
                "sectors": sectors_data
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get market sectors: {str(e)}"
            }
    
    # ==================== AGENTIC ECONOMIC ANALYSIS TOOLS ====================
    
    async def get_server_channels(self, channel_type: Optional[str] = None) -> Dict[str, Any]:
        """Get available Discord channels for economic analysis"""
        
        try:
            # Return the authorized channels for economic analysis
            # Based on the whitelist from economic_utils
            authorized_channels = {
                "NEWS": [
                    "news-information", "official-rp-news", "parody", "pbn", 
                    "liberty-ledger", "wall-street-journal", "4e-news-from-the-hill", 
                    "202news", "msnbc"
                ],
                "CONGRESS": [
                    "speaker-announcements", "house-docket", "house-floor", 
                    "house-vote-results", "senate-announcements", "senate-docket", 
                    "senate-floor", "senate-vote-results", "committee-announcements"
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
                "COURTS": ["district-court-announcements", "supreme-court-announcements"],
                "PUBLIC_SQUARE": [
                    "rp-chat", "twitter-rp", "press-releases", "press-room", 
                    "election-announcements"
                ]
            }
            
            if channel_type:
                channels = authorized_channels.get(channel_type.upper(), [])
            else:
                channels = []
                for cat_channels in authorized_channels.values():
                    channels.extend(cat_channels)
            
            return {
                "status": "success",
                "channel_type": channel_type,
                "channels": channels,
                "total_channels": len(channels),
                "authorized_only": True,
                "available_categories": list(authorized_channels.keys())
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get server channels: {str(e)}"
            }
    
    async def analyze_channel_activity(
        self,
        channel_name: str,
        days_back: int = 7,
        message_limit: int = 100,
        include_full_content: bool = False
    ) -> Dict[str, Any]:
        """Analyze Discord channel activity for economic insights"""
        
        try:
            # Check if channel is authorized using real function
            if not economic_utils.is_channel_allowed(channel_name):
                return {
                    "status": "error",
                    "channel_name": channel_name,
                    "error": f"Channel '{channel_name}' not authorized for economic analysis"
                }
            
            # Get real channel category
            channel_category = economic_utils.get_channel_category(channel_name)
            
            # Get channel ID
            channel_id = await self._get_channel_id(channel_name)
            if not channel_id:
                return {
                    "status": "error",
                    "channel_name": channel_name,
                    "channel_category": channel_category,
                    "error": f"Channel '{channel_name}' not found in Discord server"
                }
            
            # Fetch messages
            messages = await self._fetch_channel_messages(channel_id, days_back, message_limit)
            
            # Filter and format messages
            formatted_messages = []
            for msg in messages:
                if include_full_content:
                    formatted_messages.append({
                        "content": msg["content"],
                        "author": msg["author"],
                        "timestamp": msg["timestamp"],
                        "channel": channel_name
                    })
                else:
                    # Truncate content for summary
                    content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
                    formatted_messages.append({
                        "content": content,
                        "author": msg["author"],
                        "timestamp": msg["timestamp"],
                        "channel": channel_name
                    })
            
            return {
                "status": "success",
                "channel_name": channel_name,
                "channel_category": channel_category,
                "parameters": {
                    "days_back": days_back,
                    "message_limit": message_limit,
                    "include_full_content": include_full_content
                },
                "messages": formatted_messages,
                "total_messages": len(formatted_messages),
                "analysis_summary": {
                    "time_range": f"Last {days_back} days",
                    "activity_level": "high" if len(formatted_messages) > 50 else "medium" if len(formatted_messages) > 10 else "low",
                    "channel_type": channel_category
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "channel_name": channel_name,
                "error": f"Failed to analyze channel activity: {str(e)}"
            }
    
    async def extract_document_data(self, doc_url: str) -> Dict[str, Any]:
        """Extract and analyze Google Docs content for economic relevance"""
        
        try:
            # Import the fetch function we need
            from ai_tools import fetch_document_content
            
            # Fetch document content
            content = await fetch_document_content(doc_url)
            
            if not content:
                return {
                    "status": "error",
                    "document_url": doc_url,
                    "error": "Failed to fetch document content"
                }
            
            # Basic economic keyword analysis
            economic_keywords = [
                "gdp", "inflation", "unemployment", "budget", "tax", "spending",
                "economic", "finance", "fiscal", "monetary", "policy", "market"
            ]
            
            content_lower = content.lower()
            keywords_found = [kw for kw in economic_keywords if kw in content_lower]
            economic_relevance_score = len(keywords_found) / len(economic_keywords)
            
            doc_data = {
                "content": content,
                "content_length": len(content),
                "economic_relevance_score": economic_relevance_score,
                "keywords_found": keywords_found,
                "document_url": doc_url
            }
            
            return {
                "status": "success",
                "document_url": doc_url,
                "content_length": len(content),
                "economic_relevance_score": economic_relevance_score,
                "keywords_found": keywords_found,
                "document_data": doc_data
            }
            
        except Exception as e:
            return {
                "status": "error",
                "document_url": doc_url,
                "error": f"Failed to extract document data: {str(e)}"
            }
    
    async def get_previous_economic_data(self, days_back: int = 30) -> Dict[str, Any]:
        """Retrieve historical economic reports for trend analysis"""
        
        try:
            # Use the actual function from economic_utils
            historical_data = economic_utils.get_economic_data("all", days_back)
            
            return {
                "status": "success",
                "days_back": days_back,
                "data_points": len(historical_data) if isinstance(historical_data, list) else 1,
                "historical_data": historical_data,
                "analysis_period": f"Last {days_back} days"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "days_back": days_back,
                "error": f"Failed to get previous economic data: {str(e)}"
            }
    
    async def trigger_comprehensive_economic_analysis(
        self,
        user_prompt: Optional[str] = None,
        force_update: bool = False,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Trigger comprehensive agentic economic analysis"""
        
        try:
            # Call the actual agentic analysis function
            # Note: This requires a Discord client, so we'll return the trigger info
            # In a real MCP implementation, this would need proper client handling
            
            return {
                "status": "error", 
                "error": "Comprehensive analysis requires Discord client access not available in MCP context",
                "user_prompt": user_prompt,
                "force_update": force_update,
                "days_back": days_back,
                "note": "Use fetch_econ_data_manually function directly in VCBot Discord context instead"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to trigger comprehensive analysis: {str(e)}"
            }
    
    async def get_stock_initialization_data(self) -> Dict[str, Any]:
        """Get stock market initialization parameters from economic data"""
        
        try:
            # Use the actual function from stock_market
            if self.stock_market:
                init_data = self.stock_market._calculate_market_params_from_economic_data()
                
                return {
                    "status": "success",
                    "initialization_data": init_data,
                    "economic_driven": True,
                    "parameters_calculated": list(init_data.keys()) if isinstance(init_data, dict) else 0
                }
            else:
                return {
                    "status": "error",
                    "error": "Stock market system not available"
                }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get stock initialization data: {str(e)}"
            }
    
    async def submit_daily_stock_initialization(
        self,
        market_parameters: Dict[str, float],
        invisible_factors: Dict[str, float],
        daily_stock_prices: Dict[str, Dict[str, float]],
        sector_outlook: Dict[str, str],
        reasoning: Dict[str, str]
    ) -> Dict[str, Any]:
        """Submit daily stock market initialization with AI-analyzed parameters"""
        
        try:
            if not self.stock_market:
                return {
                    "status": "error",
                    "error": "Stock market system not initialized"
                }
            
            # Validate required parameters
            required_market_params = ["trend_direction", "volatility", "momentum", "market_sentiment", "long_term_outlook"]
            for param in required_market_params:
                if param not in market_parameters:
                    return {
                        "status": "error", 
                        "error": f"Missing required market parameter: {param}"
                    }
            
            required_invisible = ["institutional_flow", "liquidity_factor", "news_velocity", "sector_rotation", "risk_appetite"]
            for param in required_invisible:
                if param not in invisible_factors:
                    return {
                        "status": "error",
                        "error": f"Missing required invisible factor: {param}"
                    }
            
            # Validate stock prices
            expected_stocks = [
                "XOM", "CVX", "COP",  # ENERGY
                "NFLX", "DIS", "EA",  # ENTERTAINMENT  
                "JPM", "BAC", "V", "GS", "BRK.B",  # FINANCE
                "JNJ", "UNH", "PFE",  # HEALTH
                "CAT", "GE", "LMT",  # MANUFACTURING
                "WMT", "COST", "HD",  # RETAIL
                "AAPL", "MSFT", "GOOGL", "NVDA",  # TECH
                "BA"  # TRANSPORT
            ]
            
            missing_stocks = []
            for symbol in expected_stocks:
                if symbol not in daily_stock_prices:
                    missing_stocks.append(symbol)
            
            if missing_stocks:
                return {
                    "status": "error",
                    "error": f"Missing stock data for: {', '.join(missing_stocks)}"
                }
            
            # Validate each stock has required fields
            for symbol, stock_data in daily_stock_prices.items():
                required_fields = ["open_price", "range_low", "range_high", "sector_factor"]
                for field in required_fields:
                    if field not in stock_data:
                        return {
                            "status": "error",
                            "error": f"Stock {symbol} missing required field: {field}"
                        }
            
            # Create analysis structure matching AI output format
            analysis = {
                "parameters": market_parameters,
                "invisible_factors": invisible_factors,
                "daily_stock_prices": daily_stock_prices,
                "sector_outlook": sector_outlook,
                "reasoning": reasoning
            }
            
            # Apply parameters to stock market
            self.stock_market.market_params = {
                "trend_direction": max(-1.0, min(1.0, float(market_parameters["trend_direction"]))),
                "volatility": max(0.0, min(1.0, float(market_parameters["volatility"]))),
                "momentum": max(0.0, min(1.0, float(market_parameters["momentum"]))),
                "market_sentiment": max(0.0, min(1.0, float(market_parameters["market_sentiment"]))),
                "long_term_outlook": max(0.0, min(1.0, float(market_parameters["long_term_outlook"])))
            }
            
            # Apply invisible factors
            self.stock_market.invisible_factors = {
                "institutional_flow": max(-1.0, min(1.0, float(invisible_factors["institutional_flow"]))),
                "liquidity_factor": max(0.0, min(1.0, float(invisible_factors["liquidity_factor"]))),
                "news_velocity": max(0.0, min(1.0, float(invisible_factors["news_velocity"]))),
                "sector_rotation": max(-1.0, min(1.0, float(invisible_factors["sector_rotation"]))),
                "risk_appetite": max(0.0, min(1.0, float(invisible_factors["risk_appetite"])))
            }
            
            # Apply daily stock prices
            self.stock_market._apply_ai_stock_prices(daily_stock_prices)
            
            # Save the daily analysis
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            log_file = self.stock_market.data_dir / "analysis_logs" / f"manual_market_init_{timestamp}.txt"
            log_file.parent.mkdir(exist_ok=True)
            
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"[{timestamp}] === MANUAL MARKET INITIALIZATION ===\n")
                f.write("Market Parameters:\n")
                f.write(json.dumps(market_parameters, indent=2))
                f.write("\n\nInvisible Factors:\n")
                f.write(json.dumps(invisible_factors, indent=2))
                f.write("\n\nSector Outlook:\n")
                f.write(json.dumps(sector_outlook, indent=2))
                f.write("\n\nReasoning:\n")
                f.write(json.dumps(reasoning, indent=2))
                f.write(f"\n\n[{timestamp}] === INITIALIZATION COMPLETE ===\n")
            
            # Save to daily_analysis.json
            analysis_file = self.stock_market.data_dir / "daily_analysis.json"
            with open(analysis_file, 'w') as f:
                json.dump([analysis], f, indent=2)
            
            # Save market state
            self.stock_market.save_market_data()
            
            return {
                "status": "success",
                "message": "Stock market initialized successfully",
                "applied_parameters": {
                    "market_params": self.stock_market.market_params,
                    "invisible_factors": self.stock_market.invisible_factors,
                    "stocks_initialized": len(daily_stock_prices),
                    "log_file": str(log_file)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to initialize stock market: {str(e)}"
            }
    
    # ==================== MEMORY & CONTEXT MANAGEMENT ====================
    
    async def add_memory_entry(self, content: str, admin_id: Optional[str] = None) -> Dict[str, Any]:
        """Add memory entry for AI context continuity"""
        
        try:
            # Import the global econ_data instance 
            from economic_utils import econ_data
            
            # Convert admin_id to int if provided
            admin_id_int = int(admin_id) if admin_id else 0
            
            # Use the actual function from EconomicData class
            entry_id = econ_data.add_memory_entry(content, admin_id_int)
            
            return {
                "status": "success",
                "entry_id": entry_id,
                "content_length": len(content),
                "admin_id": admin_id,
                "message": "Memory entry added successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to add memory entry: {str(e)}"
            }
    
    async def remove_memory_entry(self, entry_id: str) -> Dict[str, Any]:
        """Remove memory entry by ID"""
        
        try:
            # Import the global econ_data instance 
            from economic_utils import econ_data
            
            # Convert entry_id to int
            entry_id_int = int(entry_id)
            
            # Use the actual function from EconomicData class
            success = econ_data.remove_memory_entry(entry_id_int)
            
            return {
                "status": "success" if success else "error",
                "entry_id": entry_id,
                "removed": success,
                "message": "Memory entry removed successfully" if success else "Entry not found"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "entry_id": entry_id,
                "error": f"Failed to remove memory entry: {str(e)}"
            }
    
    async def get_memory_context(self) -> Dict[str, Any]:
        """Get formatted memory context for AI analysis"""
        
        try:
            # Import the global econ_data instance 
            from economic_utils import econ_data
            
            # Use the actual function from EconomicData class
            memory_context = econ_data.get_memory_context()
            
            return {
                "status": "success",
                "memory_entries": len(memory_context.split('\n')) if memory_context else 0,
                "context_length": len(memory_context) if memory_context else 0,
                "memory_context": memory_context
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get memory context: {str(e)}"
            }
    
    # ==================== ADVANCED ADMINISTRATIVE TOOLS ====================
    
    async def get_economic_status(self) -> Dict[str, Any]:
        """Get comprehensive economic system status"""
        
        try:
            # Use the actual function from economic_utils
            status = economic_utils.get_economic_status()
            
            return {
                "status": "success",
                "system_status": status,
                "last_updated": status.get("last_updated", "Unknown"),
                "data_health": status.get("data_health", "Unknown")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get economic status: {str(e)}"
            }
    
    async def log_admin_action(
        self,
        admin_id: str,
        action: str,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log administrative action for audit trail"""
        
        try:
            # Use the actual function from economic_utils
            admin_id_int = int(admin_id)
            details_dict = {"details": details} if details else {}
            
            economic_utils.log_admin_action(admin_id_int, action, details_dict)
            
            return {
                "status": "success",
                "admin_id": admin_id,
                "action": action,
                "details": details,
                "message": "Admin action logged successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "admin_id": admin_id,
                "action": action,
                "error": f"Failed to log admin action: {str(e)}"
            }
    
    async def set_advanced_economic_parameter(
        self,
        parameter: str,
        value: float,
        admin_id: str,
        admin_token: str
    ) -> Dict[str, Any]:
        """Set economic parameter with enhanced admin controls"""
        
        try:
            # TODO: Validate admin_token (not implemented yet)
            
            # Use the actual function from economic_utils
            success = economic_utils.set_economic_parameter(parameter, value)
            
            if success:
                # Log the action
                await self.log_admin_action(admin_id, f"set_parameter_{parameter}", f"Value: {value}")
                
                return {
                    "status": "success",
                    "parameter": parameter,
                    "new_value": value,
                    "admin_id": admin_id,
                    "logged": True,
                    "message": f"Parameter '{parameter}' updated successfully"
                }
            else:
                return {
                    "status": "error",
                    "parameter": parameter,
                    "value": value,
                    "error": "Failed to set parameter - invalid parameter name or value"
                }
            
        except Exception as e:
            return {
                "status": "error",
                "parameter": parameter,
                "value": value,
                "admin_id": admin_id,
                "error": f"Failed to set advanced economic parameter: {str(e)}"
            }
    
    # ==================== ECONOMIC REPORT SUBMISSION ====================
    
    async def submit_economic_report(
        self,
        report_data: Dict[str, Any],
        analysis_type: str = "comprehensive",
        submit_to_discord: bool = True,
        target_channel: str = "official-rp-news"
    ) -> Dict[str, Any]:
        """Submit completed economic analysis report"""
        
        try:
            # Validate report data
            required_fields = ["gdp", "inflation", "unemployment", "sentiment"]
            missing_fields = [field for field in required_fields if field not in report_data]
            
            if missing_fields:
                return {
                    "status": "error",
                    "error": f"Missing required fields: {', '.join(missing_fields)}",
                    "required_fields": required_fields
                }
            
            # Format report for submission
            formatted_report = {
                "analysis_type": analysis_type,
                "submission_timestamp": time.time(),
                "report_data": report_data,
                "summary": {
                    "gdp_growth": report_data["gdp"].get("quarterly_growth_percent", "N/A"),
                    "inflation_rate": report_data["inflation"].get("yoy_percent", "N/A"),
                    "unemployment_rate": report_data["unemployment"].get("rate_percent", "N/A"),
                    "market_confidence": report_data["sentiment"].get("confidence_percent", "N/A")
                },
                "target_channel": target_channel,
                "discord_submission": submit_to_discord
            }
            
            # Submit the report using standalone economy
            success = standalone_economy.submit_economic_report(report_data)
            
            if success:
                report_id = f"econ_report_{int(time.time())}"
                return {
                    "status": "success",
                    "report_id": report_id,
                    "analysis_type": analysis_type,
                    "target_channel": target_channel,
                    "discord_submitted": submit_to_discord,
                    "summary": formatted_report["summary"],
                    "message": "Economic report submitted successfully and saved to data files",
                    "note": "Report has been written to individual economic data files"
                }
            else:
                return {
                    "status": "error",
                    "error": "Failed to save report to data files",
                    "analysis_type": analysis_type
                }
            
        except Exception as e:
            return {
                "status": "error",
                "analysis_type": analysis_type,
                "error": f"Failed to submit economic report: {str(e)}"
            }