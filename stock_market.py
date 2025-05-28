"""
Advanced Stock Market System for Virtual Congress Discord Bot
Implements realistic stock trading with AI-driven daily analysis and Perlin noise price movements
"""

import asyncio
import json
import os
import random
import math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import io
import base64
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import discord
from discord.ext import commands, tasks
import google.generativeai as genai
from config import GEMINI_API_KEY, BOT_HELPER_CHANNEL
from economic_utils import ALL_ALLOWED_CHANNELS, ALLOWED_CHANNELS

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

class StockMarket:
    """Advanced Stock Market System with AI-driven analysis and realistic price movements"""
    
    def __init__(self):
        self.data_dir = Path("stock_data")
        self.data_dir.mkdir(exist_ok=True)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.client = None
        self.stocks_channel_id = BOT_HELPER_CHANNEL  # Default channel
        
        # Initialize stock market structure - Real Economic Sectors
        self.categories = {
            "ENERGY": {
                "name": "Energy Sector",
                "description": "Oil, gas, and energy companies",
                "market_direction": "normal",  # up/down/normal
                "stocks": [
                    {"symbol": "XOM", "name": "ExxonMobil", "price": 129.05, "sector": "oil_gas"},
                    {"symbol": "CVX", "name": "Chevron Corporation", "price": 185.75, "sector": "oil_gas"},
                    {"symbol": "COP", "name": "ConocoPhillips", "price": 153.11, "sector": "oil_gas"}
                ]
            },
            "ENTERTAINMENT": {
                "name": "Entertainment & Media Sector",
                "description": "Entertainment, media, and streaming companies",
                "market_direction": "normal",
                "stocks": [
                    {"symbol": "NFLX", "name": "Netflix Inc.", "price": 564.99, "sector": "streaming"},
                    {"symbol": "DIS", "name": "Walt Disney Company", "price": 91.09, "sector": "entertainment"},
                    {"symbol": "EA", "name": "Electronic Arts", "price": 290.79, "sector": "gaming"}
                ]
            },
            "FINANCE": {
                "name": "Financial Services Sector", 
                "description": "Banks, investment firms, and financial services",
                "market_direction": "normal",
                "stocks": [
                    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "price": 103.97, "sector": "banking"},
                    {"symbol": "BAC", "name": "Bank of America", "price": 36.03, "sector": "banking"},
                    {"symbol": "V", "name": "Visa Inc.", "price": 152.31, "sector": "payments"},
                    {"symbol": "GS", "name": "Goldman Sachs", "price": 266.66, "sector": "investment"}
                ]
            },
            "HEALTH": {
                "name": "Healthcare Sector",
                "description": "Healthcare, pharmaceuticals, and medical devices",
                "market_direction": "normal",
                "stocks": [
                    {"symbol": "JNJ", "name": "Johnson & Johnson", "price": 105.02, "sector": "pharma"},
                    {"symbol": "UNH", "name": "UnitedHealth Group", "price": 216.74, "sector": "insurance"},
                    {"symbol": "PFE", "name": "Pfizer Inc.", "price": 43.35, "sector": "pharma"}
                ]
            },
            "MANUFACTURING": {
                "name": "Manufacturing Sector",
                "description": "Industrial manufacturing and machinery",
                "market_direction": "normal",
                "stocks": [
                    {"symbol": "CAT", "name": "Caterpillar Inc.", "price": 136.07, "sector": "machinery"},
                    {"symbol": "GE", "name": "General Electric", "price": 166.86, "sector": "industrial"},
                    {"symbol": "LMT", "name": "Lockheed Martin", "price": 376.35, "sector": "defense"}
                ]
            },
            "RETAIL": {
                "name": "Retail Sector",
                "description": "Consumer retail and wholesale companies",
                "market_direction": "normal",
                "stocks": [
                    {"symbol": "WMT", "name": "Walmart Inc.", "price": 68.88, "sector": "discount_retail"},
                    {"symbol": "COST", "name": "Costco Wholesale", "price": 331.80, "sector": "warehouse"},
                    {"symbol": "HD", "name": "Home Depot", "price": 139.25, "sector": "home_improvement"}
                ]
            },
            "TECH": {
                "name": "Technology Sector",
                "description": "Technology hardware, software, and services",
                "market_direction": "normal",
                "stocks": [
                    {"symbol": "AAPL", "name": "Apple Inc.", "price": 193.54, "sector": "consumer_tech"},
                    {"symbol": "MSFT", "name": "Microsoft Corporation", "price": 468.95, "sector": "software"},
                    {"symbol": "GOOGL", "name": "Alphabet Inc.", "price": 2782.18, "sector": "internet"},
                    {"symbol": "NVDA", "name": "NVIDIA Corporation", "price": 680.83, "sector": "semiconductors"}
                ]
            },
            "TRANSPORT": {
                "name": "Transportation Sector",
                "description": "Airlines, shipping, and transportation",
                "market_direction": "normal",
                "stocks": [
                    {"symbol": "BA", "name": "Boeing Company", "price": 262.71, "sector": "aerospace"}
                ]
            }
        }
        
        # Market parameters - calculated from economic data
        self.market_params = self._calculate_market_params_from_economic_data()
        
        # Trading state (24/7 operation)
        self.is_trading_day = True  # Always trading
        self.current_trading_day = None
        self.precomputed_prices = {}
        self.hourly_updates_task = None
        
        # Try to load existing market data after initialization
        self.load_market_data()
        
        print("📈 Stock Market System initialized")
        print(f"💼 {sum(len(cat['stocks']) for cat in self.categories.values())} individual stocks across {len(self.categories)} sectors")
        print(f"📊 Market parameters calculated from economic data: Trend {self.market_params['trend_direction']:+.2f}, Volatility {self.market_params['volatility']:.2f}")
    
    def _calculate_market_params_from_economic_data(self) -> Dict[str, float]:
        """Calculate market parameters based on current economic data"""
        try:
            # Try to read economic data files
            economic_data_dir = Path("economic_data")
            
            # Start with neutral baseline - will be adjusted by actual data
            inflation_rate = 2.0  # Fed target as baseline
            gdp_change = 2.0  # Moderate growth as baseline
            market_confidence = 50.0  # Neutral confidence as baseline
            inflation_anxiety = 50.0  # Neutral anxiety as baseline
            unemployment_rate = 4.0  # Natural rate as baseline
            
            # Read actual economic data
            inflation_file = economic_data_dir / "inflation.json"
            if inflation_file.exists():
                try:
                    with open(inflation_file, 'r') as f:
                        inflation_data = json.load(f)
                    if inflation_data:
                        latest_inflation = inflation_data[0]['data']
                        inflation_rate = latest_inflation.get('rate', inflation_rate)
                        print(f"📊 Using inflation rate: {inflation_rate}%")
                except Exception as e:
                    print(f"⚠️ Error reading inflation data: {e}")
            
            sentiment_file = economic_data_dir / "sentiment.json"
            if sentiment_file.exists():
                try:
                    with open(sentiment_file, 'r') as f:
                        sentiment_data = json.load(f)
                    if sentiment_data:
                        latest_sentiment = sentiment_data[0]['data']
                        market_confidence = latest_sentiment.get('market_confidence', market_confidence)
                        inflation_anxiety = latest_sentiment.get('inflation_anxiety', inflation_anxiety)
                        print(f"📊 Using market confidence: {market_confidence}%, anxiety: {inflation_anxiety}%")
                except Exception as e:
                    print(f"⚠️ Error reading sentiment data: {e}")
            
            gdp_file = economic_data_dir / "gdp.json"
            if gdp_file.exists():
                try:
                    with open(gdp_file, 'r') as f:
                        gdp_data = json.load(f)
                    if gdp_data:
                        latest_gdp = gdp_data[0]['data']
                        gdp_change = latest_gdp.get('change_percent', gdp_change)
                        print(f"📊 Using GDP change: {gdp_change}%")
                except Exception as e:
                    print(f"⚠️ Error reading GDP data: {e}")
            
            unemployment_file = economic_data_dir / "unemployment.json"
            if unemployment_file.exists():
                try:
                    with open(unemployment_file, 'r') as f:
                        unemployment_data = json.load(f)
                    if unemployment_data:
                        latest_unemployment = unemployment_data[0]['data']
                        unemployment_rate = latest_unemployment.get('rate', unemployment_rate)
                        print(f"📊 Using unemployment rate: {unemployment_rate}%")
                except Exception as e:
                    print(f"⚠️ Error reading unemployment data: {e}")
            
            # Calculate parameters proportionally from actual data
            
            # TREND DIRECTION: Based on GDP growth
            # -5% GDP = -1.0 trend, +5% GDP = +1.0 trend, 0% GDP = 0.0 trend
            trend_direction = max(-1.0, min(1.0, gdp_change / 5.0))
            
            # VOLATILITY: Based on inflation deviation from target (2%) and anxiety
            # Higher inflation deviation and anxiety = higher volatility
            inflation_deviation = abs(inflation_rate - 2.0) / 10.0  # Normalize to 0-1 scale
            anxiety_factor = inflation_anxiety / 100.0  # Convert to 0-1
            volatility = max(0.1, min(1.0, 0.2 + inflation_deviation + (anxiety_factor * 0.3)))
            
            # MOMENTUM: Based on GDP growth and unemployment trend
            # Strong GDP growth and low unemployment = high momentum
            gdp_momentum = max(0.0, gdp_change / 5.0)  # Convert GDP to 0-1 scale
            unemployment_momentum = max(0.0, (8.0 - unemployment_rate) / 8.0)  # Lower unemployment = higher momentum
            momentum = max(0.1, min(1.0, (gdp_momentum + unemployment_momentum) / 2.0))
            
            # MARKET SENTIMENT: Directly from market confidence data
            market_sentiment = max(0.1, min(1.0, market_confidence / 100.0))
            
            # LONG TERM OUTLOOK: Based on structural economic indicators
            # Considers inflation stability, GDP trend, and employment
            inflation_stability = max(0.0, 1.0 - (abs(inflation_rate - 2.0) / 10.0))  # Closer to 2% = better
            gdp_stability = max(0.0, min(1.0, (gdp_change + 2.0) / 6.0))  # -2% to +4% mapped to 0-1
            employment_stability = max(0.0, min(1.0, (8.0 - unemployment_rate) / 6.0))  # Lower unemployment = better
            long_term_outlook = max(0.1, min(1.0, (inflation_stability + gdp_stability + employment_stability) / 3.0))
            
            params = {
                "trend_direction": trend_direction,
                "volatility": volatility,
                "momentum": momentum,
                "market_sentiment": market_sentiment,
                "long_term_outlook": long_term_outlook
            }
            
            print(f"📈 Calculated market parameters from economic data:")
            print(f"   Trend: {trend_direction:+.3f}, Volatility: {volatility:.3f}, Momentum: {momentum:.3f}")
            print(f"   Sentiment: {market_sentiment:.3f}, Outlook: {long_term_outlook:.3f}")
            
            return params
            
        except Exception as e:
            print(f"❌ Critical error in economic calculation: {e}")
            raise Exception(f"Cannot calculate market parameters without economic data: {e}")
        
    def save_market_data(self) -> None:
        """Save current market state to JSON"""
        market_data = {
            "categories": self.categories,
            "market_params": self.market_params,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "trading_state": {
                "is_trading_day": self.is_trading_day,
                "current_trading_day": self.current_trading_day,
                "stocks_channel_id": self.stocks_channel_id
            },
            "precomputed_prices": self.precomputed_prices
        }
        
        with open(self.data_dir / "market_data.json", 'w') as f:
            json.dump(market_data, f, indent=2)
    
    def load_market_data(self) -> bool:
        """Load market state from JSON"""
        market_file = self.data_dir / "market_data.json"
        if not market_file.exists():
            return False
            
        try:
            with open(market_file, 'r') as f:
                data = json.load(f)
            
            if "categories" in data:
                self.categories = data["categories"]
            if "market_params" in data:
                self.market_params = data["market_params"]
            if "trading_state" in data:
                state = data["trading_state"]
                self.is_trading_day = state.get("is_trading_day", False)
                self.current_trading_day = state.get("current_trading_day")
                self.stocks_channel_id = state.get("stocks_channel_id", BOT_HELPER_CHANNEL)
            if "precomputed_prices" in data:
                self.precomputed_prices = data["precomputed_prices"]
            
            print("📊 Market data loaded successfully")
            if self.precomputed_prices:
                print(f"✅ Loaded {len(self.precomputed_prices)} precomputed price series")
            return True
            
        except Exception as e:
            print(f"❌ Error loading market data: {e}")
            return False
    
    def save_historical_data(self, timestamp: str, data: Dict[str, Any]) -> None:
        """Save historical price data"""
        history_file = self.data_dir / "stock_history.json"
        history = []
        
        if history_file.exists():
            with open(history_file, 'r') as f:
                history = json.load(f)
        
        history.append({
            "timestamp": timestamp,
            "data": data
        })
        
        # Keep last 10000 entries (roughly 1+ years of hourly data)
        history = history[-10000:]
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def get_historical_data(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get historical stock data"""
        history_file = self.data_dir / "stock_history.json"
        if not history_file.exists():
            return []
        
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            # Filter by date
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
            filtered = []
            
            for entry in history:
                entry_time = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
                if entry_time >= cutoff:
                    filtered.append(entry)
            
            return filtered
            
        except Exception as e:
            print(f"❌ Error loading historical data: {e}")
            return []
    
    def calculate_category_prices(self) -> Dict[str, float]:
        """Calculate ETF-like category prices based on individual stock prices"""
        category_prices = {}
        
        for cat_name, cat_data in self.categories.items():
            stocks = cat_data["stocks"]
            if stocks:
                # Simple equal-weighted average for ETF price
                total_price = sum(stock["price"] for stock in stocks)
                category_prices[cat_name] = total_price / len(stocks)
            else:
                category_prices[cat_name] = 0.0
        
        return category_prices
    
    def get_all_stocks_flat(self) -> List[Dict[str, Any]]:
        """Get all individual stocks in a flat list"""
        all_stocks = []
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                stock_copy = stock.copy()
                stock_copy["category"] = cat_name
                all_stocks.append(stock_copy)
        return all_stocks
    
    async def trigger_dynamic_update(self, reason: str = "Market update", send_discord_notification: bool = False, recalculate_baselines: bool = False) -> Dict[str, Any]:
        """Trigger comprehensive dynamic update of all stock and ETF prices"""
        print(f"🔄 Triggering dynamic update: {reason}")
        
        price_changes = {}
        
        # Optionally recalculate baseline prices from economic parameters
        if recalculate_baselines:
            print("🔄 Recalculating baseline prices from economic parameters...")
            price_changes = self.recalculate_all_baseline_prices()
        
        # Recalculate all category ETF prices based on current stock prices
        category_prices = self.calculate_category_prices()
        
        # Save updated market data
        self.save_market_data()
        
        # Create historical snapshot
        timestamp = datetime.now(timezone.utc).isoformat()
        historical_data = {
            "individual_stocks": {symbol: stock["price"] for cat in self.categories.values() 
                                for stock in cat["stocks"] for symbol in [stock["symbol"]]},
            "category_prices": category_prices,
            "market_params": self.market_params,
            "update_reason": reason,
            "dynamic_update": True
        }
        
        self.save_historical_data(timestamp, historical_data)
        
        # Calculate summary statistics
        total_stocks = sum(len(cat['stocks']) for cat in self.categories.values())
        update_summary = {
            "reason": reason,
            "timestamp": timestamp,
            "stocks_updated": total_stocks,
            "etf_prices": category_prices,
            "market_params": self.market_params.copy(),
            "baselines_recalculated": recalculate_baselines,
            "price_changes": price_changes if recalculate_baselines else {},
            "notification_sent": False
        }
        
        # Send Discord notification if requested
        if send_discord_notification and self.client:
            try:
                channel = self.client.get_channel(self.stocks_channel_id)
                if channel:
                    embed = discord.Embed(
                        title="🔄 Dynamic Market Update",
                        description=f"**Reason**: {reason}",
                        color=0x00aaff,
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    # Show ETF prices
                    etf_text = ""
                    for cat_name, price in category_prices.items():
                        emoji = "⛽" if cat_name == "ENERGY" else "🎬" if cat_name == "ENTERTAINMENT" else "🏦" if cat_name == "FINANCE" else "🏥" if cat_name == "HEALTH" else "🏭" if cat_name == "MANUFACTURING" else "🛒" if cat_name == "RETAIL" else "💻" if cat_name == "TECH" else "✈️"
                        etf_text += f"{emoji} **{cat_name}**: ${price:.2f}\n"
                    
                    embed.add_field(name="📊 Updated Sector ETFs", value=etf_text.strip(), inline=True)
                    
                    # Show market parameters
                    params = self.market_params
                    param_text = f"""
**Trend**: {params['trend_direction']:+.2f} {'📈' if params['trend_direction'] > 0 else '📉' if params['trend_direction'] < 0 else '➡️'}
**Volatility**: {params['volatility']:.2f} {'🌪️' if params['volatility'] > 0.7 else '🌊'}
**Sentiment**: {params['market_sentiment']:.2f} {'😄' if params['market_sentiment'] > 0.7 else '😐' if params['market_sentiment'] > 0.4 else '😟'}
"""
                    embed.add_field(name="📊 Market Parameters", value=param_text.strip(), inline=True)
                    
                    footer_text = f"{total_stocks} stocks updated • All ETF prices recalculated"
                    if recalculate_baselines:
                        footer_text += " • Baselines recalculated from economic data"
                    embed.set_footer(text=footer_text)
                    
                    await channel.send(embed=embed)
                    update_summary["notification_sent"] = True
                    print(f"✅ Dynamic update notification sent to Discord")
                
            except Exception as e:
                print(f"⚠️ Failed to send Discord notification: {e}")
        
        print(f"✅ Dynamic update complete: {total_stocks} stocks, {len(category_prices)} ETFs updated")
        return update_summary
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Get comprehensive market summary with all current data"""
        category_prices = self.calculate_category_prices()
        all_stocks = self.get_all_stocks_flat()
        
        # Calculate market-wide statistics
        all_prices = [stock["price"] for stock in all_stocks]
        avg_price = sum(all_prices) / len(all_prices) if all_prices else 0
        
        # Calculate total market cap (simple approximation)
        total_market_cap = sum(all_prices) * 1000  # Assuming 1000 shares per stock for simplification
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_stocks": len(all_stocks),
            "total_categories": len(self.categories),
            "average_stock_price": avg_price,
            "total_market_cap": total_market_cap,
            "category_etf_prices": category_prices,
            "market_parameters": self.market_params.copy(),
            "trading_status": {
                "is_trading_day": self.is_trading_day,
                "current_trading_day": self.current_trading_day,
                "has_precomputed_prices": bool(self.precomputed_prices)
            },
            "individual_stocks": {
                stock["symbol"]: {
                    "name": stock["name"],
                    "price": stock["price"],
                    "category": stock["category"],
                    "sector": stock["sector"]
                }
                for stock in all_stocks
            }
        }
    
    @staticmethod
    def perlin_noise(x: float, seed: int = 42) -> float:
        """Generate Perlin-like noise for realistic price movements"""
        random.seed(seed)
        # Simple implementation of Perlin-like noise
        x = x * 0.1  # Scale down for smoother noise
        
        # Multiple octaves for more realistic noise
        noise = 0.0
        amplitude = 1.0
        frequency = 1.0
        
        for _ in range(4):  # 4 octaves
            noise += amplitude * math.sin(frequency * x + random.random() * math.pi * 2)
            amplitude *= 0.5
            frequency *= 2.0
        
        return noise / 2.0  # Normalize to roughly -1 to 1
    
    def calculate_dynamic_baseline_price(self, stock: Dict[str, Any], original_price: float) -> float:
        """Calculate dynamic baseline price based on current economic parameters"""
        try:
            # Base price adjustment factors based on economic parameters
            
            # Trend direction affects baseline: bullish trend = higher baseline, bearish = lower
            trend_factor = 1.0 + (self.market_params["trend_direction"] * 0.1)  # ±10% max
            
            # Market sentiment affects valuation: high confidence = premium, low = discount
            sentiment_factor = 0.8 + (self.market_params["market_sentiment"] * 0.4)  # 0.8x to 1.2x
            
            # Long-term outlook affects baseline: good outlook = higher valuations
            outlook_factor = 0.9 + (self.market_params["long_term_outlook"] * 0.2)  # 0.9x to 1.1x
            
            # Volatility doesn't affect baseline - only affects movement amplitude
            # Momentum doesn't affect baseline - only affects movement strength
            
            # Calculate adjusted baseline
            adjusted_price = original_price * trend_factor * sentiment_factor * outlook_factor
            
            # Ensure price doesn't deviate too extremely from original
            adjusted_price = max(adjusted_price, original_price * 0.6)  # Don't drop below 60%
            adjusted_price = min(adjusted_price, original_price * 1.4)  # Don't rise above 140%
            
            return adjusted_price
            
        except Exception as e:
            print(f"⚠️ Error calculating dynamic baseline for {stock.get('symbol', 'unknown')}: {e}")
            return original_price
    
    def recalculate_all_baseline_prices(self) -> Dict[str, float]:
        """Recalculate baseline prices for all stocks based on current economic parameters"""
        print("🔄 Recalculating baseline prices from economic parameters...")
        
        price_changes = {}
        
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                symbol = stock["symbol"]
                original_price = stock["price"]
                
                # Calculate new baseline from economic parameters
                new_baseline = self.calculate_dynamic_baseline_price(stock, original_price)
                
                # Update the stock price
                stock["price"] = new_baseline
                
                price_changes[symbol] = {
                    "old_price": original_price,
                    "new_price": new_baseline,
                    "change": new_baseline - original_price,
                    "change_pct": ((new_baseline - original_price) / original_price) * 100
                }
        
        print(f"✅ Recalculated baseline prices for {len(price_changes)} stocks")
        return price_changes
    
    def generate_hourly_prices(self, trading_day: str) -> Dict[str, List[float]]:
        """Generate realistic hourly prices using Perlin noise and market parameters"""
        print(f"📊 Generating hourly prices for {trading_day}")
        
        # 24/7 trading: 24 hours = 24 price points (one per hour)
        hours = 24  # 00:00, 01:00, 02:00, ..., 23:00
        
        hourly_prices = {}
        
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                symbol = stock["symbol"]
                current_price = stock["price"]  # Use current (potentially recalculated) baseline
                
                prices = [current_price]  # Start with current baseline price
                
                # Use symbol hash as seed for consistent but different noise per stock
                noise_seed = hash(symbol + trading_day) % 10000
                
                for hour in range(1, hours):
                    # Generate Perlin noise for this hour
                    noise_value = self.perlin_noise(hour, noise_seed)
                    
                    # Apply market parameters to modify the noise
                    trend_component = self.market_params["trend_direction"] * 0.02 * hour  # Gradual trend
                    volatility_multiplier = 0.005 + (self.market_params["volatility"] * 0.015)  # 0.5% to 2% base volatility
                    momentum_factor = 1.0 + (self.market_params["momentum"] * 0.5)  # Amplify movements
                    sentiment_bias = (self.market_params["market_sentiment"] - 0.5) * 0.01  # Slight bias
                    
                    # Calculate price change
                    base_change = noise_value * volatility_multiplier * momentum_factor
                    total_change = base_change + trend_component + sentiment_bias
                    
                    # Apply change to previous price
                    new_price = prices[-1] * (1 + total_change)
                    
                    # Ensure price doesn't go negative or too extreme
                    new_price = max(new_price, current_price * 0.5)  # Don't drop below 50% of opening
                    new_price = min(new_price, current_price * 1.5)  # Don't rise above 150% of opening
                    
                    prices.append(new_price)
                
                hourly_prices[symbol] = prices
        
        print(f"✅ Generated hourly price movements for {len(hourly_prices)} stocks")
        return hourly_prices
    
    async def get_daily_market_analysis(self) -> Dict[str, Any]:
        """Use AI to analyze recent channel activity and set market parameters"""
        print("🧠 Running AI market analysis...")
        
        if not self.client:
            print("❌ Discord client not available for market analysis")
            return self.get_fallback_analysis()
        
        try:
            # Collect recent messages from all allowed channels (last 500 messages max)
            all_messages = []
            cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)  # Last 24 hours
            
            print(f"📊 Collecting messages from {len(ALL_ALLOWED_CHANNELS)} authorized channels...")
            
            for guild in self.client.guilds:
                for channel in guild.text_channels:
                    if channel.name.lower() not in ALL_ALLOWED_CHANNELS:
                        continue
                    
                    if not channel.permissions_for(guild.me).read_message_history:
                        continue
                    
                    try:
                        channel_messages = []
                        async for message in channel.history(limit=50, after=cutoff_date):  # 50 per channel max
                            if message.author.bot:
                                continue
                            
                            channel_messages.append({
                                "content": message.content[:300],  # Limit message length
                                "channel": channel.name,
                                "timestamp": message.created_at.isoformat(),
                                "author_roles": [role.name for role in getattr(message.author, 'roles', [])]
                            })
                        
                        all_messages.extend(channel_messages)
                        
                        if len(all_messages) >= 500:  # Cap at 500 total messages
                            break
                            
                    except Exception as e:
                        print(f"⚠️ Error collecting from {channel.name}: {e}")
                        continue
                
                if len(all_messages) >= 500:
                    break
            
            # Limit to 500 most recent messages
            all_messages = sorted(all_messages, key=lambda x: x["timestamp"], reverse=True)[:500]
            
            print(f"📝 Collected {len(all_messages)} messages for analysis")
            
            # Get previous day's data for context
            previous_data = self.get_previous_trading_day_data()
            
            # Construct AI prompt
            analysis_prompt = self.build_market_analysis_prompt(all_messages, previous_data)
            
            # Generate AI analysis
            response = await self.model.generate_content_async(
                analysis_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=2000
                )
            )
            
            # Parse AI response
            return self.parse_market_analysis(response.text)
            
        except Exception as e:
            print(f"❌ AI market analysis failed: {e}")
            return self.get_fallback_analysis()
    
    def build_market_analysis_prompt(self, messages: List[Dict], previous_data: Optional[Dict]) -> str:
        """Build comprehensive prompt for AI market analysis"""
        
        # Organize messages by channel category
        categorized_messages = {}
        for msg in messages:
            channel_name = msg["channel"]
            for cat_name, channels in ALLOWED_CHANNELS.items():
                if channel_name in channels:
                    if cat_name not in categorized_messages:
                        categorized_messages[cat_name] = []
                    categorized_messages[cat_name].append(msg)
                    break
        
        prompt = f"""You are an expert financial analyst for a Virtual Congress stock market simulation. 
Analyze the provided Discord server activity from the last 24 hours to determine market parameters for today's trading.

**IMPORTANT**: You must output your analysis in the exact JSON format specified at the end.

**Current Stock Market Structure**:
{json.dumps(self.categories, indent=2)}

**Market Parameters to Set** (each 0.0 to 1.0):
- trend_direction: -1.0 (bearish) to 1.0 (bullish) - overall market direction today
- volatility: 0.0 (stable) to 1.0 (very volatile) - how much prices will fluctuate
- momentum: 0.0 (weak movements) to 1.0 (strong movements) - strength of price changes
- market_sentiment: 0.0 (fearful/pessimistic) to 1.0 (confident/optimistic) - investor confidence
- long_term_outlook: 0.0 (pessimistic) to 1.0 (optimistic) - make only TINY changes to this

**Discord Activity Analysis**:
Total messages analyzed: {len(messages)}

**Activity by Category**:
"""
        
        for cat_name, cat_messages in categorized_messages.items():
            prompt += f"\n**{cat_name}** ({len(cat_messages)} messages):\n"
            # Include sample messages
            for msg in cat_messages[:3]:  # Show first 3 messages per category
                prompt += f"- [{msg['channel']}] {msg['content'][:100]}...\n"
            if len(cat_messages) > 3:
                prompt += f"... and {len(cat_messages) - 3} more messages\n"
        
        # Add previous day context
        if previous_data:
            prompt += f"\n**Previous Trading Day Context**:\n{json.dumps(previous_data, indent=2)}\n"
        else:
            prompt += "\n**Previous Trading Day Context**: No previous data - this is the initial market setup.\n"
        
        # Add current stock data and recent performance
        current_stocks = {}
        for cat_name, cat_data in self.categories.items():
            current_stocks[cat_name] = {
                "stocks": [{"symbol": s["symbol"], "name": s["name"], "price": s["price"]} for s in cat_data["stocks"]],
                "etf_price": sum(s["price"] for s in cat_data["stocks"]) / len(cat_data["stocks"]) if cat_data["stocks"] else 0
            }
        
        prompt += f"\n**Current Stock Market State**:\n{json.dumps(current_stocks, indent=2)}\n"
        
        # Add recent stock performance if available
        historical_data = self.get_historical_data(days_back=7)
        if historical_data:
            prompt += f"\n**Recent Stock Performance**: {len(historical_data)} data points from last 7 days available for analysis.\n"
            
            # Include sample of recent performance
            if len(historical_data) > 2:
                recent_sample = {
                    "oldest_data": historical_data[0]["data"]["individual_stocks"] if "individual_stocks" in historical_data[0]["data"] else {},
                    "latest_data": historical_data[-1]["data"]["individual_stocks"] if "individual_stocks" in historical_data[-1]["data"] else {}
                }
                prompt += f"Sample performance data: {json.dumps(recent_sample, indent=2)}\n"
        
        prompt += """
**Your Analysis Task**:
1. Analyze government activity, policy discussions, news sentiment, and public reaction
2. Consider how each category's activity might affect related stocks
3. Set realistic market parameters based on observed activity levels and sentiment
4. Provide clear reasoning for your parameter choices
5. For long_term_outlook, make only small adjustments (±0.05 max) unless major events occurred

**Required JSON Output Format**:
{
  "reasoning": {
    "market_overview": "Overall assessment of market conditions based on server activity",
    "trend_analysis": "Why you chose the trend_direction value",
    "volatility_analysis": "Why you chose the volatility level", 
    "momentum_analysis": "Why you chose the momentum level",
    "sentiment_analysis": "Why you chose the market_sentiment level",
    "outlook_analysis": "Why you adjusted (or didn't adjust) long_term_outlook"
  },
  "parameters": {
    "trend_direction": [calculated based on economic data and Discord activity],
    "volatility": [calculated based on economic data and Discord activity],
    "momentum": [calculated based on economic data and Discord activity],
    "market_sentiment": [calculated based on economic data and Discord activity],
    "long_term_outlook": [calculated based on economic data and Discord activity]
  },
  "stock_outlook": {
    "NEWS": "Brief outlook for news/media sector stocks",
    "CONGRESS": "Brief outlook for legislative sector stocks", 
    "EXECUTIVE": "Brief outlook for executive sector stocks",
    "STATES": "Brief outlook for state government sector stocks",
    "COURTS": "Brief outlook for judicial sector stocks",
    "PUBLIC_SQUARE": "Brief outlook for public engagement sector stocks"
  }
}

Provide your analysis now:"""
        
        return prompt
    
    def parse_market_analysis(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response and extract market parameters"""
        import re
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                
                # Validate and clamp parameters
                if "parameters" in analysis:
                    params = analysis["parameters"]
                    
                    # Clamp all values to valid ranges
                    params["trend_direction"] = max(-1.0, min(1.0, params.get("trend_direction", 0.0)))
                    params["volatility"] = max(0.0, min(1.0, params.get("volatility", 0.3)))
                    params["momentum"] = max(0.0, min(1.0, params.get("momentum", 0.5)))
                    params["market_sentiment"] = max(0.0, min(1.0, params.get("market_sentiment", 0.6)))
                    
                    # Long-term outlook changes slowly
                    current_outlook = self.market_params.get("long_term_outlook", 0.55)
                    new_outlook = params.get("long_term_outlook", current_outlook)
                    max_change = 0.05
                    clamped_outlook = max(current_outlook - max_change, 
                                        min(current_outlook + max_change, new_outlook))
                    params["long_term_outlook"] = max(0.0, min(1.0, clamped_outlook))
                    
                    self.market_params = params
                
                print("✅ AI market analysis parsed successfully")
                return analysis
            else:
                raise ValueError("No valid JSON found in AI response")
                
        except Exception as e:
            print(f"❌ Error parsing AI analysis: {e}")
            return self.get_fallback_analysis()
    
    def get_fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analysis when AI fails - uses economic data"""
        print("🔄 Using fallback market analysis with economic data")
        
        try:
            # Try to calculate parameters from economic data
            self.market_params = self._calculate_market_params_from_economic_data()
            print("✅ Fallback using economic data calculation")
            
            return {
                "reasoning": {
                    "market_overview": "Fallback analysis using economic data calculation",
                    "trend_analysis": "Trend based on GDP growth and economic indicators",
                    "volatility_analysis": "Volatility based on inflation and market sentiment data",
                    "momentum_analysis": "Momentum based on current economic environment",
                    "sentiment_analysis": "Sentiment derived from market confidence data",
                    "outlook_analysis": "Long-term outlook based on economic fundamentals"
                },
                "parameters": self.market_params.copy(),
                "stock_outlook": {cat: "Outlook based on economic fundamentals" for cat in self.categories.keys()}
            }
            
        except Exception as e:
            print(f"⚠️ Economic data fallback failed: {e}")
            print("🔄 Using minimal adjustment fallback")
            
            # Last resort: small adjustments to current parameters
            for param in ["trend_direction", "volatility", "momentum", "market_sentiment"]:
                current = self.market_params[param]
                change = random.uniform(-0.05, 0.05)  # Smaller changes
                
                if param == "trend_direction":
                    self.market_params[param] = max(-1.0, min(1.0, current + change))
                else:
                    self.market_params[param] = max(0.0, min(1.0, current + change))
            
            # Long-term outlook changes very slowly
            outlook_change = random.uniform(-0.01, 0.01)  # Even smaller changes
            current_outlook = self.market_params["long_term_outlook"]
            self.market_params["long_term_outlook"] = max(0.0, min(1.0, current_outlook + outlook_change))
            
            return {
                "reasoning": {
                    "market_overview": "Minimal adjustment fallback - economic data unavailable",
                    "trend_analysis": "Small adjustment to trend direction",
                    "volatility_analysis": "Minor volatility adjustment",
                    "momentum_analysis": "Slight momentum adjustment",
                    "sentiment_analysis": "Minor sentiment adjustment",
                    "outlook_analysis": "Long-term outlook minimally adjusted"
                },
                "parameters": self.market_params.copy(),
                "stock_outlook": {cat: "Conservative outlook" for cat in self.categories.keys()}
        }
    
    def get_previous_trading_day_data(self) -> Optional[Dict[str, Any]]:
        """Get previous trading day data for AI context (not today's)"""
        analysis_file = self.data_dir / "daily_analysis.json"
        if not analysis_file.exists():
            return None
        
        try:
            with open(analysis_file, 'r') as f:
                analyses = json.load(f)
            
            if not analyses:
                return None
                
            # Find the most recent analysis that's NOT from today
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            for analysis in reversed(analyses):  # Start from most recent
                analysis_date = analysis.get("timestamp", "")[:10]  # Extract YYYY-MM-DD
                if analysis_date != today:
                    print(f"📅 Using previous trading day analysis from {analysis_date}")
                    return analysis
            
            print("📅 No previous trading day analysis found (only today's data)")
            return None
            
        except Exception as e:
            print(f"❌ Error loading previous analysis: {e}")
        
        return None
    
    def save_daily_analysis(self, analysis: Dict[str, Any]) -> None:
        """Save daily market analysis"""
        analysis_file = self.data_dir / "daily_analysis.json"
        analyses = []
        
        if analysis_file.exists():
            with open(analysis_file, 'r') as f:
                analyses = json.load(f)
        
        # Add timestamp and current market state
        analysis["timestamp"] = datetime.now(timezone.utc).isoformat()
        analysis["market_state"] = {
            "categories": self.categories,
            "parameters": self.market_params
        }
        
        analyses.append(analysis)
        
        # Keep last 365 analyses (1 year)
        analyses = analyses[-365:]
        
        with open(analysis_file, 'w') as f:
            json.dump(analyses, f, indent=2)
    
    async def get_daily_market_analysis_with_prompt(self, custom_prompt: str, previous_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhanced daily analysis with custom prompt and consistency checks"""
        print(f"🧠 Running enhanced AI market analysis with custom prompt...")
        
        if not self.client:
            print("❌ Discord client not available for market analysis")
            return self.get_fallback_analysis()
        
        try:
            # Collect recent messages from all allowed channels with focus on news
            all_messages = []
            news_messages = []
            cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)  # Last 24 hours
            
            print(f"📊 Collecting messages from {len(ALL_ALLOWED_CHANNELS)} authorized channels with news focus...")
            
            for guild in self.client.guilds:
                for channel in guild.text_channels:
                    if channel.name.lower() not in ALL_ALLOWED_CHANNELS:
                        continue
                    
                    if not channel.permissions_for(guild.me).read_message_history:
                        continue
                    
                    try:
                        channel_messages = []
                        # Get more messages from news channels for change detection
                        limit = 100 if any(news_ch in channel.name.lower() for news_ch in ['news', 'announcement', 'press']) else 50
                        
                        async for message in channel.history(limit=limit, after=cutoff_date):
                            if message.author.bot:
                                continue
                            
                            message_data = {
                                "content": message.content[:300],  # Limit message length
                                "channel": channel.name,
                                "timestamp": message.created_at.isoformat(),
                                "author_roles": [role.name for role in getattr(message.author, 'roles', [])]
                            }
                            
                            channel_messages.append(message_data)
                            
                            # Separate news messages for change detection
                            if any(news_ch in channel.name.lower() for news_ch in ['news', 'announcement', 'press']):
                                news_messages.append(message_data)
                        
                        all_messages.extend(channel_messages)
                        
                        if len(all_messages) >= 750:  # Increased cap for enhanced analysis
                            break
                            
                    except Exception as e:
                        print(f"⚠️ Error collecting from {channel.name}: {e}")
                        continue
                
                if len(all_messages) >= 750:
                    break
            
            # Limit to most recent messages
            all_messages = sorted(all_messages, key=lambda x: x["timestamp"], reverse=True)[:750]
            news_messages = sorted(news_messages, key=lambda x: x["timestamp"], reverse=True)[:100]
            
            print(f"📝 Collected {len(all_messages)} total messages ({len(news_messages)} news messages)")
            
            # Build enhanced prompt with consistency instructions
            analysis_prompt = self.build_enhanced_analysis_prompt(
                all_messages, news_messages, previous_analysis, custom_prompt
            )
            
            # Generate AI analysis with higher output limit for detailed reasoning
            response = await self.model.generate_content_async(
                analysis_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for consistency
                    max_output_tokens=3000  # More space for reasoning
                )
            )
            
            # Parse AI response
            analysis = self.parse_market_analysis(response.text)
            
            # Add metadata about the enhancement
            analysis["enhanced_analysis"] = {
                "custom_prompt": custom_prompt,
                "news_messages_analyzed": len(news_messages),
                "total_messages_analyzed": len(all_messages),
                "consistency_check": bool(previous_analysis),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return analysis
            
        except Exception as e:
            print(f"❌ Enhanced AI market analysis failed: {e}")
            return self.get_fallback_analysis()
    
    def build_enhanced_analysis_prompt(self, messages: List[Dict], news_messages: List[Dict], 
                                       previous_analysis: Optional[Dict], custom_prompt: str) -> str:
        """Build enhanced prompt with consistency instructions and news detection"""
        
        # Organize messages by channel category
        categorized_messages = {}
        for msg in messages:
            channel_name = msg["channel"]
            for cat_name, channels in ALLOWED_CHANNELS.items():
                if channel_name in channels:
                    if cat_name not in categorized_messages:
                        categorized_messages[cat_name] = []
                    categorized_messages[cat_name].append(msg)
                    break
        
        # Determine if there's significant news
        news_count = len(news_messages)
        has_significant_news = news_count > 5  # Threshold for "significant news"
        
        previous_params_text = ""
        if previous_analysis and "parameters" in previous_analysis:
            prev_params = previous_analysis["parameters"]
            previous_params_text = f"""
**IMPORTANT CONSISTENCY INSTRUCTIONS**:
Previous trading day parameters were:
- trend_direction: {prev_params.get('trend_direction', 0):+.3f}
- volatility: {prev_params.get('volatility', 0.3):.3f}
- momentum: {prev_params.get('momentum', 0.5):.3f}
- market_sentiment: {prev_params.get('market_sentiment', 0.6):.3f}
- long_term_outlook: {prev_params.get('long_term_outlook', 0.55):.3f}

CONSISTENCY RULES:
- If there are FEWER than 5 significant news messages, maintain parameters within ±0.1 of previous values
- Only make LARGER changes (±0.2 or more) if there are major news events or significant policy changes
- For long_term_outlook, changes should be minimal (±0.03) unless there's major economic news
- The goal is market stability with gradual adjustments, not dramatic swings
"""
        else:
            previous_params_text = f"""
**INITIALIZATION FROM ECONOMIC DATA**:
No previous trading day analysis found. Initialize parameters based SOLELY on current economic data above.
Use the economic indicators to set realistic starting parameters:
- High inflation should increase volatility and decrease sentiment
- GDP growth should influence trend direction and momentum
- Market confidence should directly influence market_sentiment
- Economic uncertainty should increase volatility
"""
        
        prompt = f"""You are an expert financial analyst for a Virtual Congress stock market simulation. 
Analyze the provided Discord server activity from the last 24 hours to determine market parameters for today's trading.

**CUSTOM USER INSTRUCTION**: {custom_prompt}

{previous_params_text}

**NEWS ANALYSIS**:
Found {news_count} news messages in the last 24 hours.
Significant news threshold: {'MET' if has_significant_news else 'NOT MET'} ({news_count}/5 messages)

**Current Stock Market Structure**:
{json.dumps(self.categories, indent=2)}

**Market Parameters to Set** (each 0.0 to 1.0):
- trend_direction: -1.0 (bearish) to 1.0 (bullish) - overall market direction today
- volatility: 0.0 (stable) to 1.0 (very volatile) - how much prices will fluctuate  
- momentum: 0.0 (weak movements) to 1.0 (strong movements) - strength of price changes
- market_sentiment: 0.0 (fearful/pessimistic) to 1.0 (confident/optimistic) - investor confidence
- long_term_outlook: 0.0 (pessimistic) to 1.0 (optimistic) - make only TINY changes to this

**Discord Activity Analysis**:
Total messages analyzed: {len(messages)}
News messages analyzed: {news_count}

**Activity by Category**:
"""
        
        for cat_name, cat_messages in categorized_messages.items():
            prompt += f"\n**{cat_name}** ({len(cat_messages)} messages):\n"
            # Include sample messages
            for msg in cat_messages[:3]:  # Show first 3 messages per category
                prompt += f"- [{msg['channel']}] {msg['content'][:100]}...\n"
            if len(cat_messages) > 3:
                prompt += f"... and {len(cat_messages) - 3} more messages\n"
        
        # Add dedicated news section
        if news_messages:
            prompt += f"\n**KEY NEWS MESSAGES** ({len(news_messages)} messages):\n"
            for msg in news_messages[:5]:  # Show top 5 news messages
                prompt += f"- [{msg['channel']}] {msg['content'][:150]}...\n"
        
        # Add previous analysis context if available
        if previous_analysis:
            prompt += f"\n**Previous Analysis Context**:\n"
            if "reasoning" in previous_analysis:
                prev_reasoning = previous_analysis["reasoning"]
                prompt += f"Previous market overview: {prev_reasoning.get('market_overview', 'N/A')[:200]}...\n"
            prompt += f"Previous timestamp: {previous_analysis.get('timestamp', 'unknown')[:19]}\n"
        
        # Add current stock data
        current_stocks = {}
        for cat_name, cat_data in self.categories.items():
            current_stocks[cat_name] = {
                "stocks": [{"symbol": s["symbol"], "name": s["name"], "price": s["price"]} for s in cat_data["stocks"]],
                "etf_price": sum(s["price"] for s in cat_data["stocks"]) / len(cat_data["stocks"]) if cat_data["stocks"] else 0
            }
        
        prompt += f"\n**Current Stock Market State**:\n{json.dumps(current_stocks, indent=2)}\n"
        
        # Add current economic data from files
        try:
            from economic_utils import get_economic_data
            economic_data = get_economic_data("all", days_back=30)
            
            # Include inflation data
            if "inflation" in economic_data and economic_data["inflation"]:
                latest_inflation = economic_data["inflation"][0]["data"]
                prompt += f"\n**CURRENT INFLATION DATA**:\n"
                prompt += f"- Current Rate: {latest_inflation.get('rate', 'N/A')}%\n"
                prompt += f"- Federal Funds Rate: {latest_inflation.get('federal_funds_rate', 'N/A')}%\n"
                prompt += f"- Trend: {latest_inflation.get('trend', 'N/A')}\n"
                prompt += f"- Policy Impact: {latest_inflation.get('policy_impact', 'N/A')[:150]}...\n"
            
            # Include GDP data
            if "gdp" in economic_data and economic_data["gdp"]:
                latest_gdp = economic_data["gdp"][0]["data"]
                prompt += f"\n**CURRENT GDP DATA**:\n"
                prompt += f"- GDP: ${latest_gdp.get('value', 'N/A')}T\n"
                prompt += f"- Growth Rate: {latest_gdp.get('change_percent', 'N/A')}%\n"
                prompt += f"- Quarterly Growth: {latest_gdp.get('quarterly_growth', 'N/A')}%\n"
                prompt += f"- Outlook: {latest_gdp.get('outlook', 'N/A')[:150]}...\n"
            
            # Include sentiment data
            if "sentiment" in economic_data and economic_data["sentiment"]:
                latest_sentiment = economic_data["sentiment"][0]["data"]
                prompt += f"\n**CURRENT MARKET SENTIMENT DATA**:\n"
                prompt += f"- Market Confidence: {latest_sentiment.get('market_confidence', 'N/A')}%\n"
                prompt += f"- Business Sentiment: {latest_sentiment.get('business_sentiment', 'N/A')}%\n"
                prompt += f"- Consumer Confidence: {latest_sentiment.get('consumer_confidence', 'N/A')}%\n"
                prompt += f"- Inflation Anxiety: {latest_sentiment.get('inflation_anxiety', 'N/A')}%\n"
                prompt += f"- Outlook: {latest_sentiment.get('outlook', 'N/A')[:150]}...\n"
            
            # Include unemployment data
            if "unemployment" in economic_data and economic_data["unemployment"]:
                latest_unemployment = economic_data["unemployment"][0]["data"]
                prompt += f"\n**CURRENT UNEMPLOYMENT DATA**:\n"
                prompt += f"- Rate: {latest_unemployment.get('rate', 'N/A')}%\n"
                prompt += f"- Trend: {latest_unemployment.get('trend', 'N/A')}\n"
                prompt += f"- Labor Market: {latest_unemployment.get('labor_market_state', 'N/A')}\n"
                
        except Exception as e:
            print(f"⚠️ Could not load economic data for AI prompt: {e}")
            prompt += f"\n**ECONOMIC DATA**: Not available\n"
        
        # Add recent performance context
        historical_data = self.get_historical_data(days_back=7)
        if historical_data:
            prompt += f"\n**Recent Stock Performance**: {len(historical_data)} data points from last 7 days available.\n"
        
        prompt += f"""
**Your Enhanced Analysis Task**:
1. FIRST: Evaluate if there are significant news events or policy changes that justify parameter changes
2. Apply the consistency rules - maintain stability unless news warrants changes
3. Consider the custom user instruction: "{custom_prompt}"
4. Analyze government activity, policy discussions, news sentiment, and public reaction  
5. Set realistic market parameters based on observed activity levels and sentiment
6. Provide detailed reasoning for any parameter changes from previous analysis
7. For long_term_outlook, make only tiny adjustments (±0.03 max) unless major events occurred

**Required JSON Output Format**:
{{
  "reasoning": {{
    "market_overview": "Overall assessment of market conditions based on server activity",
    "news_impact": "Assessment of whether news messages justify parameter changes",
    "consistency_analysis": "Explanation of how you maintained consistency with previous analysis",
    "trend_analysis": "Why you chose the trend_direction value and how it relates to previous",
    "volatility_analysis": "Why you chose the volatility level and any changes from previous",
    "momentum_analysis": "Why you chose the momentum level and justification for changes",
    "sentiment_analysis": "Why you chose the market_sentiment level",
    "outlook_analysis": "Why you adjusted (or didn't adjust) long_term_outlook",
    "custom_prompt_impact": "How the custom prompt '{custom_prompt}' influenced your analysis"
  }},
  "parameters": {{
    "trend_direction": [number between -1.0 and 1.0 based on economic data and analysis],
    "volatility": [number between 0.0 and 1.0 based on economic data and analysis],
    "momentum": [number between 0.0 and 1.0 based on economic data and analysis],
    "market_sentiment": [number between 0.0 and 1.0 based on economic data and analysis],
    "long_term_outlook": [number between 0.0 and 1.0 based on economic data and analysis]
  }},
  "stock_outlook": {{
    "ENERGY": "Brief outlook for energy sector stocks",
    "ENTERTAINMENT": "Brief outlook for entertainment sector stocks",
    "FINANCE": "Brief outlook for finance sector stocks", 
    "HEALTH": "Brief outlook for health sector stocks",
    "MANUFACTURING": "Brief outlook for manufacturing sector stocks",
    "RETAIL": "Brief outlook for retail sector stocks",
    "TECH": "Brief outlook for tech sector stocks",
    "TRANSPORT": "Brief outlook for transport sector stocks"
  }},
  "change_summary": {{
    "significant_changes": ["List any significant parameter changes and why"],
    "news_driven_changes": ["List changes specifically driven by news"],
    "consistency_maintained": true
  }}
}}

Provide your enhanced analysis now:"""
        
        return prompt
    
    async def replace_daily_analysis(self, new_analysis: Dict[str, Any]) -> None:
        """Delete previous analysis and save new one"""
        analysis_file = self.data_dir / "daily_analysis.json"
        
        # Load existing analyses
        analyses = []
        if analysis_file.exists():
            try:
                with open(analysis_file, 'r') as f:
                    analyses = json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Invalid JSON in daily analysis file, starting fresh")
                analyses = []
        
        # Remove today's analysis if it exists
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        analyses = [a for a in analyses if not a.get("timestamp", "").startswith(today)]
        
        print(f"🗑️ Removed existing analysis for {today}")
        
        # Add new analysis with current market state
        new_analysis["timestamp"] = datetime.now(timezone.utc).isoformat()
        new_analysis["market_state"] = {
            "categories": self.categories,
            "parameters": self.market_params
        }
        
        analyses.append(new_analysis)
        
        # Keep last 365 analyses (1 year)
        analyses = analyses[-365:]
        
        # Save updated analyses
        with open(analysis_file, 'w') as f:
            json.dump(analyses, f, indent=2)
        
        print(f"✅ Saved new analysis replacing previous one for {today}")
    
    async def apply_hourly_price_update(self, hour_index: int) -> None:
        """Apply precomputed price update for a specific hour"""
        if not self.precomputed_prices:
            print("⚠️ No precomputed prices available")
            return
        
        print(f"📊 Applying price update for hour {hour_index}")
        
        # Update all stock prices
        price_updates = {}
        
        for cat_name, cat_data in self.categories.items():
            for i, stock in enumerate(cat_data["stocks"]):
                symbol = stock["symbol"]
                if symbol in self.precomputed_prices:
                    prices = self.precomputed_prices[symbol]
                    if hour_index < len(prices):
                        old_price = stock["price"]
                        new_price = prices[hour_index]
                        stock["price"] = new_price
                        
                        price_updates[symbol] = {
                            "old_price": old_price,
                            "new_price": new_price,
                            "change": new_price - old_price,
                            "change_pct": ((new_price - old_price) / old_price) * 100
                        }
        
        # Calculate updated category prices
        category_prices = self.calculate_category_prices()
        
        # Save updated market data
        self.save_market_data()
        
        # Save historical data
        timestamp = datetime.now(timezone.utc).isoformat()
        historical_data = {
            "individual_stocks": {symbol: stock["price"] for cat in self.categories.values() 
                                for stock in cat["stocks"] for symbol in [stock["symbol"]]},
            "category_prices": category_prices,
            "market_params": self.market_params,
            "trading_hour": hour_index,
            "analysis_update": True
        }
        
        self.save_historical_data(timestamp, historical_data)
        
        print(f"✅ Updated {len(price_updates)} stock prices and ETFs for hour {hour_index}")
        
        return price_updates
    
    def generate_stock_chart(self, symbol: str, prices: List[float]) -> Optional[bytes]:
        """Generate matplotlib chart for stock price movement"""
        try:
            # Create figure
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Generate time labels for 24/7 trading (last 12 hours shown for readability)
            start_hour = max(0, 24 - len(prices))  # Start from appropriate hour
            hours = [f"{h:02d}:00" for h in range(start_hour, start_hour + len(prices))]
            hours = hours[:len(prices)]  # Match the number of price points
            
            # Plot line chart
            ax.plot(hours, prices, linewidth=2, color='#00ff88', marker='o', markersize=4)
            
            # Calculate change
            if len(prices) > 1:
                change = prices[-1] - prices[0]
                change_pct = (change / prices[0]) * 100
                
                color = '#00ff88' if change >= 0 else '#ff4444'
                direction = '↗' if change >= 0 else '↘'
                
                ax.set_title(f"{symbol} - {direction} ${change:+.2f} ({change_pct:+.2f}%)", 
                           fontsize=14, color=color, fontweight='bold')
            else:
                ax.set_title(f"{symbol}", fontsize=14, color='white', fontweight='bold')
            
            # Style the chart
            ax.set_xlabel("Hours (ET) [24/7 Trading]", fontsize=10, color='lightgray')
            ax.set_ylabel("Price ($)", fontsize=10, color='lightgray')
            ax.grid(True, alpha=0.3)
            ax.tick_params(colors='lightgray')
            
            # Rotate x-axis labels for better readability
            plt.xticks(rotation=45)
            
            # Tight layout
            plt.tight_layout()
            
            # Save to bytes
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', facecolor='#2f3136', dpi=100)
            buffer.seek(0)
            
            chart_bytes = buffer.getvalue()
            plt.close(fig)
            
            return chart_bytes
            
        except Exception as e:
            print(f"❌ Error generating chart for {symbol}: {e}")
            return None

# Global stock market instance
stock_market = StockMarket()

def get_stock_market() -> StockMarket:
    """Get the global stock market instance"""
    return stock_market

class StockMarketScheduler:
    """Handles automated trading day scheduling and hourly updates"""
    
    def __init__(self, stock_market: StockMarket):
        self.stock_market = stock_market
        self.daily_prep_task = None
        self.hourly_update_task = None
        self.current_hour_index = 0
        
    def get_et_now(self) -> datetime:
        """Get current Eastern Time"""
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo("America/New_York"))
        except ImportError:
            # Fallback for older Python versions
            import pytz
            et_tz = pytz.timezone("America/New_York")
            return datetime.now(et_tz)
    
    def is_trading_hours(self) -> bool:
        """Check if currently in trading hours (9 AM - 5 PM ET)"""
        et_now = self.get_et_now()
        return 9 <= et_now.hour < 17  # 9 AM to 4:59 PM
    
    def get_trading_day_id(self) -> str:
        """Get current trading day identifier"""
        et_now = self.get_et_now()
        return et_now.strftime("%Y-%m-%d")
    
    def get_next_market_open(self) -> datetime:
        """Get the next market opening time (9 AM ET)"""
        et_now = self.get_et_now()
        
        # If it's before 9 AM today, market opens today at 9 AM
        if et_now.hour < 9:
            next_open = et_now.replace(hour=9, minute=0, second=0, microsecond=0)
        else:
            # Otherwise, market opens tomorrow at 9 AM
            tomorrow = et_now + timedelta(days=1)
            next_open = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        
        return next_open
    
    def get_next_prep_time(self) -> datetime:
        """Get next market prep time (8:40 AM ET, 20 minutes before open)"""
        next_open = self.get_next_market_open()
        return next_open - timedelta(minutes=20)
    
    async def start_scheduler(self):
        """Start the automated scheduler"""
        print("⏰ Starting stock market scheduler...")
        
        # Start daily prep task
        self.daily_prep_task = asyncio.create_task(self.daily_prep_loop())
        
        # Start hourly updates (24/7 trading - always active)
        self.hourly_update_task = asyncio.create_task(self.hourly_update_loop())
        
        print("✅ Stock market scheduler started")
    
    async def daily_prep_loop(self):
        """Daily loop to prepare market for each trading day"""
        while True:
            try:
                next_prep = self.get_next_prep_time()
                current_time = self.get_et_now()
                
                # Calculate sleep time until next prep
                sleep_seconds = (next_prep - current_time).total_seconds()
                
                if sleep_seconds > 0:
                    print(f"💤 Next market prep in {sleep_seconds/3600:.1f} hours at {next_prep.strftime('%I:%M %p ET')}")
                    await asyncio.sleep(sleep_seconds)
                
                # Run market preparation
                await self.prepare_trading_day()
                
                # Wait a bit to avoid immediate re-triggering
                await asyncio.sleep(60)
                
            except Exception as e:
                print(f"❌ Error in daily prep loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def prepare_trading_day(self):
        """Run daily market analysis and update parameters (8:40 AM ET daily)"""
        trading_day = self.get_trading_day_id()
        print(f"📊 Running daily market analysis for: {trading_day} [24/7 Trading]")
        
        try:
            # Run AI analysis
            analysis = await self.stock_market.get_daily_market_analysis()
            
            # Save analysis
            self.stock_market.save_daily_analysis(analysis)
            
            # Update market parameters from analysis
            self.stock_market.market_params = analysis.get("parameters", self.stock_market.market_params)
            
            # CRITICAL: Recalculate baseline prices from new economic parameters
            print("🔄 Recalculating baseline prices for new trading day...")
            self.stock_market.recalculate_all_baseline_prices()
            
            # Generate hourly prices for the day with updated baselines
            hourly_prices = self.stock_market.generate_hourly_prices(trading_day)
            self.stock_market.precomputed_prices = hourly_prices
            
            # Set trading day state (always active for 24/7 trading)
            self.stock_market.is_trading_day = True
            self.stock_market.current_trading_day = trading_day
            self.current_hour_index = 0
            
            # Save market data
            self.stock_market.save_market_data()
            
            # Send preparation message to channel
            await self.send_daily_analysis_message(analysis)
            
            print(f"✅ Daily analysis complete for {trading_day} • 24/7 Trading continues")
            
        except Exception as e:
            print(f"❌ Error preparing trading day: {e}")
    
    async def hourly_update_loop(self):
        """Hourly loop to update stock prices continuously (24/7 trading)"""
        while True:
            try:
                # Market is always open - no need to check trading hours
                
                # Wait until the next hour
                et_now = self.get_et_now()
                next_hour = et_now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                sleep_seconds = (next_hour - et_now).total_seconds()
                
                if sleep_seconds > 0:
                    await asyncio.sleep(sleep_seconds)
                
                # Update prices
                await self.update_hourly_prices()
                
            except Exception as e:
                print(f"❌ Error in hourly update loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def update_hourly_prices(self):
        """Update stock prices with precomputed hourly values"""
        if not self.stock_market.precomputed_prices:
            print("⚠️ No precomputed prices available")
            return
        
        et_now = self.get_et_now()
        hour_index = et_now.hour  # 0 = midnight, 1 = 1 AM, etc. (24-hour format)
        
        # Market runs 24/7 - no hour restrictions
        
        print(f"📊 Updating stock prices for hour {hour_index} ({et_now.strftime('%I:%M %p ET')}) [24/7 Trading]")
        
        # Update all stock prices
        price_updates = {}
        
        for cat_name, cat_data in self.stock_market.categories.items():
            for i, stock in enumerate(cat_data["stocks"]):
                symbol = stock["symbol"]
                if symbol in self.stock_market.precomputed_prices:
                    prices = self.stock_market.precomputed_prices[symbol]
                    if hour_index < len(prices):
                        old_price = stock["price"]
                        new_price = prices[hour_index]
                        stock["price"] = new_price
                        
                        price_updates[symbol] = {
                            "old_price": old_price,
                            "new_price": new_price,
                            "change": new_price - old_price,
                            "change_pct": ((new_price - old_price) / old_price) * 100
                        }
        
        # Calculate category prices
        category_prices = self.stock_market.calculate_category_prices()
        
        # Save historical data
        timestamp = datetime.now(timezone.utc).isoformat()
        historical_data = {
            "individual_stocks": {symbol: stock["price"] for cat in self.stock_market.categories.values() 
                                for stock in cat["stocks"] for symbol in [stock["symbol"]]},
            "category_prices": category_prices,
            "market_params": self.stock_market.market_params,
            "trading_hour": hour_index
        }
        
        self.stock_market.save_historical_data(timestamp, historical_data)
        self.stock_market.save_market_data()
        
        # Send update to Discord
        await self.send_hourly_update(price_updates, category_prices, hour_index)
        
        self.current_hour_index = hour_index
    
    async def send_daily_analysis_message(self, analysis: Dict[str, Any]):
        """Send daily analysis message to Discord"""
        if not self.stock_market.client:
            return
        
        try:
            channel = self.stock_market.client.get_channel(self.stock_market.stocks_channel_id)
            if not channel:
                print(f"⚠️ Stocks channel {self.stock_market.stocks_channel_id} not found")
                return
            
            # Create embed
            embed = discord.Embed(
                title="📊 Daily Market Analysis Complete",
                description=f"Analysis Day: {self.stock_market.current_trading_day} • 24/7 Trading Active",
                color=0x00ff88,
                timestamp=datetime.utcnow()
            )
            
            # Market parameters
            params = analysis.get("parameters", {})
            param_text = f"""
**Trend**: {params.get('trend_direction', 0):.2f} {'📈' if params.get('trend_direction', 0) > 0 else '📉' if params.get('trend_direction', 0) < 0 else '➡️'}
**Volatility**: {params.get('volatility', 0):.2f} {'🌪️' if params.get('volatility', 0) > 0.7 else '🌊' if params.get('volatility', 0) > 0.4 else '🌊'}
**Momentum**: {params.get('momentum', 0):.2f} {'🚀' if params.get('momentum', 0) > 0.7 else '⚡' if params.get('momentum', 0) > 0.4 else '🐌'}
**Sentiment**: {params.get('market_sentiment', 0):.2f} {'😄' if params.get('market_sentiment', 0) > 0.7 else '😐' if params.get('market_sentiment', 0) > 0.4 else '😟'}
"""
            
            embed.add_field(name="📊 Market Parameters", value=param_text.strip(), inline=True)
            
            # Market outlook by sector
            outlook = analysis.get("stock_outlook", {})
            outlook_text = ""
            for sector, desc in outlook.items():
                emoji = "📰" if sector == "NEWS" else "🏛️" if sector == "CONGRESS" else "🏢" if sector == "EXECUTIVE" else "🏞️" if sector == "STATES" else "⚖️" if sector == "COURTS" else "👥"
                outlook_text += f"{emoji} **{sector}**: {desc[:50]}...\n"
            
            if outlook_text:
                embed.add_field(name="🎯 Sector Outlook", value=outlook_text.strip(), inline=False)
            
            # AI reasoning summary
            reasoning = analysis.get("reasoning", {})
            if "market_overview" in reasoning:
                overview = reasoning["market_overview"][:200] + "..." if len(reasoning["market_overview"]) > 200 else reasoning["market_overview"]
                embed.add_field(name="🧠 AI Analysis", value=overview, inline=False)
            
            embed.set_footer(text="Daily analysis complete • 24/7 Trading Active")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            print(f"❌ Error sending market prep message: {e}")
    
    async def send_hourly_update(self, price_updates: Dict, category_prices: Dict, hour_index: int):
        """Send hourly price update to Discord"""
        if not self.stock_market.client:
            return
        
        try:
            channel = self.stock_market.client.get_channel(self.stock_market.stocks_channel_id)
            if not channel:
                return
            
            et_now = self.get_et_now()
            
            # Create main embed
            embed = discord.Embed(
                title=f"📊 Hourly Market Update",
                description=f"{et_now.strftime('%I:%M %p ET')} • Hour {hour_index:02d}/24 [24/7 Trading]",
                color=0x0099ff,
                timestamp=datetime.utcnow()
            )
            
            # Show biggest movers
            if price_updates:
                # Sort by absolute percentage change
                sorted_updates = sorted(price_updates.items(), 
                                      key=lambda x: abs(x[1]["change_pct"]), reverse=True)
                
                movers_text = ""
                for symbol, update in sorted_updates[:6]:  # Top 6 movers
                    change_pct = update["change_pct"]
                    direction = "📈" if change_pct > 0 else "📉" if change_pct < 0 else "➡️"
                    movers_text += f"{direction} **{symbol}**: ${update['new_price']:.2f} ({change_pct:+.1f}%)\n"
                
                embed.add_field(name="🏃 Biggest Movers", value=movers_text.strip(), inline=True)
            
            # Show category ETF prices
            if category_prices:
                etf_text = ""
                for cat_name, price in category_prices.items():
                    emoji = "📰" if cat_name == "NEWS" else "🏛️" if cat_name == "CONGRESS" else "🏢" if cat_name == "EXECUTIVE" else "🏞️" if cat_name == "STATES" else "⚖️" if cat_name == "COURTS" else "👥"
                    etf_text += f"{emoji} **{cat_name}**: ${price:.2f}\n"
                
                embed.add_field(name="📊 Sector ETFs", value=etf_text.strip(), inline=True)
            
            # Try to create and attach a chart for the most active stock
            chart_bytes = None
            if price_updates:
                most_active_symbol = max(price_updates.keys(), 
                                       key=lambda s: abs(price_updates[s]["change_pct"]))
                
                if most_active_symbol in self.stock_market.precomputed_prices:
                    prices = self.stock_market.precomputed_prices[most_active_symbol][:hour_index + 1]
                    # Show last 12 hours for readability on 24/7 charts
                    chart_prices = prices[-12:] if len(prices) > 12 else prices
                    chart_bytes = self.stock_market.generate_stock_chart(most_active_symbol, chart_prices)
            
            if chart_bytes:
                # Attach chart
                chart_file = discord.File(io.BytesIO(chart_bytes), filename=f"{most_active_symbol}_chart.png")
                embed.set_image(url=f"attachment://{most_active_symbol}_chart.png")
                await channel.send(embed=embed, file=chart_file)
            else:
                await channel.send(embed=embed)
            
        except Exception as e:
            print(f"❌ Error sending hourly update: {e}")

# Global scheduler instance
stock_scheduler = None

async def initialize_stock_market(client) -> None:
    """Initialize the stock market system"""
    global stock_scheduler
    
    print("📈 Initializing Stock Market System...")
    
    stock_market.client = client
    
    # Load existing data
    if stock_market.load_market_data():
        print("📊 Existing market data loaded")
    else:
        print("🆕 New market initialization - integrating with economic system...")
        
        # Try to get economic initialization data
        try:
            from economic_utils import get_stock_initialization_data
            econ_init = get_stock_initialization_data()
            
            if "stock_market_initialization" in econ_init:
                # Use economic data to set initial market parameters
                init_params = econ_init["stock_market_initialization"]
                stock_market.market_params.update(init_params)
                print(f"📊 Market parameters initialized from economic data")
                print(f"   Trend: {init_params['trend_direction']:+.2f}, Volatility: {init_params['volatility']:.2f}")
                print(f"   Sentiment: {init_params['market_sentiment']:.2f}, Momentum: {init_params['momentum']:.2f}")
            
            if "initialization_message" in econ_init:
                print(f"📈 {econ_init['initialization_message']}")
                
        except Exception as e:
            print(f"⚠️ Could not integrate with economic system: {e}")
            print("📊 Using default market parameters")
        
        # Save the initialized data
        stock_market.save_market_data()
    
    # Initialize scheduler
    stock_scheduler = StockMarketScheduler(stock_market)
    await stock_scheduler.start_scheduler()
    
    print("✅ Stock Market System ready")