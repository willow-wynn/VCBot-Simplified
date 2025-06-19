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
import signal
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import discord
from discord.ext import commands, tasks
import google.generativeai as genai
from config import GEMINI_API_KEY, BOT_HELPER_CHANNEL, STOCK_DATA_DIR, JSON_OUTPUT_CHANNEL
from economic_utils import ALL_ALLOWED_CHANNELS, ALLOWED_CHANNELS

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

class StockMarket:
    """Advanced Stock Market System with AI-driven analysis and realistic price movements"""
    
    def __init__(self):
        self.data_dir = STOCK_DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.client = None
        self.stocks_channel_id = BOT_HELPER_CHANNEL  # Default channel
        
        # Flag to prevent infinite loops during initialization
        self._initializing = True
        # Flag to prevent infinite loops during ETF price calculations
        self._calculating_etf_prices = False
        
        # Initialize invisible market factors
        self.invisible_factors = {
            "institutional_flow": 0.0,
            "liquidity_factor": 0.7,
            "news_velocity": 0.5,
            "sector_rotation": 0.0,
            "risk_appetite": 0.5
        }
        
        # On-demand pricing configuration
        self.price_update_rate_minutes = 60  # Default 60 minutes (hourly)
        self.market_open_time = None  # Will be set when market opens
        self.daily_ranges = {}  # Store daily price ranges for each stock
        
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
                    {"symbol": "GS", "name": "Goldman Sachs", "price": 266.66, "sector": "investment"},
                    {"symbol": "BRK.B", "name": "Berkshire Hathaway Class B", "price": 296.34, "sector": "holdings"}
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
        
        # Initialize ETF structure
        self.etfs = {
            # Market Index ETFs
            "SPY": {
                "symbol": "SPY",
                "name": "SPDR S&P 500 ETF",
                "type": "market_cap_weighted",
                "description": "Tracks the S&P 500 index of large-cap US stocks",
                "expense_ratio": 0.0009,  # 0.09%
                "holdings": {
                    "AAPL": 0.15, "MSFT": 0.13, "GOOGL": 0.08, "NVDA": 0.07,
                    "JPM": 0.04, "UNH": 0.04, "JNJ": 0.03, "V": 0.03,
                    "XOM": 0.03, "WMT": 0.03, "BAC": 0.02, "HD": 0.02,
                    "CVX": 0.02, "PFE": 0.02, "DIS": 0.02, "NFLX": 0.02,
                    "COP": 0.01, "GS": 0.01, "LMT": 0.01, "COST": 0.01,
                    "CAT": 0.01, "BA": 0.01, "GE": 0.01, "EA": 0.01,
                    "BRK.B": 0.03
                },
                "volatility_modifier": 0.7,  # Less volatile than individual stocks
                "price": 450.0,  # Will be calculated dynamically
                "daily_range_low": 445.0,
                "daily_range_high": 455.0
            },
            "QQQ": {
                "symbol": "QQQ",
                "name": "Invesco QQQ Trust",
                "type": "market_cap_weighted",
                "description": "Tracks the NASDAQ-100 index of large-cap tech stocks",
                "expense_ratio": 0.0020,  # 0.20%
                "holdings": {
                    "AAPL": 0.20, "MSFT": 0.18, "GOOGL": 0.12, "NVDA": 0.15,
                    "NFLX": 0.05, "V": 0.04, "DIS": 0.03, "EA": 0.03,
                    "JPM": 0.02, "UNH": 0.02, "JNJ": 0.02, "WMT": 0.02,
                    "HD": 0.02, "GS": 0.02, "COST": 0.02, "CAT": 0.02,
                    "BA": 0.02, "GE": 0.02
                },
                "volatility_modifier": 0.8,  # Tech-heavy, more volatile
                "price": 380.0,
                "daily_range_low": 375.0,
                "daily_range_high": 385.0
            },
            "DIA": {
                "symbol": "DIA",
                "name": "SPDR Dow Jones Industrial Average ETF",
                "type": "equal_weighted",
                "description": "Tracks the Dow Jones Industrial Average of 30 large companies",
                "expense_ratio": 0.0016,  # 0.16%
                "holdings": {
                    "AAPL": 0.06, "MSFT": 0.06, "JPM": 0.06, "UNH": 0.06,
                    "JNJ": 0.06, "V": 0.06, "WMT": 0.06, "HD": 0.06,
                    "CVX": 0.06, "DIS": 0.06, "GS": 0.06, "CAT": 0.06,
                    "BA": 0.06, "XOM": 0.06, "GOOGL": 0.04
                },
                "volatility_modifier": 0.6,  # Blue-chip, less volatile
                "price": 350.0,
                "daily_range_low": 347.0,
                "daily_range_high": 353.0
            },
            "VTI": {
                "symbol": "VTI",
                "name": "Vanguard Total Stock Market ETF",
                "type": "market_cap_weighted",
                "description": "Tracks the entire US stock market",
                "expense_ratio": 0.0003,  # 0.03%
                "holdings": {
                    # Represents entire market, weighted by market cap
                    "AAPL": 0.10, "MSFT": 0.09, "GOOGL": 0.06, "NVDA": 0.05,
                    "JPM": 0.03, "UNH": 0.03, "JNJ": 0.03, "V": 0.03,
                    "XOM": 0.03, "WMT": 0.03, "BAC": 0.03, "HD": 0.03,
                    "CVX": 0.03, "PFE": 0.03, "DIS": 0.03, "NFLX": 0.03,
                    "COP": 0.02, "GS": 0.02, "LMT": 0.02, "COST": 0.02,
                    "CAT": 0.02, "BA": 0.02, "GE": 0.02, "EA": 0.02,
                    "BRK.B": 0.04
                },
                "volatility_modifier": 0.65,  # Total market, moderate volatility
                "price": 240.0,
                "daily_range_low": 238.0,
                "daily_range_high": 242.0
            },
            # Sector ETFs
            "XLE": {
                "symbol": "XLE",
                "name": "Energy Select Sector SPDR Fund",
                "type": "sector",
                "description": "Tracks energy sector companies",
                "expense_ratio": 0.0010,  # 0.10%
                "sector": "ENERGY",
                "volatility_modifier": 0.9,  # Sector ETFs more volatile than broad market
                "price": 85.0,
                "daily_range_low": 83.0,
                "daily_range_high": 87.0
            },
            "XLF": {
                "symbol": "XLF",
                "name": "Financial Select Sector SPDR Fund",
                "type": "sector",
                "description": "Tracks financial sector companies",
                "expense_ratio": 0.0010,
                "sector": "FINANCE",
                "volatility_modifier": 0.85,
                "price": 40.0,
                "daily_range_low": 39.0,
                "daily_range_high": 41.0
            },
            "XLK": {
                "symbol": "XLK",
                "name": "Technology Select Sector SPDR Fund",
                "type": "sector",
                "description": "Tracks technology sector companies",
                "expense_ratio": 0.0010,
                "sector": "TECH",
                "volatility_modifier": 0.9,
                "price": 175.0,
                "daily_range_low": 172.0,
                "daily_range_high": 178.0
            },
            "XLV": {
                "symbol": "XLV",
                "name": "Health Care Select Sector SPDR Fund",
                "type": "sector",
                "description": "Tracks healthcare sector companies",
                "expense_ratio": 0.0010,
                "sector": "HEALTH",
                "volatility_modifier": 0.75,
                "price": 140.0,
                "daily_range_low": 138.0,
                "daily_range_high": 142.0
            },
            "XLI": {
                "symbol": "XLI",
                "name": "Industrial Select Sector SPDR Fund",
                "type": "sector",
                "description": "Tracks industrial and manufacturing companies",
                "expense_ratio": 0.0010,
                "sector": "MANUFACTURING",
                "volatility_modifier": 0.8,
                "price": 115.0,
                "daily_range_low": 113.0,
                "daily_range_high": 117.0
            },
            "XLY": {
                "symbol": "XLY",
                "name": "Consumer Discretionary Select Sector SPDR Fund",
                "type": "sector",
                "description": "Tracks consumer discretionary companies",
                "expense_ratio": 0.0010,
                "sector": "RETAIL",
                "volatility_modifier": 0.85,
                "price": 180.0,
                "daily_range_low": 177.0,
                "daily_range_high": 183.0
            },
            "XLRE": {
                "symbol": "XLRE",
                "name": "Real Estate Select Sector SPDR Fund",
                "type": "sector",
                "description": "Tracks real estate and REIT companies",
                "expense_ratio": 0.0010,
                "sector": "RETAIL",  # Using retail as proxy for real estate
                "volatility_modifier": 0.7,
                "price": 45.0,
                "daily_range_low": 44.0,
                "daily_range_high": 46.0
            },
            "XLP": {
                "symbol": "XLP",
                "name": "Consumer Staples Select Sector SPDR Fund",
                "type": "sector",
                "description": "Tracks consumer staples companies",
                "expense_ratio": 0.0010,
                "sector": "RETAIL",  # Consumer staples are retail-adjacent
                "volatility_modifier": 0.6,  # Staples are less volatile
                "price": 75.0,
                "daily_range_low": 74.0,
                "daily_range_high": 76.0
            },
            "XLU": {
                "symbol": "XLU",
                "name": "Utilities Select Sector SPDR Fund",
                "type": "sector",
                "description": "Tracks utility companies",
                "expense_ratio": 0.0010,
                "sector": "TRANSPORT",  # Utilities/infrastructure similar to transport
                "volatility_modifier": 0.5,  # Utilities are very stable
                "price": 70.0,
                "daily_range_low": 69.5,
                "daily_range_high": 70.5
            },
            "XLB": {
                "symbol": "XLB",
                "name": "Materials Select Sector SPDR Fund",
                "type": "sector",
                "description": "Tracks materials and mining companies",
                "expense_ratio": 0.0010,
                "sector": "MANUFACTURING",  # Materials are manufacturing inputs
                "volatility_modifier": 0.85,
                "price": 90.0,
                "daily_range_low": 88.0,
                "daily_range_high": 92.0
            },
            "XLC": {
                "symbol": "XLC",
                "name": "Communication Services Select Sector SPDR Fund",
                "type": "sector",
                "description": "Tracks media and communication companies",
                "expense_ratio": 0.0010,
                "sector": "ENTERTAINMENT",  # Media/comms maps to entertainment
                "volatility_modifier": 0.9,
                "price": 85.0,
                "daily_range_low": 83.0,
                "daily_range_high": 87.0
            },
            # Additional ETFs
            "EEM": {
                "symbol": "EEM",
                "name": "iShares MSCI Emerging Markets ETF",
                "type": "equal_weighted",
                "description": "Tracks high-growth emerging market stocks",
                "expense_ratio": 0.0068,  # 0.68%
                "holdings": {
                    # Focus on high-growth tech and entertainment stocks
                    "NVDA": 0.15, "NFLX": 0.15, "EA": 0.10, "AAPL": 0.10,
                    "MSFT": 0.10, "GOOGL": 0.10, "DIS": 0.10, "HD": 0.05,
                    "WMT": 0.05, "COST": 0.05, "V": 0.05
                },
                "volatility_modifier": 1.2,  # Higher volatility for emerging markets
                "price": 45.0,
                "daily_range_low": 43.0,
                "daily_range_high": 47.0
            },
            "AGG": {
                "symbol": "AGG",
                "name": "iShares Core U.S. Aggregate Bond ETF",
                "type": "bond",
                "description": "Tracks investment-grade U.S. bonds",
                "expense_ratio": 0.0003,  # 0.03%
                "holdings": {},  # Bond ETF - inverse correlation with market
                "volatility_modifier": 0.3,  # Very low volatility
                "price": 105.0,
                "daily_range_low": 104.5,
                "daily_range_high": 105.5,
                "inverse_correlation": True  # Moves opposite to stock market
            },
            "DJP": {
                "symbol": "DJP",
                "name": "iPath Bloomberg Commodity Index ETN",
                "type": "commodity",
                "description": "Tracks commodity futures including energy and materials",
                "expense_ratio": 0.0070,  # 0.70%
                "holdings": {
                    # Heavy weight on energy and materials stocks
                    "XOM": 0.25, "CVX": 0.20, "COP": 0.15, "CAT": 0.15,
                    "GE": 0.10, "BA": 0.10, "LMT": 0.05
                },
                "volatility_modifier": 1.0,  # Moderate volatility
                "price": 30.0,
                "daily_range_low": 29.0,
                "daily_range_high": 31.0
            }
        }
        
        # Add market cap data for stocks (in billions)
        self.market_caps = {
            "AAPL": 3000, "MSFT": 2800, "GOOGL": 1700, "NVDA": 1600,
            "BRK.B": 780, "JPM": 490, "UNH": 480, "JNJ": 380,
            "V": 450, "WMT": 420, "XOM": 410, "CVX": 340,
            "HD": 330, "BAC": 280, "PFE": 260, "DIS": 200,
            "NFLX": 190, "COP": 140, "GS": 130, "LMT": 110,
            "COST": 320, "CAT": 150, "BA": 140, "GE": 170,
            "EA": 40
        }
        
        # Market parameters - will be set by AI analysis only (no defaults)
        self.market_params = {
            "trend_direction": 0.0,
            "volatility": 0.5,
            "momentum": 0.5,
            "market_sentiment": 0.5,
            "long_term_outlook": 0.5
        }
        
        # Initialize ETF attributes (needs market_params to be set first)
        self._initialize_etf_attributes()
        
        # Softcap configuration parameters
        self.softcap_config = {
            "steepness": 75,      # How quickly resistance increases (higher = sharper transition)
            "max_resistance": 0.95,  # Maximum damping factor (0.95 = 95% resistance at extreme distances)
            "enabled": True       # Can disable to revert to hard caps if needed
        }
        
        # Initialize stock attributes for AI pricing
        self._initialize_stock_attributes()
        
        # Trading state (24/7 operation)
        self.is_trading_day = True  # Always trading
        self.current_trading_day = None
        self.last_market_open_time = None  # Track last analysis/update time
        self.precomputed_prices = {}  # Keep for backward compatibility but won't use
        self.etf_price_cache = {}  # Cache ETF prices with timestamps
        self.etf_cache_expiry = None  # When to refresh the cache (9 AM ET next day)
        self.hourly_updates_task = None
        self.admin_only_trading = False  # Trading restriction flag
        
        # Memory-first architecture tracking
        self._memory_dirty = False  # Track if memory state needs saving
        self._last_checkpoint = datetime.now(timezone.utc)
        self._checkpoint_task = None  # Will be created when bot starts
        
        # Try to load existing market data after initialization
        self.load_market_data()
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        print("📈 Stock Market System initialized")
        print(f"💼 {sum(len(cat['stocks']) for cat in self.categories.values())} individual stocks across {len(self.categories)} sectors")
        print(f"📊 {len(self.etfs)} ETFs available (market indices & sector funds)")
        print(f"📊 Market parameters calculated from economic data: Trend {self.market_params['trend_direction']:+.2f}, Volatility {self.market_params['volatility']:.2f}")
        
        # Initialization complete - allow ETF price updates now
        self._initializing = False
        
        # Precompute ETF prices on startup
        self.precompute_etf_prices()
    
    def _initialize_stock_attributes(self) -> None:
        """Initialize additional stock attributes for AI pricing"""
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                # Set default daily ranges if not present
                if "daily_range_low" not in stock:
                    stock["daily_range_low"] = stock["price"] * 0.97
                if "daily_range_high" not in stock:
                    stock["daily_range_high"] = stock["price"] * 1.03
                if "sector_factor" not in stock:
                    stock["sector_factor"] = 1.0
    
    def _initialize_etf_attributes(self) -> None:
        """Initialize ETF attributes and calculate initial prices"""
        # Set initialization flag to prevent circular recursion
        self._initializing = True
        
        try:
            # Update S&P ETF name based on stock count
            total_stocks = sum(len(cat['stocks']) for cat in self.categories.values())
            if 'SPY' in self.etfs:
                self.etfs['SPY']['name'] = f"S&P {total_stocks} ETF"
                self.etfs['SPY']['description'] = f"Tracks the S&P {total_stocks} index of all US stocks"
            
            # Don't calculate prices during initialization - will be done by precompute_etf_prices
            
            for symbol, etf in self.etfs.items():
                # Ensure all ETFs have required attributes
                if "ai_opening_price" not in etf:
                    etf["ai_opening_price"] = etf["price"]
                if "current_price" not in etf:
                    etf["current_price"] = etf["price"]
                if "sector_factor" not in etf:
                    etf["sector_factor"] = 1.0
                    
                # Calculate initial price based on holdings for non-sector ETFs
                if etf["type"] != "sector":
                    etf["price"] = self.calculate_etf_price(symbol)
        finally:
            # Clear initialization flag
            self._initializing = False
    
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
                        latest_inflation = inflation_data[-1]['data']
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
                        latest_sentiment = sentiment_data[-1]['data']
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
                        latest_gdp = gdp_data[-1]['data']
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
                        latest_unemployment = unemployment_data[-1]['data']
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
            
            # Update stored parameters and save
            self.market_params = params
            self.save_market_data()
            
            return params
            
        except Exception as e:
            print(f"❌ Critical error in economic calculation: {e}")
            raise Exception(f"Cannot calculate market parameters without economic data: {e}")
    
    def _calculate_parameter_ranges_from_economic_data(self) -> Dict[str, Dict[str, float]]:
        """Calculate acceptable parameter ranges based on economic conditions
        
        This creates data-driven ranges that AI should respect when setting parameters.
        The ranges adapt to current economic conditions instead of being hardcoded.
        """
        try:
            # Get current economic indicators
            economic_data_dir = Path("economic_data")
            
            # Read economic indicators with defaults
            inflation_rate = 2.0
            gdp_change = 2.0
            market_confidence = 50.0
            unemployment_rate = 4.0
            
            # Read actual data (same as above function)
            inflation_file = economic_data_dir / "inflation.json"
            if inflation_file.exists():
                with open(inflation_file, 'r') as f:
                    data = json.load(f)
                    if data:
                        inflation_rate = data[0]['data'].get('rate', inflation_rate)
            
            gdp_file = economic_data_dir / "gdp.json"
            if gdp_file.exists():
                with open(gdp_file, 'r') as f:
                    data = json.load(f)
                    if data:
                        gdp_change = data[0]['data'].get('change_percent', gdp_change)
            
            sentiment_file = economic_data_dir / "sentiment.json"
            if sentiment_file.exists():
                with open(sentiment_file, 'r') as f:
                    data = json.load(f)
                    if data:
                        market_confidence = data[0]['data'].get('market_confidence', market_confidence)
            
            unemployment_file = economic_data_dir / "unemployment.json"
            if unemployment_file.exists():
                with open(unemployment_file, 'r') as f:
                    data = json.load(f)
                    if data:
                        unemployment_rate = data[0]['data'].get('rate', unemployment_rate)
            
            # Calculate dynamic ranges based on economic conditions
            ranges = {}
            
            # TREND DIRECTION RANGE
            # GDP determines the center and width of acceptable trend range
            trend_center = max(-1.0, min(1.0, gdp_change / 5.0))
            trend_flexibility = 0.3  # Allow ±0.3 flexibility around economic-driven center
            
            # In extreme conditions, widen the acceptable range
            if abs(gdp_change) > 4.0:  # Strong growth or recession
                trend_flexibility = 0.5
            
            ranges["trend_direction"] = {
                "min": max(-1.0, trend_center - trend_flexibility),
                "max": min(1.0, trend_center + trend_flexibility)
            }
            
            # VOLATILITY RANGE
            # Base volatility on inflation deviation and market confidence
            inflation_deviation = abs(inflation_rate - 2.0)
            base_volatility = 0.2 + (inflation_deviation / 10.0)  # Higher inflation = higher base volatility
            
            # Low confidence also increases volatility floor
            if market_confidence < 40:
                base_volatility += 0.2
            
            ranges["volatility"] = {
                "min": max(0.1, base_volatility - 0.2),
                "max": min(1.0, base_volatility + 0.3)
            }
            
            # MOMENTUM RANGE
            # Based on GDP trend and employment
            base_momentum = 0.5  # Neutral
            
            if gdp_change > 3.0 and unemployment_rate < 4.0:
                base_momentum = 0.7  # Strong economy
            elif gdp_change < -1.0 or unemployment_rate > 6.0:
                base_momentum = 0.3  # Weak economy
            
            ranges["momentum"] = {
                "min": max(0.1, base_momentum - 0.3),
                "max": min(1.0, base_momentum + 0.3)
            }
            
            # MARKET SENTIMENT RANGE
            # Centered around actual confidence data with some flexibility
            sentiment_center = market_confidence / 100.0
            
            ranges["market_sentiment"] = {
                "min": max(0.1, sentiment_center - 0.2),
                "max": min(1.0, sentiment_center + 0.2)
            }
            
            # LONG TERM OUTLOOK RANGE
            # Very narrow range - only small adjustments allowed
            base_params = self._calculate_market_params_from_economic_data()
            current_outlook = base_params.get("long_term_outlook", 0.5)
            
            ranges["long_term_outlook"] = {
                "min": max(0.1, current_outlook - 0.02),
                "max": min(1.0, current_outlook + 0.02)
            }
            
            return ranges
            
        except Exception as e:
            print(f"⚠️ Error calculating parameter ranges: {e}")
            # Return neutral ranges as fallback
            return {
                "trend_direction": {"min": -0.5, "max": 0.5},
                "volatility": {"min": 0.2, "max": 0.8},
                "momentum": {"min": 0.2, "max": 0.8},
                "market_sentiment": {"min": 0.3, "max": 0.7},
                "long_term_outlook": {"min": 0.48, "max": 0.52}
            }
        
    def save_market_data(self) -> None:
        """Save current market state to JSON - now schedules async save"""
        # Mark as dirty and let background task handle it
        self._mark_dirty()
        
        # If we're in an async context, schedule immediate background save
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_save_market_data())
        except RuntimeError:
            # Not in async context, do synchronous save
            self._sync_save_market_data()
    
    def _sync_save_market_data(self) -> None:
        """Synchronous save for non-async contexts"""
        market_data = {
            "categories": self.categories,
            "etfs": self.etfs,
            "market_caps": self.market_caps,
            "market_params": self.market_params,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "trading_state": {
                "is_trading_day": self.is_trading_day,
                "current_trading_day": self.current_trading_day,
                "stocks_channel_id": self.stocks_channel_id,
                "admin_only_trading": self.admin_only_trading,
                "price_update_rate_minutes": self.price_update_rate_minutes,
                "market_open_time": self.market_open_time.isoformat() if self.market_open_time else None,
                "last_market_open_time": self.last_market_open_time
            },
            "precomputed_prices": self.precomputed_prices,
            "daily_ranges": self.daily_ranges
        }
        
        with open(self.data_dir / "market_data.json", 'w') as f:
            json.dump(market_data, f, indent=2)
    
    async def _async_save_market_data(self) -> None:
        """Async save that runs in background after UI response"""
        await asyncio.sleep(0.1)  # Small delay to ensure UI responds first
        
        market_data = {
            "categories": self.categories,
            "etfs": self.etfs,
            "market_caps": self.market_caps,
            "market_params": self.market_params,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "trading_state": {
                "is_trading_day": self.is_trading_day,
                "current_trading_day": self.current_trading_day,
                "stocks_channel_id": self.stocks_channel_id,
                "admin_only_trading": self.admin_only_trading,
                "price_update_rate_minutes": self.price_update_rate_minutes,
                "market_open_time": self.market_open_time.isoformat() if self.market_open_time else None,
                "last_market_open_time": self.last_market_open_time
            },
            "precomputed_prices": self.precomputed_prices,
            "daily_ranges": self.daily_ranges
        }
        
        # Write to temp file first for atomicity
        temp_file = self.data_dir / "market_data.tmp"
        with open(temp_file, 'w') as f:
            json.dump(market_data, f, indent=2)
        
        # Atomic rename
        temp_file.replace(self.data_dir / "market_data.json")
        self._memory_dirty = False
        self._last_checkpoint = datetime.now(timezone.utc)
    
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
                self.admin_only_trading = state.get("admin_only_trading", False)
                self.price_update_rate_minutes = state.get("price_update_rate_minutes", 60)
                self.last_market_open_time = state.get("last_market_open_time") or data.get("last_updated")
                if state.get("market_open_time"):
                    self.market_open_time = datetime.fromisoformat(state["market_open_time"])
                else:
                    self.market_open_time = None
            if "precomputed_prices" in data:
                self.precomputed_prices = data["precomputed_prices"]
            if "daily_ranges" in data:
                self.daily_ranges = data["daily_ranges"]
            if "etfs" in data:
                self.etfs = data["etfs"]
            if "market_caps" in data:
                self.market_caps = data["market_caps"]
            
            # Initialize ETF attributes after loading
            self._initialize_etf_attributes()
            
            print("📊 Market data loaded successfully")
            if self.precomputed_prices:
                print(f"✅ Loaded {len(self.precomputed_prices)} precomputed price series")
            return True
            
        except Exception as e:
            print(f"❌ Error loading market data: {e}")
            return False
    
    # Memory-First Architecture Methods
    def _mark_dirty(self) -> None:
        """Mark memory state as needing save"""
        self._memory_dirty = True
    
    def _setup_signal_handlers(self) -> None:
        """Handle SIGINT/SIGTERM for clean shutdown"""
        def emergency_save(signum, frame):
            print("📊 Emergency save triggered by signal...")
            self._emergency_save_sync()
            print("🔄 Exiting after emergency save...")
            import sys
            sys.exit(0)
            
        signal.signal(signal.SIGINT, emergency_save)
        signal.signal(signal.SIGTERM, emergency_save)
    
    def _emergency_save_sync(self) -> None:
        """Blocking save for emergency shutdown"""
        try:
            print("💾 Performing emergency save...")
            market_data = {
                "categories": self.categories,
                "etfs": self.etfs,
                "market_caps": self.market_caps,
                "market_params": self.market_params,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "trading_state": {
                    "is_trading_day": self.is_trading_day,
                    "current_trading_day": self.current_trading_day,
                    "stocks_channel_id": self.stocks_channel_id,
                    "admin_only_trading": self.admin_only_trading,
                    "price_update_rate_minutes": self.price_update_rate_minutes,
                    "market_open_time": self.market_open_time.isoformat() if self.market_open_time else None,
                    "last_market_open_time": self.last_market_open_time
                },
                "precomputed_prices": self.precomputed_prices,
                "daily_ranges": self.daily_ranges
            }
            
            # Direct synchronous write
            with open(self.data_dir / "market_data.json", 'w') as f:
                json.dump(market_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            print("✅ Emergency save completed")
        except Exception as e:
            print(f"❌ Emergency save failed: {e}")
    
    async def _checkpoint_loop(self) -> None:
        """Periodically save memory to disk"""
        while True:
            try:
                await asyncio.sleep(30)  # Every 30 seconds
                
                if self._memory_dirty:
                    print("📊 Checkpoint: Saving market data...")
                    await self._async_save_market_data()
                    print("✅ Checkpoint save completed")
                    
            except asyncio.CancelledError:
                # Final save on shutdown
                if self._memory_dirty:
                    print("📊 Final checkpoint save...")
                    await self._async_save_market_data()
                raise
            except Exception as e:
                print(f"⚠️ Checkpoint save error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def save_historical_data(self, timestamp: str, data: Dict[str, Any]) -> None:
        """Save historical price data - now deferred"""
        # Schedule async save if in async context
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_save_historical_data(timestamp, data))
        except RuntimeError:
            # Not in async context, do synchronous save
            self._sync_save_historical_data(timestamp, data)
    
    def _sync_save_historical_data(self, timestamp: str, data: Dict[str, Any]) -> None:
        """Synchronous historical save"""
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
    
    async def _async_save_historical_data(self, timestamp: str, data: Dict[str, Any]) -> None:
        """Async historical save that runs in background"""
        await asyncio.sleep(0.1)  # Small delay to ensure UI responds first
        
        history_file = self.data_dir / "stock_history.json"
        history = []
        
        if history_file.exists():
            with open(history_file, 'r') as f:
                history = json.load(f)
        
        history.append({
            "timestamp": timestamp,
            "data": data
        })
        
        # Keep last 10000 entries
        history = history[-10000:]
        
        # Write to temp file first
        temp_file = self.data_dir / "stock_history.tmp"
        with open(temp_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        # Atomic rename
        temp_file.replace(self.data_dir / "stock_history.json")
    
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
    
    def clear_price_history(self) -> bool:
        """Clear all stock price history"""
        try:
            history_file = self.data_dir / "stock_history.json"
            if history_file.exists():
                history_file.unlink()
                print("✅ Stock price history cleared")
                return True
            else:
                print("ℹ️ No price history to clear")
                return True
        except Exception as e:
            print(f"❌ Error clearing price history: {e}")
            return False
    
    def _get_sector_rotation_factor(self, sector_name: str) -> float:
        """Get sector-specific rotation multiplier"""
        sector_factors = {
            "TECH": 1.3,         # High rotation sensitivity
            "FINANCE": 1.1,      # Moderate rotation sensitivity
            "ENERGY": 0.9,       # Lower rotation sensitivity
            "HEALTH": 0.7,       # Stable, less affected by rotation
            "RETAIL": 1.0,       # Average rotation sensitivity
            "MANUFACTURING": 0.8, # Moderate stability
            "ENTERTAINMENT": 1.2, # Higher rotation sensitivity
            "TRANSPORT": 1.0      # Average rotation sensitivity
        }
        return sector_factors.get(sector_name, 1.0)
    
    def simulate_trading_days(self, num_days: int = 5, test_params: Optional[Dict] = None) -> Dict[str, Any]:
        """Simulate multiple trading days to test market stability"""
        print(f"🧪 Simulating {num_days} trading days for market stability testing...")
        
        simulation_results = {
            "days_simulated": num_days,
            "market_broke": False,
            "min_prices": {},
            "max_prices": {},
            "final_prices": {},
            "daily_summaries": []
        }
        
        # Store original prices
        original_prices = {}
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                original_prices[stock["symbol"]] = stock["price"]
        
        try:
            for day in range(num_days):
                print(f"📅 Simulating day {day + 1}/{num_days}")
                
                # Apply test parameters if provided
                if test_params and day == 2:  # Apply stress test on day 3
                    print(f"⚡ Applying stress test parameters: {test_params}")
                    self.market_params.update(test_params)
                
                # Use basic economic parameters for simulation (no fake analysis)
                print("⚠️ Simulation mode: Using economic data parameters without AI analysis")
                # Just use current economic parameters without generating fake data
                self.market_params = self._calculate_market_params_from_economic_data()
                
                # Generate hourly prices
                trading_day = f"2024-01-{day+1:02d}"
                hourly_prices = self.generate_hourly_prices(trading_day)
                
                # Analyze the day's results
                day_summary = {
                    "day": day + 1,
                    "market_params": self.market_params.copy(),
                    "stock_ranges": {},
                    "max_daily_change": 0.0,
                    "broke_stocks": []
                }
                
                for symbol, prices in hourly_prices.items():
                    if not prices:
                        continue
                        
                    min_price = min(prices)
                    max_price = max(prices)
                    final_price = prices[-1]
                    
                    # Track overall extremes
                    if symbol not in simulation_results["min_prices"] or min_price < simulation_results["min_prices"][symbol]:
                        simulation_results["min_prices"][symbol] = min_price
                    if symbol not in simulation_results["max_prices"] or max_price > simulation_results["max_prices"][symbol]:
                        simulation_results["max_prices"][symbol] = max_price
                    
                    simulation_results["final_prices"][symbol] = final_price
                    
                    # Check for broken stocks (too low or too high)
                    original_price = original_prices[symbol]
                    if min_price < original_price * 0.01:  # Below 1% of original
                        day_summary["broke_stocks"].append(f"{symbol}: fell to ${min_price:.4f} from ${original_price:.2f}")
                        simulation_results["market_broke"] = True
                    if max_price > original_price * 100:  # Above 100x original
                        day_summary["broke_stocks"].append(f"{symbol}: rose to ${max_price:.2f} from ${original_price:.2f}")
                        simulation_results["market_broke"] = True
                    
                    # Track daily ranges
                    daily_change = abs(max_price - min_price) / min_price
                    day_summary["stock_ranges"][symbol] = {
                        "min": min_price,
                        "max": max_price,
                        "range_pct": daily_change * 100
                    }
                    
                    if daily_change > day_summary["max_daily_change"]:
                        day_summary["max_daily_change"] = daily_change
                    
                    # Update stock price for next day
                    for cat_name, cat_data in self.categories.items():
                        for stock in cat_data["stocks"]:
                            if stock["symbol"] == symbol:
                                stock["price"] = final_price
                                break
                
                simulation_results["daily_summaries"].append(day_summary)
                
                print(f"📊 Day {day + 1} complete: Max daily change {day_summary['max_daily_change']*100:.1f}%, {len(day_summary['broke_stocks'])} broken stocks")
        
        except Exception as e:
            print(f"❌ Simulation failed on day {day + 1}: {e}")
            simulation_results["market_broke"] = True
            simulation_results["error"] = str(e)
        
        # Restore original prices
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                symbol = stock["symbol"]
                if symbol in original_prices:
                    stock["price"] = original_prices[symbol]
        
        # Summary
        if simulation_results["market_broke"]:
            print("❌ Market stability test FAILED - market broke during simulation")
        else:
            print("✅ Market stability test PASSED - market remained stable")
        
        return simulation_results
    
    
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
        
    def calculate_market_average(self) -> float:
        """Calculate overall market average price for charts"""
        all_stocks = self.get_all_stocks_flat()
        if not all_stocks:
            return 0.0
        
        total_price = sum(stock["price"] for stock in all_stocks)
        return total_price / len(all_stocks)
    
    def get_all_stocks_flat(self) -> List[Dict[str, Any]]:
        """Get all individual stocks in a flat list"""
        all_stocks = []
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                stock_copy = stock.copy()
                stock_copy["category"] = cat_name
                all_stocks.append(stock_copy)
        return all_stocks
    
    def get_all_tradeable_assets(self) -> List[Dict[str, Any]]:
        """Get all tradeable assets (stocks and ETFs) in a flat list"""
        # Start with all individual stocks
        all_assets = self.get_all_stocks_flat()
        
        # Add ETFs
        for etf_symbol, etf_data in self.etfs.items():
            etf_copy = etf_data.copy()
            etf_copy["category"] = "ETF"
            etf_copy["is_etf"] = True
            # Ensure price is current
            etf_copy["price"] = etf_copy.get("current_price", self.calculate_etf_price(etf_symbol))
            all_assets.append(etf_copy)
        
        return all_assets
    
    async def trigger_dynamic_update(self, reason: str = "Market update", send_discord_notification: bool = False, save_history: bool = True) -> Dict[str, Any]:
        """Trigger comprehensive dynamic update of all stock and ETF prices"""
        print(f"🔄 Triggering dynamic update: {reason}")
        
        # Update last market open time
        self.last_market_open_time = datetime.now(timezone.utc).isoformat()
        
        # NOTE: Removed baseline recalculation - prices should only be set by AI analysis
        
        # Recalculate all category ETF prices based on current stock prices
        category_prices = self.calculate_category_prices()
        
        # Update ETF prices
        etf_prices = {}
        for etf_symbol in self.etfs.keys():
            etf_prices[etf_symbol] = self.calculate_etf_price(etf_symbol)
            self.etfs[etf_symbol]["current_price"] = etf_prices[etf_symbol]
        
        # Save updated market data
        self.save_market_data()
        
        # Create historical snapshot
        timestamp = datetime.now(timezone.utc).isoformat()
        historical_data = {
            "individual_stocks": {symbol: stock["price"] for cat in self.categories.values() 
                                for stock in cat["stocks"] for symbol in [stock["symbol"]]},
            "category_prices": category_prices,
            "etf_prices": etf_prices,
            "market_params": self.market_params,
            "update_reason": reason,
            "dynamic_update": True
        }
        
        # Only save to history if requested (hourly updates)
        if save_history:
            self.save_historical_data(timestamp, historical_data)
        
        # Calculate summary statistics
        total_stocks = sum(len(cat['stocks']) for cat in self.categories.values())
        update_summary = {
            "reason": reason,
            "timestamp": timestamp,
            "stocks_updated": total_stocks,
            "etf_prices": category_prices,
            "market_params": self.market_params.copy(),
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
                    embed.set_footer(text=footer_text)
                    
                    await channel.send(embed=embed)
                    update_summary["notification_sent"] = True
                    print(f"✅ Dynamic update notification sent to Discord")
                
            except Exception as e:
                print(f"⚠️ Failed to send Discord notification: {e}")
        
        print(f"✅ Dynamic update complete: {total_stocks} stocks, {len(category_prices)} ETFs updated")
        return update_summary
    
    async def send_json_to_channel(self, data: Dict[str, Any], source: str = "Stock Market Analysis") -> None:
        """Send JSON analysis data to the JSON output channel"""
        try:
            if not self.client:
                print("⚠️ Discord client not available for JSON output")
                return
                
            channel = self.client.get_channel(JSON_OUTPUT_CHANNEL)
            if not channel:
                print(f"⚠️ JSON output channel {JSON_OUTPUT_CHANNEL} not found")
                return
            
            # Format the JSON with proper indentation
            json_str = json.dumps(data, indent=2)
            
            # Create embed header
            embed = discord.Embed(
                title=f"📈 {source} JSON Output",
                description=f"Full analysis data from {source}",
                color=0x00aaff,
                timestamp=datetime.now(timezone.utc)
            )
            
            # If JSON is small enough, send as code block
            if len(json_str) < 1900:
                await channel.send(embed=embed)
                await channel.send(f"```json\n{json_str}\n```")
            else:
                # Send as file attachment if too large
                json_bytes = json_str.encode('utf-8')
                file = discord.File(io.BytesIO(json_bytes), filename=f"{source.lower().replace(' ', '_')}_analysis.json")
                await channel.send(embed=embed, file=file)
            
            print(f"✅ JSON output sent to channel {JSON_OUTPUT_CHANNEL}")
            
        except Exception as e:
            print(f"❌ Failed to send JSON to channel: {e}")
    
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
    
    def set_price_update_rate(self, minutes: int) -> bool:
        """Set the price update rate in minutes
        
        Args:
            minutes: Update rate in minutes (minimum 1, maximum 1440 for daily)
            
        Returns:
            True if successful, False otherwise
        """
        if minutes < 1:
            print("❌ Update rate must be at least 1 minute")
            return False
        if minutes > 1440:
            print("❌ Update rate cannot exceed 1440 minutes (24 hours)")
            return False
            
        old_rate = self.price_update_rate_minutes
        self.price_update_rate_minutes = minutes
        
        # Save the new rate
        self.save_market_data()
        
        print(f"✅ Price update rate changed from {old_rate} minutes to {minutes} minutes")
        print(f"📊 Prices will now update every {minutes} minute{'s' if minutes != 1 else ''}")
        
        return True
    
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
    
    def calculate_etf_price(self, etf_symbol: str, target_time: datetime = None) -> float:
        """Calculate ETF price based on holdings and type"""
        if etf_symbol not in self.etfs:
            return 0.0
            
        etf = self.etfs[etf_symbol]
        
        # For sector ETFs, calculate based on sector average
        if etf["type"] == "sector":
            sector_name = etf.get("sector")
            if sector_name and sector_name in self.categories:
                total_price = 0.0
                stocks = self.categories[sector_name]["stocks"]
                for stock in stocks:
                    price = self.calculate_price_at_time(stock["symbol"], target_time) if target_time else stock.get("current_price", stock["price"])
                    total_price += price
                base_price = total_price / len(stocks) if stocks else 0.0
            else:
                base_price = etf.get("price", 100.0)
        
        # For market cap weighted ETFs
        elif etf["type"] == "market_cap_weighted":
            total_value = 0.0
            total_weight = 0.0
            
            for stock_symbol, weight in etf.get("holdings", {}).items():
                stock_price = self.get_stock_price(stock_symbol)
                if stock_price and stock_price > 0:
                    if target_time:
                        stock_price = self.calculate_price_at_time(stock_symbol, target_time)
                    total_value += stock_price * weight
                    total_weight += weight
            
            # Normalize if weights don't sum to 1
            if total_weight > 0:
                base_price = total_value / total_weight
            else:
                base_price = etf.get("price", 100.0)
        
        # For equal weighted ETFs
        elif etf["type"] == "equal_weighted":
            holdings = etf.get("holdings", {})
            if holdings:
                total_price = 0.0
                valid_holdings = 0
                
                for stock_symbol in holdings.keys():
                    stock_price = self.get_stock_price(stock_symbol)
                    if stock_price and stock_price > 0:
                        if target_time:
                            stock_price = self.calculate_price_at_time(stock_symbol, target_time)
                        total_price += stock_price
                        valid_holdings += 1
                
                if valid_holdings > 0:
                    # Equal weight means average of all holdings
                    base_price = total_price / valid_holdings
                else:
                    base_price = etf.get("price", 100.0)
            else:
                base_price = etf.get("price", 100.0)
        
        # For bond ETFs - inverse correlation with market
        elif etf["type"] == "bond":
            # Start with base price
            base_price = etf.get("price", 105.0)
            
            # Bond prices move inversely to market sentiment and volatility
            market_sentiment = self.market_params.get("market_sentiment", 0.5)
            market_volatility = self.market_params.get("volatility", 0.5)
            
            # Higher market sentiment = lower bond prices (inverse relationship)
            sentiment_factor = 1.0 - (market_sentiment - 0.5) * 0.1
            
            # Higher volatility = higher bond prices (flight to safety)
            volatility_factor = 1.0 + (market_volatility - 0.5) * 0.05
            
            base_price = base_price * sentiment_factor * volatility_factor
        
        # For commodity ETFs
        elif etf["type"] == "commodity":
            # Calculate based on holdings (weighted average of commodity-related stocks)
            holdings = etf.get("holdings", {})
            if holdings:
                total_value = 0.0
                total_weight = 0.0
                
                for stock_symbol, weight in holdings.items():
                    stock_price = self.get_stock_price(stock_symbol)
                    if stock_price and stock_price > 0:
                        if target_time:
                            stock_price = self.calculate_price_at_time(stock_symbol, target_time)
                        total_value += stock_price * weight
                        total_weight += weight
                
                if total_weight > 0:
                    base_price = total_value / total_weight
                else:
                    base_price = etf.get("price", 30.0)
            else:
                base_price = etf.get("price", 30.0)
        
        else:
            base_price = etf.get("price", 100.0)
        
        # Apply expense ratio (reduces returns slightly)
        expense_ratio = etf.get("expense_ratio", 0.001)
        daily_expense = expense_ratio / 365
        base_price = base_price * (1 - daily_expense)
        
        # If calculating at a specific time, apply volatility-adjusted noise
        if target_time:
            return self._apply_etf_volatility(etf_symbol, base_price, target_time)
        
        return base_price
    
    def _apply_etf_volatility(self, etf_symbol: str, base_price: float, target_time: datetime) -> float:
        """Apply volatility to ETF price using Perlin noise"""
        etf = self.etfs.get(etf_symbol, {})
        volatility_modifier = etf.get("volatility_modifier", 0.7)
        
        # Use similar noise calculation as stocks but with reduced volatility
        now = datetime.now(timezone.utc)
        hours_elapsed = (target_time - datetime(2025, 1, 1, tzinfo=timezone.utc)).total_seconds() / 3600
        
        # Get market parameters
        market_volatility = self.market_params.get("volatility", 0.5)
        
        # Use ETF symbol as seed for consistency
        seed = sum(ord(c) for c in etf_symbol) * 1000
        
        # Generate multi-scale noise
        weekly_noise = self.perlin_noise(hours_elapsed / 168, seed)
        daily_noise = self.perlin_noise(hours_elapsed / 24, seed + 1000)
        hourly_noise = self.perlin_noise(hours_elapsed, seed + 2000)
        
        # Combine with ETF-specific weights (less volatile than stocks)
        combined_noise = (
            weekly_noise * 0.5 +    # More weight on longer-term trends
            daily_noise * 0.3 +
            hourly_noise * 0.2
        )
        
        # Apply volatility with ETF modifier
        volatility_factor = market_volatility * volatility_modifier * 0.02  # Max 2% daily move
        
        # Handle inverse correlation for bond ETFs
        if etf.get("inverse_correlation", False):
            # Bond ETFs move opposite to market noise
            price_change = -combined_noise * volatility_factor * 0.5  # Reduced movement for bonds
        else:
            price_change = combined_noise * volatility_factor
        
        # Apply daily ranges if available
        daily_low = etf.get("daily_range_low", base_price * 0.98)
        daily_high = etf.get("daily_range_high", base_price * 1.02)
        
        final_price = base_price * (1 + price_change)
        
        # Soft cap within daily ranges
        if self.softcap_config["enabled"]:
            if final_price > daily_high:
                excess = (final_price - daily_high) / daily_high
                resistance = 1 / (1 + self.softcap_config["steepness"] * excess)
                final_price = daily_high + (final_price - daily_high) * (1 - resistance * self.softcap_config["max_resistance"])
            elif final_price < daily_low:
                deficit = (daily_low - final_price) / daily_low
                resistance = 1 / (1 + self.softcap_config["steepness"] * deficit)
                final_price = daily_low - (daily_low - final_price) * (1 - resistance * self.softcap_config["max_resistance"])
        
        return round(final_price, 2)
    
    def precompute_etf_prices(self) -> None:
        """Precompute and cache all ETF prices for the trading day"""
        try:
            print("🔄 Precomputing ETF prices for the trading day...")
            start_time = datetime.now(timezone.utc)
            
            # Clear existing cache
            self.etf_price_cache = {}
            
            # Set cache expiry to 9 AM ET next day
            from zoneinfo import ZoneInfo
            et_now = datetime.now(ZoneInfo("America/New_York"))
            tomorrow_9am = (et_now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            self.etf_cache_expiry = tomorrow_9am
            
            # Calculate and cache prices for all ETFs
            for symbol in self.etfs:
                price = self.calculate_etf_price(symbol)
                self.etf_price_cache[symbol] = {
                    'price': price,
                    'timestamp': datetime.now(timezone.utc)
                }
                # Also update the ETF's current_price field
                self.etfs[symbol]['current_price'] = price
            
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"✅ Precomputed {len(self.etf_price_cache)} ETF prices in {elapsed:.2f} seconds")
            print(f"📅 Cache valid until {tomorrow_9am.strftime('%Y-%m-%d %I:%M %p ET')}")
            
        except Exception as e:
            print(f"❌ Error precomputing ETF prices: {e}")
            import traceback
            traceback.print_exc()
    
    def get_cached_etf_price(self, symbol: str) -> Optional[float]:
        """Get ETF price from cache or calculate if needed"""
        try:
            # Check if cache exists and is not expired
            from zoneinfo import ZoneInfo
            if self.etf_cache_expiry and datetime.now(ZoneInfo("America/New_York")) < self.etf_cache_expiry:
                if symbol in self.etf_price_cache:
                    return self.etf_price_cache[symbol]['price']
            
            # Cache miss or expired - calculate fresh price
            price = self.calculate_etf_price(symbol)
            
            # Update cache
            self.etf_price_cache[symbol] = {
                'price': price,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Also update the ETF's current_price field
            if symbol in self.etfs:
                self.etfs[symbol]['current_price'] = price
            
            return price
            
        except Exception as e:
            print(f"❌ Error getting cached ETF price for {symbol}: {e}")
            # Fallback to direct calculation
            return self.calculate_etf_price(symbol)
    
    def get_etf_price(self, symbol: str) -> Optional[float]:
        """Get current ETF price"""
        if symbol in self.etfs:
            etf = self.etfs[symbol]
            # Return current price if available, otherwise calculate
            return etf.get("current_price", self.calculate_etf_price(symbol))
        return None
    
    def calculate_price_at_time(self, symbol: str, target_time: datetime = None) -> float:
        """Calculate stock price at any given time using multi-scale Perlin noise
        
        This system operates on multiple time scales:
        - Weekly trends (economic report driven)
        - Multi-day trends (economic report driven) 
        - Daily movements (day-specific)
        - Intraday fluctuations (day-specific)
        
        Args:
            symbol: Stock symbol
            target_time: Time to calculate price for (defaults to current time)
            
        Returns:
            Calculated price at the specified time
        """
        # Use current time if not specified
        if target_time is None:
            target_time = datetime.now(timezone.utc)
            
        # Find the stock
        stock = None
        cat_name = None
        for cname, cat_data in self.categories.items():
            for s in cat_data["stocks"]:
                if s["symbol"] == symbol:
                    stock = s
                    cat_name = cname
                    break
            if stock:
                break
                
        if not stock:
            raise ValueError(f"Stock {symbol} not found")
            
        # Get market open time for today
        if self.market_open_time is None:
            # Set market open to 9 AM ET of current day
            et_now = datetime.now(timezone.utc).replace(hour=14, minute=0, second=0, microsecond=0)  # 9 AM ET = 14:00 UTC
            self.market_open_time = et_now.replace(hour=14, minute=0, second=0, microsecond=0)
            
        # Calculate various time scales
        time_elapsed = (target_time - self.market_open_time).total_seconds()
        hours_elapsed = time_elapsed / 3600.0  # Hours since market open
        days_elapsed = time_elapsed / 86400.0  # Days since market open
        weeks_elapsed = time_elapsed / 604800.0  # Weeks since market open
        
        # FIX 0.2: ALWAYS USE AI OPENING PRICE AS BASE
        # ALWAYS use AI opening price as base for time calculations
        if "ai_opening_price" in stock and stock["ai_opening_price"]:
            opening_price = stock["ai_opening_price"]  # ALWAYS USE AI OPENING
        elif symbol in self.daily_ranges and "open_price" in self.daily_ranges[symbol]:
            opening_price = self.daily_ranges[symbol]["open_price"]  # Fallback
        else:
            # CRITICAL ERROR - no AI opening price!
            raise ValueError(f"No AI opening price for {symbol} - daily analysis failed")
        
        # Generate seeds for different time scales
        trading_day = self.current_trading_day or target_time.strftime("%Y-%m-%d")
        
        # Economic report seed (weekly trends) - changes only with economic reports
        economic_seed = hash(symbol + "economic_2024") % 10000
        
        # Daily seeds for shorter-term movements
        daily_seed = hash(symbol + trading_day) % 10000
        
        # MULTI-SCALE PERLIN NOISE SYSTEM
        # Scale 1: Weekly macro trends (40% weight) - economic report driven
        weekly_noise = self.perlin_noise(weeks_elapsed * 2.0, economic_seed)
        
        # Scale 2: Multi-day trends (30% weight) - economic report driven  
        multiday_noise = self.perlin_noise(days_elapsed * 0.8, economic_seed + 1000)
        
        # Scale 3: Daily movements (20% weight) - day specific
        daily_noise = self.perlin_noise(hours_elapsed * 0.3, daily_seed + 2000)
        
        # Scale 4: Intraday fluctuations (10% weight) - day specific
        intraday_noise = self.perlin_noise(hours_elapsed * 2.0, daily_seed + 3000)
        
        # Combine noise layers with proper weights
        combined_noise = (
            weekly_noise * 0.4 + 
            multiday_noise * 0.3 + 
            daily_noise * 0.2 + 
            intraday_noise * 0.1
        )
        
        # MUCH LARGER BASE VOLATILITY for realistic movements
        base_volatility = 0.008 + (self.market_params["volatility"] * 0.035)  # 0.8% to 4.3% base
        
        # Get invisible factors
        invisible = self.invisible_factors
        
        # SIGNIFICANTLY STRONGER TREND COMPONENT
        # Normal market should do 4-5% monthly = ~1% weekly = ~0.14% daily
        trend_strength = self.market_params["momentum"] * 0.7 + 0.3  # 0.3 to 1.0
        trend_component = self.market_params["trend_direction"] * 0.0012 * hours_elapsed * trend_strength
        
        # Long-term economic drift (operates over weeks/months)
        economic_drift = self.market_params["trend_direction"] * 0.0004 * days_elapsed
        
        # Volatility adjustments (more dramatic)
        liquidity_adj = (2.0 - invisible["liquidity_factor"]) * 0.8  # Increased impact
        risk_adj = (1.0 - invisible["risk_appetite"]) * 0.6  # Increased impact
        volatility_multiplier = base_volatility * (1.0 + liquidity_adj + risk_adj)
        
        # Market factors with increased impact
        institutional_component = invisible["institutional_flow"] * 0.003 * abs(combined_noise)  # 3x stronger
        news_amplifier = 1.0 + (invisible["news_velocity"] * 0.8 * abs(combined_noise))  # Stronger amplification
        sector_flow = invisible["sector_rotation"] * self._get_sector_rotation_factor(cat_name) * 0.002  # 2.5x stronger
        sentiment_bias = (self.market_params["market_sentiment"] - 0.5) * 0.006  # 3x stronger
        
        # Calculate total price change with much larger scale
        base_change = combined_noise * volatility_multiplier * news_amplifier
        total_change = (
            base_change + 
            trend_component + 
            economic_drift +
            institutional_component + 
            sector_flow + 
            sentiment_bias
        )
        
        # Apply change to opening price
        calculated_price = opening_price * (1 + total_change)
        
        # Wider daily ranges to allow for larger movements
        if symbol in self.daily_ranges:
            range_low = self.daily_ranges[symbol]["low"] 
            range_high = self.daily_ranges[symbol]["high"]
        else:
            # Much wider default range based on volatility
            range_multiplier = 0.05 + (self.market_params["volatility"] * 0.15)  # 5% to 20% daily range
            range_low = opening_price * (1 - range_multiplier)
            range_high = opening_price * (1 + range_multiplier)
        
        # SOFTCAP SYSTEM: Progressive resistance instead of hard clamping
        # Allows prices to move beyond AI ranges but with increasing resistance
        if self.softcap_config["enabled"]:
            softcap_steepness = self.softcap_config["steepness"]
            max_resistance = self.softcap_config["max_resistance"]
        
            if calculated_price < range_low:
                # Price is below the AI range
                distance_ratio = (range_low - calculated_price) / range_low
                # Exponential resistance: starts gentle, increases rapidly
                resistance_factor = 1 - (1 - math.exp(-softcap_steepness * distance_ratio)) * max_resistance
                # Apply resistance: pull price back towards range boundary
                calculated_price = range_low - (range_low - calculated_price) * resistance_factor
            elif calculated_price > range_high:
                # Price is above the AI range
                distance_ratio = (calculated_price - range_high) / range_high
                # Exponential resistance: starts gentle, increases rapidly  
                resistance_factor = 1 - (1 - math.exp(-softcap_steepness * distance_ratio)) * max_resistance
                # Apply resistance: pull price back towards range boundary
                calculated_price = range_high + (calculated_price - range_high) * resistance_factor
        else:
            # Fallback to old hard clamping if softcaps disabled
            if calculated_price < range_low:
                overshoot = (range_low - calculated_price) / range_low
                if overshoot > 0.02:
                    calculated_price = range_low * (1 - 0.02)
            elif calculated_price > range_high:
                overshoot = (calculated_price - range_high) / range_high
                if overshoot > 0.02:
                    calculated_price = range_high * (1 + 0.02)
        
        # Final safety check
        calculated_price = max(calculated_price, 0.01)
        
        return calculated_price
    
    def get_stock_price(self, symbol: str) -> Optional[float]:
        """Get current price for a stock using on-demand calculation
        
        When any stock price is fetched, update ALL stock current prices
        to ensure consistency across the market.
        """
        try:
            # Update all stock prices to current time
            current_time = datetime.now(timezone.utc)
            for category_name, category_data in self.categories.items():
                for stock in category_data["stocks"]:
                    try:
                        stock["current_price"] = self.calculate_price_at_time(stock["symbol"], current_time)
                    except:
                        # Keep existing price if calculation fails
                        pass
            
            # Update ETF prices too (but not during initialization or ETF calculation to prevent infinite loop)
            if (hasattr(self, 'etfs') and 
                not getattr(self, '_initializing', False) and 
                not getattr(self, '_calculating_etf_prices', False)):
                self._calculating_etf_prices = True
                try:
                    for etf_symbol in self.etfs:
                        try:
                            self.etfs[etf_symbol]["current_price"] = self.calculate_etf_price(etf_symbol, current_time)
                        except:
                            pass
                finally:
                    self._calculating_etf_prices = False
            
            # Return the requested stock's price
            return self.calculate_price_at_time(symbol, current_time)
        except ValueError:
            return None
    
    
    def generate_hourly_prices(self, trading_day: str) -> Dict[str, List[float]]:
        """Generate sophisticated hourly prices using AI parameters, invisible factors, and multi-layer Perlin noise"""
        print(f"📊 Generating AI-driven hourly prices for {trading_day}")
        
        # 24/7 trading: 24 hours = 24 price points (one per hour)
        hours = 24  # 00:00, 01:00, 02:00, ..., 23:00
        
        hourly_prices = {}
        
        # Get invisible factors for complex price modeling
        invisible = getattr(self, 'invisible_factors', {
            "institutional_flow": 0.0,
            "liquidity_factor": 0.7,
            "news_velocity": 0.5,
            "sector_rotation": 0.0,
            "risk_appetite": 0.5
        })
        
        # Calculate base volatility from market parameters (more dynamic range)
        base_volatility = 0.002 + (self.market_params["volatility"] * 0.008)  # 0.2% to 1.0% base
        
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                symbol = stock["symbol"]
                opening_price = stock["price"]  # AI-set opening price
                
                # Get AI-provided daily range or calculate default
                range_low = stock.get("daily_range_low", opening_price * 0.97)
                range_high = stock.get("daily_range_high", opening_price * 1.03)
                sector_factor = stock.get("sector_factor", 1.0)
                
                prices = [opening_price]  # Start with AI-set opening price
                
                # Use multiple noise seeds for complex layered movement
                base_seed = hash(symbol + trading_day) % 10000
                trend_seed = (base_seed + 1000) % 10000
                micro_seed = (base_seed + 2000) % 10000
                
                for hour in range(1, hours):
                    # Layer 1: Primary trend noise (slower, bigger movements)
                    primary_noise = self.perlin_noise(hour * 0.3, base_seed)
                    
                    # Layer 2: Secondary trend (medium frequency)
                    secondary_noise = self.perlin_noise(hour * 0.8, trend_seed)
                    
                    # Layer 3: Micro movements (high frequency, small amplitude)
                    micro_noise = self.perlin_noise(hour * 2.0, micro_seed)
                    
                    # Combine noise layers with different weights
                    combined_noise = (primary_noise * 0.6) + (secondary_noise * 0.3) + (micro_noise * 0.1)
                    
                    # Apply market parameters with sophisticated modeling
                    
                    # Trend component: stronger effect based on momentum
                    trend_strength = self.market_params["momentum"] * 0.5 + 0.2  # 0.2 to 0.7
                    trend_component = self.market_params["trend_direction"] * 0.0015 * hour * trend_strength
                    
                    # Volatility: affected by liquidity and risk appetite
                    liquidity_adj = (2.0 - invisible["liquidity_factor"]) * 0.5  # Low liquidity = higher volatility
                    risk_adj = (1.0 - invisible["risk_appetite"]) * 0.3  # Low risk appetite = higher volatility
                    volatility_multiplier = base_volatility * sector_factor * (1.0 + liquidity_adj + risk_adj)
                    
                    # Institutional flow effect (affects larger movements)
                    institutional_component = invisible["institutional_flow"] * 0.001 * abs(combined_noise)
                    
                    # News velocity effect (amplifies sudden movements)
                    news_amplifier = 1.0 + (invisible["news_velocity"] * 0.5 * abs(combined_noise))
                    
                    # Sector rotation effect
                    sector_flow = invisible["sector_rotation"] * self._get_sector_rotation_factor(cat_name) * 0.0008
                    
                    # Sentiment bias (affects direction probability)
                    sentiment_bias = (self.market_params["market_sentiment"] - 0.5) * 0.002
                    
                    # Calculate final price change
                    base_change = combined_noise * volatility_multiplier * news_amplifier
                    total_change = (
                        base_change + 
                        trend_component + 
                        institutional_component + 
                        sector_flow + 
                        sentiment_bias
                    )
                    
                    # Apply change to previous price
                    new_price = prices[-1] * (1 + total_change)
                    
                    # SOFTCAP SYSTEM: Apply progressive resistance instead of hard limits
                    if self.softcap_config["enabled"]:
                        softcap_steepness = self.softcap_config["steepness"]
                        max_resistance = self.softcap_config["max_resistance"]
                        
                        if new_price < range_low:
                            # Price is below the AI range
                            distance_ratio = (range_low - new_price) / range_low
                            resistance_factor = 1 - (1 - math.exp(-softcap_steepness * distance_ratio)) * max_resistance
                            new_price = range_low - (range_low - new_price) * resistance_factor
                        elif new_price > range_high:
                            # Price is above the AI range
                            distance_ratio = (new_price - range_high) / range_high
                            resistance_factor = 1 - (1 - math.exp(-softcap_steepness * distance_ratio)) * max_resistance
                            new_price = range_high + (new_price - range_high) * resistance_factor
                    else:
                        # Fallback to old hard clamping if softcaps disabled
                        new_price = max(new_price, range_low)
                        new_price = min(new_price, range_high)
                    
                    # Hourly change limits based on volatility (secondary constraint)
                    max_hourly_change = prices[-1] * volatility_multiplier * 3.0  # 3x volatility as max hourly
                    if abs(new_price - prices[-1]) > max_hourly_change:
                        if new_price > prices[-1]:
                            new_price = prices[-1] + max_hourly_change
                        else:
                            new_price = prices[-1] - max_hourly_change
                    
                    # Final safety check: ensure price doesn't become unrealistic
                    new_price = max(new_price, 0.01)  # Can't go below 1 cent
                    
                    prices.append(new_price)
                
                hourly_prices[symbol] = prices
        
        print(f"✅ Generated sophisticated AI-driven price movements for {len(hourly_prices)} stocks")
        return hourly_prices
    
    async def get_daily_market_analysis(self) -> Dict[str, Any]:
        """Use AI to analyze recent channel activity and set market parameters with retry logic and logging"""
        print("🧠 Running AI market analysis...")
        
        # Create analysis log file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = self.data_dir / "analysis_logs" / f"daily_market_analysis_{timestamp}.txt"
        log_file.parent.mkdir(exist_ok=True)
        
        def log_to_file(message: str):
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}\n")
        
        log_to_file("=== DAILY MARKET ANALYSIS SESSION START ===")
        log_to_file(f"Analysis timestamp: {timestamp}")
        
        if not self.client:
            error_msg = "Discord client not available for market analysis"
            print(f"❌ {error_msg}")
            log_to_file(f"ERROR: {error_msg}")
            log_to_file("CRITICAL: Cannot operate without Discord client for intelligent analysis")
            raise Exception("Stock market requires Discord client for intelligent data collection")
        
        # STEP 1: Initialize from base parameters calculated from economic data
        log_to_file("STEP 1: Calculating base parameters from economic data")
        try:
            base_params = self._calculate_market_params_from_economic_data()
            log_to_file(f"Base parameters: {json.dumps(base_params, indent=2)}")
            print("📊 Base parameters calculated from economic data")
        except Exception as e:
            error_msg = f"Failed to calculate base parameters: {e}"
            print(f"❌ {error_msg}")
            log_to_file(f"ERROR: {error_msg}")
            log_to_file("CRITICAL: Cannot operate without economic data")
            raise Exception(f"Stock market requires economic data for parameter calculation: {e}")
        
        # STEP 2: Collect Discord activity with retry logic
        log_to_file("STEP 2: Collecting Discord activity")
        max_retries = 3
        retry_count = 0
        all_messages = []
        
        while retry_count < max_retries:
            try:
                cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)
                log_to_file(f"Collecting messages from {len(ALL_ALLOWED_CHANNELS)} authorized channels (attempt {retry_count + 1})")
                
                for guild in self.client.guilds:
                    for channel in guild.text_channels:
                        if channel.name.lower() not in ALL_ALLOWED_CHANNELS:
                            continue
                        
                        if not channel.permissions_for(guild.me).read_message_history:
                            continue
                        
                        try:
                            channel_messages = []
                            async for message in channel.history(limit=50, after=cutoff_date):
                                if message.author.bot:
                                    continue
                                
                                channel_messages.append({
                                    "content": message.content[:300],
                                    "channel": channel.name,
                                    "timestamp": message.created_at.isoformat(),
                                    "author_roles": [role.name for role in getattr(message.author, 'roles', [])]
                                })
                            
                            all_messages.extend(channel_messages)
                            log_to_file(f"Collected {len(channel_messages)} messages from {channel.name}")
                            
                            if len(all_messages) >= 500:
                                break
                                
                        except Exception as e:
                            log_to_file(f"Error collecting from {channel.name}: {e}")
                            continue
                    
                    if len(all_messages) >= 500:
                        break
                
                # Success - exit retry loop
                break
                
            except Exception as e:
                retry_count += 1
                error_msg = f"Discord collection attempt {retry_count} failed: {e}"
                print(f"⚠️ {error_msg}")
                log_to_file(f"WARNING: {error_msg}")
                
                if retry_count < max_retries:
                    log_to_file(f"Retrying Discord collection...")
                    await asyncio.sleep(2)  # Wait before retry
                else:
                    log_to_file(f"All Discord collection attempts failed")
                    log_to_file("CRITICAL: Cannot operate without Discord activity data")
                    raise Exception("Stock market requires Discord activity data for intelligent analysis")
        
        all_messages = sorted(all_messages, key=lambda x: x["timestamp"], reverse=True)[:500]
        log_to_file(f"Successfully collected {len(all_messages)} messages for analysis")
        print(f"📝 Collected {len(all_messages)} messages for analysis")
        
        # STEP 3: AI Analysis with structured output and retry logic
        log_to_file("STEP 3: Running AI analysis with structured output and economic constraints")
        previous_data = self.get_previous_trading_day_data()
        
        ai_retry_count = 0
        max_ai_retries = 3
        
        while ai_retry_count < max_ai_retries:
            try:
                # Create structured output schema
                market_analysis_schema = self._create_market_analysis_schema(base_params)
                log_to_file("Created structured output schema for market analysis")
                
                # Build prompt for structured output
                analysis_prompt = self.build_structured_analysis_prompt(all_messages, previous_data, base_params)
                log_to_file(f"AI attempt {ai_retry_count + 1}: Sending structured prompt to Gemini")
                
                # Use structured output to enforce schema
                response = await self.model.generate_content_async(
                    analysis_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=3000,
                        response_mime_type="application/json",
                        response_schema=market_analysis_schema
                    )
                )
                
                log_to_file(f"Structured AI Response received ({len(response.text)} characters)")
                log_to_file("--- STRUCTURED AI RESPONSE ---")
                log_to_file(response.text)
                log_to_file("--- END STRUCTURED AI RESPONSE ---")
                
                # Parse structured output (should be valid JSON)
                parsed_result = self.parse_structured_market_analysis(response.text, base_params, log_file)
                log_to_file("✅ Structured AI analysis completed successfully")
                print("✅ AI analysis completed with structured output and retry logic")
                
                # Send JSON output to designated channel
                try:
                    # Parse the raw AI response for sending
                    ai_response_json = json.loads(response.text)
                    
                    # Create comprehensive output including both AI response and parsed result
                    comprehensive_output = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "ai_raw_response": ai_response_json,
                        "parsed_analysis": {
                            "market_params": parsed_result.get("market_params", {}),
                            "invisible_factors": parsed_result.get("invisible_factors", {}),
                            "daily_ranges": parsed_result.get("daily_ranges", {}),
                            "sector_outlooks": parsed_result.get("sector_outlooks", {})
                        },
                        "base_economic_params": base_params,
                        "messages_analyzed": len(all_messages),
                        "analysis_type": "Stock Market Daily Analysis"
                    }
                    
                    await self.send_json_to_channel(comprehensive_output, "Stock Market Analysis (Hourly)")
                    log_to_file("✅ JSON output sent to designated channel")
                except Exception as e:
                    log_to_file(f"WARNING: Failed to send JSON output: {e}")
                    print(f"⚠️ Failed to send JSON output: {e}")
                
                return parsed_result
                
            except json.JSONDecodeError as e:
                ai_retry_count += 1
                error_msg = f"AI JSON parsing failed (attempt {ai_retry_count}): {e}"
                print(f"❌ {error_msg}")
                log_to_file(f"ERROR: {error_msg}")
                
                if ai_retry_count < max_ai_retries:
                    log_to_file(f"Retrying AI analysis...")
                    await asyncio.sleep(3)  # Wait before retry
                else:
                    log_to_file("All AI analysis attempts failed")
                    log_to_file("CRITICAL: Cannot operate without AI analysis")
                    raise Exception("Stock market requires AI analysis for intelligent parameter setting")
                    
            except Exception as e:
                ai_retry_count += 1
                error_msg = f"AI analysis failed (attempt {ai_retry_count}): {e}"
                print(f"❌ {error_msg}")
                log_to_file(f"ERROR: {error_msg}")
                
                if ai_retry_count < max_ai_retries:
                    log_to_file(f"Retrying AI analysis...")
                    await asyncio.sleep(3)
                else:
                    log_to_file("All AI analysis attempts failed")
                    log_to_file("CRITICAL: Cannot operate without AI analysis")
                    raise Exception("Stock market requires AI analysis for intelligent parameter setting")
        
        # Should never reach here - all paths above either return or raise
        log_to_file("CRITICAL: Unexpected code path in AI analysis")
        raise Exception("Stock market AI analysis reached unexpected code path")
    
    
    
    def _create_market_analysis_schema(self, base_params: Dict[str, float]) -> Dict[str, Any]:
        """Create JSON schema for structured market analysis output"""
        
        # Create schema for all individual stocks
        stock_price_properties = {}
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                stock_price_properties[stock["symbol"]] = {
                    "type": "object",
                    "properties": {
                        "open_price": {"type": "number"},
                        "range_low": {"type": "number"},
                        "range_high": {"type": "number"},
                        "sector_factor": {"type": "number"}
                    },
                    "required": ["open_price", "range_low", "range_high", "sector_factor"]
                }
        
        # Create schema for sector outlook
        sector_outlook_properties = {}
        for cat_name in self.categories.keys():
            sector_outlook_properties[cat_name] = {"type": "string"}
        
        schema = {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "object",
                    "properties": {
                        "economic_assessment": {"type": "string"},
                        "parameter_justification": {"type": "string"},
                        "discord_impact": {"type": "string"},
                        "market_outlook": {"type": "string"}
                    },
                    "required": ["economic_assessment", "parameter_justification", "discord_impact", "market_outlook"]
                },
                "parameters": {
                    "type": "object",
                    "properties": {
                        "trend_direction": {"type": "number"},
                        "volatility": {"type": "number"},
                        "momentum": {"type": "number"},
                        "market_sentiment": {"type": "number"},
                        "long_term_outlook": {"type": "number"}
                    },
                    "required": ["trend_direction", "volatility", "momentum", "market_sentiment", "long_term_outlook"]
                },
                "invisible_factors": {
                    "type": "object",
                    "properties": {
                        "institutional_flow": {"type": "number"},
                        "liquidity_factor": {"type": "number"},
                        "news_velocity": {"type": "number"},
                        "sector_rotation": {"type": "number"},
                        "risk_appetite": {"type": "number"}
                    },
                    "required": ["institutional_flow", "liquidity_factor", "news_velocity", "sector_rotation", "risk_appetite"]
                },
                "daily_stock_prices": {
                    "type": "object",
                    "properties": stock_price_properties,
                    "required": list(stock_price_properties.keys())
                },
                "sector_outlook": {
                    "type": "object",
                    "properties": sector_outlook_properties,
                    "required": list(sector_outlook_properties.keys())
                }
            },
            "required": ["reasoning", "parameters", "invisible_factors", "daily_stock_prices", "sector_outlook"]
        }
        
        return schema
    
    def build_structured_analysis_prompt(self, messages: List[Dict], previous_data: Optional[Dict], base_params: Dict[str, float]) -> str:
        """Build prompt specifically for structured JSON output"""
        
        # Get current economic indicators from files
        try:
            economic_data_dir = Path("economic_data")
            
            # Read current economic data
            inflation_rate = 2.0
            market_confidence = 50.0
            gdp_change = 2.0
            unemployment_rate = 4.0
            
            inflation_file = economic_data_dir / "inflation.json"
            if inflation_file.exists():
                with open(inflation_file, 'r') as f:
                    inflation_data = json.load(f)
                if inflation_data:
                    inflation_rate = inflation_data[0]['data'].get('rate', 2.0)
            
            sentiment_file = economic_data_dir / "sentiment.json"
            if sentiment_file.exists():
                with open(sentiment_file, 'r') as f:
                    sentiment_data = json.load(f)
                if sentiment_data:
                    market_confidence = sentiment_data[0]['data'].get('market_confidence', 50.0)
            
            gdp_file = economic_data_dir / "gdp.json"
            if gdp_file.exists():
                with open(gdp_file, 'r') as f:
                    gdp_data = json.load(f)
                if gdp_data:
                    gdp_change = gdp_data[0]['data'].get('change_percent', 2.0)
            
            unemployment_file = economic_data_dir / "unemployment.json"
            if unemployment_file.exists():
                with open(unemployment_file, 'r') as f:
                    unemployment_data = json.load(f)
                if unemployment_data:
                    unemployment_rate = unemployment_data[0]['data'].get('rate', 4.0)
        
        except Exception:
            pass  # Use defaults
        
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
        
        prompt = f"""You are a financial analyst for a Virtual Congress stock market simulation. You must provide a comprehensive market analysis in the required JSON format.

**CURRENT ECONOMIC INDICATORS:**
- Inflation Rate: {inflation_rate}% (Fed target: 2.0%)
- GDP Growth: {gdp_change}% quarterly 
- Market Confidence: {market_confidence}% (neutral: 50%)
- Unemployment: {unemployment_rate}% (natural rate: 3.5-4.0%)

**BASE PARAMETERS (calculated from economic data):**
{json.dumps(base_params, indent=2)}

**PARAMETER GUIDELINES:**
- trend_direction: Should reflect GDP growth ({gdp_change}%) and economic momentum
- volatility: Should reflect inflation deviation from 2% target ({inflation_rate}% vs 2.0%)
- market_sentiment: Should align with market confidence ({market_confidence}%)
- momentum: Should reflect economic growth momentum and employment trends
- long_term_outlook: Small changes only (±0.02 from {base_params.get('long_term_outlook', 0.4):.3f})

**DISCORD ACTIVITY ANALYSIS (last 24 hours):**
Total messages analyzed: {len(messages)}
"""
        
        for cat_name, cat_messages in categorized_messages.items():
            prompt += f"\n{cat_name}: {len(cat_messages)} messages"
            if cat_messages:
                sample_content = " | ".join([msg['content'][:50] for msg in cat_messages[:2]])
                prompt += f" - Sample: {sample_content}..."
        
        prompt += f"""

**STOCK UNIVERSE (all must have prices set):**
{', '.join([f"{stock['symbol']}" for cat_data in self.categories.values() for stock in cat_data['stocks']])}

**ANALYSIS REQUIREMENTS:**
1. Set market parameters based on economic indicators and Discord activity
2. Provide specific opening prices and daily ranges for ALL 24 stocks
3. Set invisible market factors (institutional flow, liquidity, etc.)
4. Give sector-specific outlooks for all 8 sectors
5. Provide detailed reasoning for all decisions

**OUTPUT FORMAT:** The response will be automatically formatted as JSON matching the required schema. Focus on providing accurate analysis based on the economic data and Discord activity."""
        
        return prompt
    
    def parse_structured_market_analysis(self, ai_response: str, base_params: Dict[str, float], log_file) -> Dict[str, Any]:
        """Parse structured JSON output from AI"""
        
        def log_to_file(message: str):
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}\n")
        
        log_to_file("=== PARSING STRUCTURED AI ANALYSIS ===")
        
        try:
            # Parse JSON (should be valid due to structured output)
            analysis = json.loads(ai_response)
            log_to_file("✅ Structured JSON parsed successfully")
            
            # Validate parameters are present
            if "parameters" not in analysis:
                raise ValueError("Missing parameters in AI response")
            
            params = analysis["parameters"]
            log_to_file(f"AI provided parameters: {json.dumps(params, indent=2)}")
            
            # FIX 1.1: Store parameters in analysis object for proper extraction
            # Store parameters in analysis object for proper extraction
            analysis["parameters"] = {
                "trend_direction": max(-1.0, min(1.0, float(params.get("trend_direction", 0.0)))),
                "volatility": max(0.0, min(1.0, float(params.get("volatility", 0.5)))),
                "momentum": max(0.0, min(1.0, float(params.get("momentum", 0.5)))),
                "market_sentiment": max(0.0, min(1.0, float(params.get("market_sentiment", 0.5)))),
                "long_term_outlook": max(0.0, min(1.0, float(params.get("long_term_outlook", base_params.get("long_term_outlook", 0.4)))))
            }
            
            # Apply to self.market_params immediately
            self.market_params = analysis["parameters"].copy()
            log_to_file(f"Final market parameters stored in analysis: {json.dumps(analysis['parameters'], indent=2)}")
            
            # Apply invisible factors if provided
            if "invisible_factors" in analysis:
                invisible = analysis["invisible_factors"]
                self.invisible_factors = {
                    "institutional_flow": max(-1.0, min(1.0, float(invisible.get("institutional_flow", 0.0)))),
                    "liquidity_factor": max(0.0, min(1.0, float(invisible.get("liquidity_factor", 0.7)))),
                    "news_velocity": max(0.0, min(1.0, float(invisible.get("news_velocity", 0.5)))),
                    "sector_rotation": max(-1.0, min(1.0, float(invisible.get("sector_rotation", 0.0)))),
                    "risk_appetite": max(0.0, min(1.0, float(invisible.get("risk_appetite", 0.5))))
                }
                log_to_file(f"Applied invisible factors: {json.dumps(self.invisible_factors, indent=2)}")
            
            # FIX 1.2: ENSURE STOCK PRICES ARE ALWAYS APPLIED
            # CRITICAL: Daily stock prices are REQUIRED
            if "daily_stock_prices" not in analysis:
                log_to_file("❌ CRITICAL: No daily stock prices provided by AI")
                raise ValueError("AI analysis must provide daily_stock_prices for all stocks")
            
            # Validate all stocks have prices
            required_symbols = {stock["symbol"] for cat in self.categories.values() for stock in cat["stocks"]}
            provided_symbols = set(analysis["daily_stock_prices"].keys())
            missing_symbols = required_symbols - provided_symbols
            
            if missing_symbols:
                log_to_file(f"❌ CRITICAL: Missing prices for stocks: {missing_symbols}")
                raise ValueError(f"AI must provide prices for all stocks. Missing: {missing_symbols}")
            
            # Validate price data structure
            for symbol, price_data in analysis["daily_stock_prices"].items():
                required_fields = ["open_price", "range_low", "range_high", "sector_factor"]
                missing_fields = [field for field in required_fields if field not in price_data]
                if missing_fields:
                    raise ValueError(f"Stock {symbol} missing required fields: {missing_fields}")
            
            log_to_file(f"✅ Validated prices for {len(provided_symbols)} stocks")
            self._apply_ai_stock_prices(analysis["daily_stock_prices"])
            
            log_to_file("✅ Structured analysis applied successfully")
            return analysis
            
        except json.JSONDecodeError as e:
            log_to_file(f"❌ JSON parsing failed: {e}")
            log_to_file("Structured output should never fail JSON parsing")
            raise
        except Exception as e:
            log_to_file(f"❌ Error processing structured analysis: {e}")
            raise
    
    
    # REMOVED: _create_fallback_analysis_with_base_params 
    # Per CLAUDE.md principles: "NEVER fall back to fake, random, or artificially generated data"
    
    def parse_market_analysis(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response and extract market parameters, stock prices, and invisible factors"""
        import re
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                
                # Validate and clamp market parameters
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
                
                # Validate and clamp invisible factors
                if "invisible_factors" in analysis:
                    invisible = analysis["invisible_factors"]
                    invisible["institutional_flow"] = max(-1.0, min(1.0, invisible.get("institutional_flow", 0.0)))
                    invisible["liquidity_factor"] = max(0.0, min(1.0, invisible.get("liquidity_factor", 0.7)))
                    invisible["news_velocity"] = max(0.0, min(1.0, invisible.get("news_velocity", 0.5)))
                    invisible["sector_rotation"] = max(-1.0, min(1.0, invisible.get("sector_rotation", 0.0)))
                    invisible["risk_appetite"] = max(0.0, min(1.0, invisible.get("risk_appetite", 0.5)))
                    
                    # Store invisible factors for use in price generation
                    self.invisible_factors = invisible
                else:
                    # Default invisible factors if not provided
                    self.invisible_factors = {
                        "institutional_flow": 0.0,
                        "liquidity_factor": 0.7,
                        "news_velocity": 0.5,
                        "sector_rotation": 0.0,
                        "risk_appetite": 0.5
                    }
                
                # Apply daily stock prices if provided
                if "daily_stock_prices" in analysis:
                    self._apply_ai_stock_prices(analysis["daily_stock_prices"])
                    print("✅ AI-provided daily stock prices applied")
                else:
                    print("⚠️ No daily stock prices in AI response, using current prices")
                
                print("✅ AI market analysis parsed successfully")
                return analysis
            else:
                raise ValueError("No valid JSON found in AI response")
                
        except Exception as e:
            print(f"❌ Error parsing AI analysis: {e}")
            raise Exception(f"Failed to parse AI analysis: {e}")
    
    def _apply_ai_stock_prices(self, daily_prices: Dict[str, Dict[str, float]]) -> None:
        """Apply AI-provided daily stock prices and ranges"""
        print("🔄 Applying AI-provided daily stock prices...")
        
        # Clear daily ranges for new trading day
        self.daily_ranges = {}
        
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                symbol = stock["symbol"]
                if symbol in daily_prices:
                    price_data = daily_prices[symbol]
                    
                    # Validate price data
                    open_price = max(0.1, price_data.get("open_price", stock["price"]))
                    range_low = max(0.1, price_data.get("range_low", open_price * 0.95))
                    range_high = max(range_low + 0.1, price_data.get("range_high", open_price * 1.05))
                    sector_factor = max(0.1, min(3.0, price_data.get("sector_factor", 1.0)))
                    
                    # Ensure range is valid
                    if range_low > open_price:
                        range_low = open_price * 0.95
                    if range_high < open_price:
                        range_high = open_price * 1.05
                    
                    # FIX 0.1: NEVER OVERWRITE AI OPENING PRICES
                    # Store AI opening price in separate field that never changes
                    stock["ai_opening_price"] = open_price  # PRESERVE AI OPENING (NEVER CHANGES)
                    stock["price"] = open_price             # THE ONE TRUE PRICE FIELD
                    stock["daily_range_low"] = range_low
                    stock["daily_range_high"] = range_high
                    stock["sector_factor"] = sector_factor
                    
                    # Store in daily_ranges for on-demand calculation
                    self.daily_ranges[symbol] = {
                        "low": range_low,
                        "high": range_high,
                        "sector_factor": sector_factor,
                        "open_price": open_price  # Store AI-provided opening price
                    }
                    
                    print(f"📊 {symbol}: ${open_price:.2f} (${range_low:.2f}-${range_high:.2f}, factor: {sector_factor:.1f})")
                else:
                    # No AI price provided, set default range
                    stock["daily_range_low"] = stock["price"] * 0.97
                    stock["daily_range_high"] = stock["price"] * 1.03
                    stock["sector_factor"] = 1.0
                    
                    # Store in daily_ranges
                    self.daily_ranges[symbol] = {
                        "low": stock["daily_range_low"],
                        "high": stock["daily_range_high"],
                        "sector_factor": 1.0
                    }
    
    # REMOVED: get_fallback_analysis
    # Per CLAUDE.md principles: "NEVER fall back to fake, random, or artificially generated data"
    # System now raises exceptions instead of generating fallback data
    
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
        """Save daily market analysis - CRITICAL DATA, saves immediately"""
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
        
        # Write to temp file first for atomicity
        temp_file = self.data_dir / "daily_analysis.tmp"
        with open(temp_file, 'w') as f:
            json.dump(analyses, f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Force to disk immediately
        
        # Atomic rename
        temp_file.replace(analysis_file)
        
        # Also save market data immediately for critical updates
        self._sync_save_market_data()
        print("✅ Critical daily analysis saved immediately")
    
    async def get_daily_market_analysis_with_prompt(self, custom_prompt: str, previous_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhanced daily analysis with custom prompt and consistency checks"""
        print(f"🧠 Running enhanced AI market analysis with custom prompt...")
        
        if not self.client:
            print("❌ Discord client not available for market analysis")
            raise Exception("Stock market requires Discord client for intelligent data collection")
        
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
            raise Exception(f"Enhanced AI market analysis failed: {e}")
    
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
        """Apply on-demand price update - calculates prices dynamically"""
        print(f"📊 Calculating prices on-demand for update period {hour_index}")
        
        # Update all stock prices using on-demand calculation
        price_updates = {}
        
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                symbol = stock["symbol"]
                old_price = stock["price"]
                
                # FIX 0.1: Calculate new price but preserve AI opening
                # Ensure AI opening price exists
                if "ai_opening_price" not in stock:
                    raise ValueError(f"Stock {symbol} missing AI opening price - daily analysis failed")
                
                # Calculate new price on-demand
                new_price = self.calculate_price_at_time(symbol)
                
                # Update the ONE TRUE price field
                stock["price"] = new_price
                
                price_updates[symbol] = {
                    "old_price": old_price,
                    "new_price": new_price,
                    "change": new_price - old_price,
                    "change_pct": ((new_price - old_price) / old_price) * 100
                }
        
        # Calculate updated category prices
        category_prices = self.calculate_category_prices()
        
        # Update ETF prices
        etf_prices = {}
        for etf_symbol in self.etfs.keys():
            etf_prices[etf_symbol] = self.calculate_etf_price(etf_symbol)
            self.etfs[etf_symbol]["current_price"] = etf_prices[etf_symbol]
        
        # Save updated market data
        self.save_market_data()
        
        # Save historical data
        timestamp = datetime.now(timezone.utc).isoformat()
        historical_data = {
            "individual_stocks": {symbol: stock["price"] for cat in self.categories.values() 
                                for stock in cat["stocks"] for symbol in [stock["symbol"]]},
            "category_prices": category_prices,
            "etf_prices": etf_prices,
            "market_params": self.market_params,
            "trading_hour": hour_index,
            "analysis_update": True
        }
        
        self.save_historical_data(timestamp, historical_data)
        
        print(f"✅ Updated {len(price_updates)} stock prices and ETFs using on-demand calculation")
        
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
    
    def generate_stock_chart_on_demand(self, symbol: str, hours_back: int = 48) -> Optional[bytes]:
        """Generate chart using on-demand price calculation for specified hours"""
        try:
            # Calculate prices for each hour going back
            current_time = datetime.now(timezone.utc)
            prices = []
            timestamps = []
            
            # Check if this is an ETF
            is_etf = symbol in self.etfs if hasattr(self, 'etfs') else False
            
            # Generate prices at intervals based on update rate
            intervals = hours_back * (60 // self.price_update_rate_minutes)
            interval_minutes = self.price_update_rate_minutes
            
            for i in range(intervals):
                # Calculate time for this data point
                time_offset = timedelta(minutes=interval_minutes * (intervals - 1 - i))
                price_time = current_time - time_offset
                
                # Calculate price at this time
                try:
                    if is_etf:
                        price = self.calculate_etf_price(symbol, price_time)
                    else:
                        price = self.calculate_price_at_time(symbol, price_time)
                    prices.append(price)
                    timestamps.append(price_time)
                except Exception as e:
                    print(f"⚠️ Error calculating price for {symbol} at {price_time}: {e}")
                    continue
            
            if len(prices) < 2:
                return None
            
            # Generate chart with calculated prices
            return self.generate_stock_chart(symbol, prices)
            
        except Exception as e:
            print(f"❌ Error generating on-demand chart for {symbol}: {e}")
            return None
    
    def generate_market_average_chart(self, hour_index: int) -> Optional[bytes]:
        """Generate matplotlib chart for overall market average movement using historical data"""
        try:
            # Get historical data from the last 12 hours for chart
            history_file = self.data_dir / "stock_history.json"
            if not history_file.exists():
                return None
                
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            # Get recent data points for the chart (last 12 entries or hour_index + 1, whichever is smaller)
            recent_history = history[-min(12, hour_index + 1):] if history else []
            
            if len(recent_history) < 2:
                return None
            
            # Calculate market averages from historical data
            market_averages = []
            timestamps = []
            
            for entry in recent_history:
                if "individual_stocks" in entry:
                    stock_prices = list(entry["individual_stocks"].values())
                    if stock_prices:
                        avg_price = sum(stock_prices) / len(stock_prices)
                        market_averages.append(avg_price)
                        # Extract hour from timestamp for label
                        if "timestamp" in entry:
                            from datetime import datetime
                            dt = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
                            timestamps.append(dt.strftime("%H:%M"))
                        else:
                            timestamps.append(f"{len(timestamps):02d}:00")
            
            if len(market_averages) < 2:
                return None
            
            # Create figure
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Use the extracted timestamps for x-axis labels
            # Plot market average line
            ax.plot(timestamps, market_averages, linewidth=3, color='#00aaff', marker='o', markersize=5)
            
            # Calculate overall change
            if len(market_averages) > 1:
                change = market_averages[-1] - market_averages[0]
                change_pct = (change / market_averages[0]) * 100
                
                color = '#00ff88' if change >= 0 else '#ff4444'
                direction = '📈' if change >= 0 else '📉'
                
                ax.set_title(f"Market Average - {direction} ${change:+.2f} ({change_pct:+.2f}%)", 
                           fontsize=14, color=color, fontweight='bold')
            else:
                ax.set_title("Market Average", fontsize=14, color='white', fontweight='bold')
            
            # Style the chart
            ax.set_xlabel("Hours (ET) [24/7 Trading]", fontsize=10, color='lightgray')
            ax.set_ylabel("Average Price ($)", fontsize=10, color='lightgray')
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
            print(f"❌ Error generating market average chart: {e}")
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
    
    async def _generate_emergency_prices(self):
        """Generate emergency price data when no precomputed prices exist"""
        try:
            print("🚨 Generating emergency price data...")
            
            # Get current trading day
            trading_day = self.get_trading_day_id()
            
            # Run a quick AI analysis or use fallback
            try:
                analysis = await self.stock_market.get_daily_market_analysis()
                self.stock_market.save_daily_analysis(analysis)
                print("✅ Emergency AI analysis completed")
            except Exception as e:
                print(f"⚠️ Emergency AI analysis failed, using fallback: {e}")
                analysis = self.stock_market.get_fallback_analysis()
            
            # Update market parameters
            self.stock_market.market_params = analysis.get("parameters", self.stock_market.market_params)
            
            # Generate hourly prices for current day
            hourly_prices = self.stock_market.generate_hourly_prices(trading_day)
            self.stock_market.precomputed_prices = hourly_prices
            
            # Set trading day state
            self.stock_market.is_trading_day = True
            self.stock_market.current_trading_day = trading_day
            
            # Save market data
            self.stock_market.save_market_data()
            
            print(f"✅ Emergency price generation complete for {trading_day}")
            
        except Exception as e:
            print(f"❌ Emergency price generation failed: {e}")
    
    async def force_daily_initialization(self):
        """Force a complete daily market initialization"""
        try:
            print("🔄 Force initializing daily market data...")
            await self.prepare_trading_day()
            print("✅ Force daily initialization completed")
            return True
        except Exception as e:
            print(f"❌ Force daily initialization failed: {e}")
            return False
    
    async def start_scheduler(self):
        """Start the automated scheduler"""
        print("⏰ Starting stock market scheduler...")
        
        # Start daily prep task
        self.daily_prep_task = asyncio.create_task(self.daily_prep_loop())
        
        # Start hourly updates (24/7 trading - always active)
        self.hourly_update_task = asyncio.create_task(self.hourly_update_loop())
        
        # Start checkpoint loop for periodic saves
        self.stock_market._checkpoint_task = asyncio.create_task(self.stock_market._checkpoint_loop())
        
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
                
                # Wait until after market open (9 AM) to avoid re-triggering
                current_time = self.get_et_now()
                if current_time.hour == 8:  # If we're still in the 8 AM hour
                    # Calculate seconds until 9:01 AM to be safe
                    next_hour = current_time.replace(hour=9, minute=1, second=0, microsecond=0)
                    wait_seconds = (next_hour - current_time).total_seconds()
                    await asyncio.sleep(wait_seconds)
                else:
                    # Normal wait if not in the 8 AM hour
                    await asyncio.sleep(60)
                
            except Exception as e:
                print(f"❌ Error in daily prep loop: {e}")
                import traceback
                traceback.print_exc()
                
                # Wait 5 minutes before retrying
                await asyncio.sleep(300)
                
                # Check if the task should continue running
                if asyncio.current_task().cancelled():
                    print("🛑 Daily prep task was cancelled, stopping...")
                    break
    
    async def prepare_trading_day(self):
        """Run daily market analysis and update parameters (8:40 AM ET daily)"""
        trading_day = self.get_trading_day_id()
        print(f"📊 Running daily market analysis for: {trading_day} [24/7 Trading]")
        
        try:
            # FIX 0.3: Set market open time BEFORE running AI analysis
            et_now = self.get_et_now()
            self.stock_market.market_open_time = et_now.replace(hour=9, minute=0, second=0, microsecond=0)
            print(f"🕕 Market open time set BEFORE analysis: {self.stock_market.market_open_time.strftime('%I:%M %p ET')}")
            
            # Run AI analysis
            analysis = await self.stock_market.get_daily_market_analysis()
            
            # Save analysis
            self.stock_market.save_daily_analysis(analysis)
            
            # Update market parameters from analysis
            self.stock_market.market_params = analysis.get("parameters", self.stock_market.market_params)
            
            # Validate all stocks have AI opening prices
            for cat_data in self.stock_market.categories.values():
                for stock in cat_data["stocks"]:
                    if "ai_opening_price" not in stock:
                        raise ValueError(f"Stock {stock['symbol']} missing AI opening price")
            
            # AI has already set all prices - no need for baseline recalculation
            print("✅ Market parameters and prices set by AI analysis")
            
            # Set trading day state (always active for 24/7 trading)
            self.stock_market.is_trading_day = True
            self.stock_market.current_trading_day = trading_day
            self.current_hour_index = 0
            
            # Precompute ETF prices for the day
            print("📊 Precomputing ETF prices for the trading day...")
            self.stock_market.precompute_etf_prices()
            
            # Save market data
            self.stock_market.save_market_data()
            
            # Send preparation message to channel
            await self.send_daily_analysis_message(analysis)
            
            print(f"✅ Daily analysis complete for {trading_day} • 24/7 Trading continues")
            
        except Exception as e:
            print(f"❌ Error preparing trading day: {e}")
    
    async def hourly_update_loop(self):
        """Update loop based on price update rate (default hourly)"""
        while True:
            try:
                # Market is always open - no need to check trading hours
                
                # Wait until the next update period
                et_now = self.get_et_now()
                minutes_per_update = self.stock_market.price_update_rate_minutes
                
                # Calculate next update time
                current_minutes = et_now.hour * 60 + et_now.minute
                next_update_minutes = ((current_minutes // minutes_per_update) + 1) * minutes_per_update
                next_update_hour = next_update_minutes // 60
                next_update_minute = next_update_minutes % 60
                
                # Handle day rollover
                if next_update_hour >= 24:
                    next_update = (et_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    next_update = et_now.replace(hour=next_update_hour, minute=next_update_minute, second=0, microsecond=0)
                
                sleep_seconds = (next_update - et_now).total_seconds()
                
                if sleep_seconds > 0:
                    print(f"🕰️ Next price update in {sleep_seconds/60:.1f} minutes at {next_update.strftime('%I:%M %p ET')}")
                    await asyncio.sleep(sleep_seconds)
                
                # Update prices using on-demand calculation
                await self.update_prices_on_demand()
                
            except Exception as e:
                print(f"❌ Error in update loop: {e}")
                import traceback
                traceback.print_exc()
                
                # Progressive backoff: start with 5 minutes, increase on repeated failures
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
                
                # Check if the task should continue running
                if asyncio.current_task().cancelled():
                    print("🛑 Hourly update task was cancelled, stopping...")
                    break
    
    async def update_prices_on_demand(self):
        """Update stock prices using on-demand calculation"""
        et_now = self.get_et_now()
        
        # Ensure market open time is set
        if not self.stock_market.market_open_time:
            print("⚠️ Market open time not set, initializing...")
            success = await self.force_daily_initialization()
            if not success:
                print("❌ Could not initialize market, skipping update")
                return
        
        print(f"📊 Calculating stock prices on-demand at {et_now.strftime('%I:%M %p ET')} [24/7 Trading]")
        
        # Update all stock prices using on-demand calculation
        price_updates = {}
        
        for cat_data in self.stock_market.categories.values():
            for stock in cat_data["stocks"]:
                symbol = stock["symbol"]
                old_price = stock["price"]
                
                # FIX 0.1: Calculate new price but preserve AI opening
                try:
                    # Ensure AI opening price exists
                    if "ai_opening_price" not in stock:
                        raise ValueError(f"Stock {symbol} missing AI opening price - daily analysis failed")
                    
                    old_price = stock.get("price", stock["ai_opening_price"])
                    new_price = self.stock_market.calculate_price_at_time(symbol, et_now)
                    
                    # Update the ONE TRUE price field
                    stock["price"] = new_price
                    # CRITICAL: ai_opening_price is NEVER modified after being set by AI
                    
                    price_updates[symbol] = {
                        "old_price": old_price,
                        "new_price": new_price,
                        "change": new_price - old_price,
                        "change_pct": ((new_price - old_price) / old_price) * 100
                    }
                except Exception as e:
                    print(f"⚠️ Error calculating price for {symbol}: {e}")
        
        # Calculate category prices
        category_prices = self.stock_market.calculate_category_prices()
        
        # Update ETF prices
        etf_prices = {}
        for etf_symbol in self.stock_market.etfs.keys():
            etf_prices[etf_symbol] = self.stock_market.calculate_etf_price(etf_symbol)
            self.stock_market.etfs[etf_symbol]["current_price"] = etf_prices[etf_symbol]
        
        # Save historical data
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Calculate hour index for display purposes
        time_elapsed = (et_now - self.stock_market.market_open_time).total_seconds()
        hour_index = int(time_elapsed / 3600)
        
        historical_data = {
            "individual_stocks": {symbol: stock["price"] for cat in self.stock_market.categories.values() 
                                for stock in cat["stocks"] for symbol in [stock["symbol"]]},
            "category_prices": category_prices,
            "etf_prices": etf_prices,
            "market_params": self.stock_market.market_params,
            "trading_hour": hour_index,
            "update_rate_minutes": self.stock_market.price_update_rate_minutes
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
                timestamp=datetime.now(timezone.utc)
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
                timestamp=datetime.now(timezone.utc)
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
                    emoji = "⛽" if cat_name == "ENERGY" else "🎬" if cat_name == "ENTERTAINMENT" else "🏦" if cat_name == "FINANCE" else "🏥" if cat_name == "HEALTH" else "🏭" if cat_name == "MANUFACTURING" else "🛒" if cat_name == "RETAIL" else "💻" if cat_name == "TECH" else "✈️" if cat_name == "TRANSPORT" else "📊"
                    etf_text += f"{emoji} **{cat_name}**: ${price:.2f}\n"
                
                embed.add_field(name="📊 Sector ETFs", value=etf_text.strip(), inline=True)
            
            # Create and attach a chart for the overall market average
            chart_bytes = self.stock_market.generate_market_average_chart(hour_index)
            
            if chart_bytes:
                # Attach market average chart
                chart_file = discord.File(io.BytesIO(chart_bytes), filename="market_average_chart.png")
                embed.set_image(url="attachment://market_average_chart.png")
                await channel.send(embed=embed, file=chart_file)
            else:
                await channel.send(embed=embed)
            
        except Exception as e:
            print(f"❌ Error sending hourly update: {e}")

# Global scheduler instance
stock_scheduler = None

def is_scheduler_running():
    """Check if the scheduler is running and healthy"""
    global stock_scheduler
    if not stock_scheduler:
        return False
    
    # Check if tasks exist and are not done/cancelled
    daily_running = (hasattr(stock_scheduler, 'daily_prep_task') and 
                    stock_scheduler.daily_prep_task and 
                    not stock_scheduler.daily_prep_task.done() and 
                    not stock_scheduler.daily_prep_task.cancelled())
    
    hourly_running = (hasattr(stock_scheduler, 'hourly_update_task') and 
                     stock_scheduler.hourly_update_task and 
                     not stock_scheduler.hourly_update_task.done() and 
                     not stock_scheduler.hourly_update_task.cancelled())
    
    return daily_running and hourly_running

def stop_scheduler():
    """Properly stop and cleanup the scheduler"""
    global stock_scheduler
    if stock_scheduler:
        # Cancel tasks
        if hasattr(stock_scheduler, 'daily_prep_task') and stock_scheduler.daily_prep_task:
            if not stock_scheduler.daily_prep_task.done():
                stock_scheduler.daily_prep_task.cancel()
            stock_scheduler.daily_prep_task = None
            
        if hasattr(stock_scheduler, 'hourly_update_task') and stock_scheduler.hourly_update_task:
            if not stock_scheduler.hourly_update_task.done():
                stock_scheduler.hourly_update_task.cancel()
            stock_scheduler.hourly_update_task = None
        
        # Reset global scheduler
        stock_scheduler = None
        print("⏹️ Stock market scheduler stopped and cleaned up")
        return True
    return False

async def initialize_stock_market(client) -> None:
    """Initialize the stock market system"""
    global stock_scheduler
    
    print("📈 Initializing Stock Market System...")
    
    stock_market.client = client
    
    # Stop existing scheduler if running
    if is_scheduler_running():
        print("⚠️ Existing scheduler detected, stopping before initialization...")
        stop_scheduler()
    
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
    
    # Initialize scheduler only if not already running
    if not is_scheduler_running():
        stock_scheduler = StockMarketScheduler(stock_market)
        await stock_scheduler.start_scheduler()
        print("✅ Stock market scheduler initialized and started")
    else:
        print("ℹ️ Scheduler already running, skipping initialization")
    
    # Check if we need to run initial market preparation
    if not stock_market.market_open_time or not stock_market.current_trading_day:
        print("🔄 No market open time found, running daily market initialization...")
        try:
            await stock_scheduler.prepare_trading_day()
            print("✅ Daily market initialization completed")
        except Exception as e:
            print(f"⚠️ Daily market initialization failed, trying emergency fallback: {e}")
            try:
                await stock_scheduler._generate_emergency_prices()
                print("✅ Emergency fallback completed")
            except Exception as e2:
                print(f"❌ Both daily init and emergency fallback failed: {e2}")
    
    print("✅ Stock Market System ready")