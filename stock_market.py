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
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
import discord
from discord.ext import commands, tasks
from pathlib import Path
import google.generativeai as genai
from config import GEMINI_API_KEY, BOT_HELPER_CHANNEL, STOCK_DATA_DIR, JSON_OUTPUT_CHANNEL, ECONOMIC_DATA_DIR
from economic_utils import ALL_ALLOWED_CHANNELS, ALLOWED_CHANNELS

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# AIDEV-NOTE: stock-market-overview; complete system documentation
"""
====================================================================================
                        STOCK MARKET SYSTEM ARCHITECTURE
====================================================================================

OVERVIEW:
- 24/7 AI-driven stock market with 24 companies across 8 sectors
- Daily AI analysis sets opening prices based on Discord activity & economic data  
- Hourly Perlin noise generates realistic price movements from AI openings
- Full UnbelievaBoat integration for real Discord economy trading

KEY CLASSES:
1. StockMarket (line ~130): Main market engine
   - Manages stock data, AI analysis, price calculations
   - Key data: self.categories (stocks by sector), self.market_params, self.daily_ranges
   
2. StockScheduler (line ~3152): Handles timing and automation
   - Daily AI analysis at midnight ET
   - Hourly price updates via Perlin noise
   - Manages Discord notifications

CRITICAL FLOWS:

1. DAILY AI PRICE SETTING (midnight ET):
   - get_daily_market_analysis() [~1872]: Entry point for AI analysis
   - Collects Discord messages from last 24h across authorized channels
   - Sends to Gemini 2.0 with economic indicators & previous day's state
   - parse_structured_market_analysis() [~2253]: Parses AI JSON response
   - _apply_ai_stock_prices() [~2407]: VALIDATES & applies opening prices
     * Checks for stagnant prices (same as previous)
     * Checks for erratic prices (>20% change)  
     * Applies $1 random adjustment if validation fails
   - save_daily_analysis() [~2496]: Persists to daily_analysis.json

2. HOURLY PRICE UPDATES:
   - hourly_update_loop() [~3358]: Triggers every N minutes (default 60)
   - apply_hourly_price_update() [~2907]: Calculates new prices
   - calculate_price_at_time() [~1536]: PERLIN NOISE generator
     * Uses ai_opening_price as base (NEVER modified after AI sets it)
     * Multi-scale noise: weekly, daily, hourly, minute components
     * Respects daily_range_low/high set by AI
   - Saves to stock_history.json for charts

3. ETF CALCULATIONS:
   - calculate_etf_price() [~1452]: Weighted average of sector stocks
   - ETFs defined in self.etfs with sector mappings
   - Updated whenever individual stock prices change

KEY DATA STRUCTURES:

self.categories = {
    "TECH": {
        "stocks": [
            {
                "symbol": "AAPL",
                "name": "Apple Inc",
                "price": 150.00,  # Current price (changes hourly)
                "sector_factor": 1.0
            }
        ]
    }
}

self.market_params = {
    "trend_direction": 0.0,  # -1 to 1
    "volatility": 0.5,       # 0 to 1  
    "momentum": 0.5,         # 0 to 1
    "market_sentiment": 0.5, # 0 to 1
    "long_term_outlook": 0.5 # 0 to 1 (changes slowly)
}

IMPORTANT FILES:
- stock_data/market_data.json: Current market state
- stock_data/stock_history.json: Price history for charts
- stock_data/daily_analysis.json: AI analysis history
- economic_data/*.json: GDP, inflation, unemployment data

INTEGRATION POINTS:
- stock_trading.py: Handles buy/sell with UnbelievaBoat API
- stock_commands.py: Discord slash commands
- economic_engine.py: Provides economic indicators
- data_managers.py: Centralized data access layer

CRITICAL METHODS TO KNOW:
- get_daily_market_analysis() [~1872]: AI daily analysis entry
- _apply_ai_stock_prices() [~2407]: Price validation & application
- calculate_price_at_time() [~1536]: Perlin noise price generation
- trigger_dynamic_update() [~983]: Force market-wide update
- save_market_data() [~616]: Persist to JSON

AIDEV-TODO: Search for these AIDEV-NOTE tags for key locations:
- ai-price-entry-point: Where AI sets daily prices
- price-validation: Stagnant/erratic price checks
- perlin-price-calc: Hourly price generation
- hourly-trigger: Scheduler update loop
====================================================================================
"""

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
        
        # AIDEV-NOTE: perlin-params; Per-stock Perlin noise parameters set by AI
        # Initialize per-stock Perlin parameters (AI-controlled)
        self.stock_perlin_params = {}  # Will be populated with per-stock parameters
        # Default structure for each stock:
        # {
        #     "AAPL": {
        #         "trend_strength": 0.5,      # 0-1, how strong the trend is
        #         "trend_direction": 0.0,     # -1 to 1, bearish to bullish
        #         "volatility": 0.5,          # 0-1, how volatile this specific stock is
        #         "noise_scale": 1.0,         # Multiplier for Perlin noise amplitude
        #         "cycle_frequency": 1.0,     # How fast the stock cycles
        #         "sector_correlation": 1.0,  # How much it follows its sector
        #     }
        # }
        
        # On-demand pricing configuration
        self.price_update_rate_minutes = 60  # Default 60 minutes (hourly)
        
        # AIDEV-NOTE: 24-7-market; Initialize market open time to prevent warnings
        # Set to today at 9 AM ET for 24/7 market operation
        from zoneinfo import ZoneInfo
        et_now = datetime.now(ZoneInfo("America/New_York"))
        self.market_open_time = et_now.replace(hour=9, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        self.last_market_open_time = self.market_open_time.isoformat()
        
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
                "price": 450.0  # Will be calculated dynamically
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
                "price": 380.0
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
        
        # Initialize cache attributes BEFORE ETF initialization
        # Trading state (24/7 operation)
        self.is_trading_day = True  # Always trading
        self.current_trading_day = None
        self.stock_price_cache = {}  # Cache stock prices with timestamps
        self.etf_price_cache = {}  # Cache ETF prices with timestamps
        self.price_cache_expiry = None  # When to refresh the cache (9 AM ET next day)
        
        # 5-minute interval price caches
        # AIDEV-NOTE: 5min-cache; stores precomputed prices for deterministic lookups
        self.stock_price_cache_5min = {}  # {symbol: {minute_offset: price}}
        self.etf_price_cache_5min = {}    # {symbol: {minute_offset: price}}
        
        # Initialize ETF attributes (needs market_params and caches to be set first)
        self._initialize_etf_attributes()
        
        # Initialize stock attributes for AI pricing
        self._initialize_stock_attributes()
        
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
        print(f"🤖 Market parameters await AI analysis (current: neutral defaults)")
        
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
                    
                # Skip price calculation during initialization - caches aren't populated yet
                # Price calculation will be done by precompute_etf_prices after stocks are cached
        finally:
            # Clear initialization flag
            self._initializing = False
    
    def deterministic_hash(self, input_string: str) -> int:
        """Generate deterministic hash that's consistent across program runs
        
        AIDEV-NOTE: Replaces Python's hash() which is non-deterministic between runs
        """
        # Use SHA256 for deterministic hashing
        hash_bytes = hashlib.sha256(input_string.encode('utf-8')).digest()
        # Convert first 8 bytes to integer
        return int.from_bytes(hash_bytes[:8], byteorder='big')
    
    # AIDEV-NOTE: deprecated-functions-removed; AI sets all params, no formulas
    # _calculate_market_params_from_economic_data() removed - AI analysis only
    # _calculate_parameter_ranges_from_economic_data() removed - AI has full control
    
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
            "stock_perlin_params": self.stock_perlin_params,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "trading_state": {
                "is_trading_day": self.is_trading_day,
                "current_trading_day": self.current_trading_day,
                "stocks_channel_id": self.stocks_channel_id,
                "admin_only_trading": self.admin_only_trading,
                "price_update_rate_minutes": self.price_update_rate_minutes,
                "market_open_time": self.market_open_time.isoformat() if self.market_open_time else None,
                "last_market_open_time": self.last_market_open_time
            }
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
            "stock_perlin_params": self.stock_perlin_params,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "trading_state": {
                "is_trading_day": self.is_trading_day,
                "current_trading_day": self.current_trading_day,
                "stocks_channel_id": self.stocks_channel_id,
                "admin_only_trading": self.admin_only_trading,
                "price_update_rate_minutes": self.price_update_rate_minutes,
                "market_open_time": self.market_open_time.isoformat() if self.market_open_time else None,
                "last_market_open_time": self.last_market_open_time
            }
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
            # Load Perlin parameters if available
            if "stock_perlin_params" in data:
                self.stock_perlin_params = data["stock_perlin_params"]
            if "etfs" in data:
                self.etfs = data["etfs"]
            if "market_caps" in data:
                self.market_caps = data["market_caps"]
            
            # Initialize ETF attributes after loading
            self._initialize_etf_attributes()
            
            print("📊 Market data loaded successfully")
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
                "stock_perlin_params": self.stock_perlin_params,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "trading_state": {
                    "is_trading_day": self.is_trading_day,
                    "current_trading_day": self.current_trading_day,
                    "stocks_channel_id": self.stocks_channel_id,
                    "admin_only_trading": self.admin_only_trading,
                    "price_update_rate_minutes": self.price_update_rate_minutes,
                    "market_open_time": self.market_open_time.isoformat() if self.market_open_time else None,
                    "last_market_open_time": self.last_market_open_time
                }
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
                
                # Use neutral parameters for simulation (no AI analysis)
                print("⚠️ Simulation mode: Using neutral default parameters without AI analysis")
                # Use neutral defaults for testing
                self.market_params = {
                    "trend_direction": 0.0,
                    "volatility": 0.5,
                    "momentum": 0.5,
                    "market_sentiment": 0.5,
                    "long_term_outlook": 0.5
                }
                
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
            # Ensure price is current (use cached price)
            etf_copy["price"] = etf_copy.get("current_price", self.get_cached_etf_price(etf_symbol) or etf_copy.get("price", 100.0))
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
            # Use cached price to prevent recursion
            cached_price = self.get_cached_etf_price(etf_symbol)
            etf_prices[etf_symbol] = cached_price if cached_price is not None else self.etfs[etf_symbol].get("price", 100.0)
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
                "market_active": True  # 24/7 trading
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
        """Calculate ETF price based on holdings and type
        
        DEPRECATED: Only used during initialization. Use get_current_price() for runtime lookups.
        AIDEV-NOTE: deprecated-calc; causes recursion if called outside precomputation
        """
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
    
    def calculate_etf_price_from_cache(self, etf_symbol: str) -> float:
        """Calculate ETF price using only cached stock prices (for precomputation)"""
        if etf_symbol not in self.etfs:
            raise ValueError(f"ETF {etf_symbol} not found")
            
        etf = self.etfs[etf_symbol]
        
        # For sector ETFs, calculate based on sector average
        if etf["type"] == "sector":
            sector_name = etf.get("sector")
            if sector_name and sector_name in self.categories:
                total_price = 0.0
                count = 0
                stocks = self.categories[sector_name]["stocks"]
                for stock in stocks:
                    symbol = stock["symbol"]
                    if symbol in self.stock_price_cache:
                        total_price += self.stock_price_cache[symbol]['price']
                        count += 1
                if count > 0:
                    base_price = total_price / count
                else:
                    base_price = etf.get("price", 100.0)
            else:
                base_price = etf.get("price", 100.0)
        
        # For market cap weighted ETFs
        elif etf["type"] == "market_cap_weighted":
            total_value = 0.0
            total_weight = 0.0
            
            for stock_symbol, weight in etf.get("holdings", {}).items():
                if stock_symbol in self.stock_price_cache:
                    stock_price = self.stock_price_cache[stock_symbol]['price']
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
                    if stock_symbol in self.stock_price_cache:
                        stock_price = self.stock_price_cache[stock_symbol]['price']
                        total_price += stock_price
                        valid_holdings += 1
                
                if valid_holdings > 0:
                    # Equal weight means average of all holdings
                    base_price = total_price / valid_holdings
                else:
                    base_price = etf.get("price", 100.0)
            else:
                base_price = etf.get("price", 100.0)
        
        # For bond ETFs - use same logic as calculate_etf_price
        elif etf["type"] == "bond":
            base_price = etf.get("price", 105.0)
            market_sentiment = self.market_params.get("market_sentiment", 0.5)
            market_volatility = self.market_params.get("volatility", 0.5)
            sentiment_factor = 1.0 - (market_sentiment - 0.5) * 0.1
            volatility_factor = 1.0 + (market_volatility - 0.5) * 0.05
            base_price = base_price * sentiment_factor * volatility_factor
        
        # For other ETF types
        else:
            base_price = etf.get("price", 100.0)
        
        # Apply ETF-specific volatility
        etf_volatility = etf.get("volatility", 0.02)
        random_factor = 1.0 + (self.deterministic_hash(etf_symbol + str(datetime.now(timezone.utc).date())) % 100 - 50) / 5000 * etf_volatility
        
        final_price = base_price * random_factor
        
        # Apply soft caps if needed
        if hasattr(self, 'softcap_config') and self.softcap_config.get("enabled", True):
            daily_low = etf.get("daily_low", base_price * 0.95)
            daily_high = etf.get("daily_high", base_price * 1.05)
            
            if final_price < daily_low:
                undershoot = (daily_low - final_price) / daily_low
                if undershoot > 0.02:
                    resistance = min(undershoot / 0.02, 1.0)
                    final_price = daily_low - (daily_low - final_price) * (1 - resistance * self.softcap_config["max_resistance"])
            elif final_price > daily_high:
                overshoot = (final_price - daily_high) / daily_high
                if overshoot > 0.02:
                    resistance = min(overshoot / 0.02, 1.0)
                    final_price = daily_high + (final_price - daily_high) * (1 - resistance * self.softcap_config["max_resistance"])
        
        return round(final_price, 2)
    
    def precompute_all_prices(self) -> None:
        """Precompute and cache all stock and ETF prices for 5-minute intervals throughout the day"""
        try:
            print("🔄 Precomputing all prices for 5-minute intervals...")
            start_time = datetime.now(timezone.utc)
            
            # Clear all caches
            self.stock_price_cache_5min = {}
            self.etf_price_cache_5min = {}
            self.stock_price_cache = {}
            self.etf_price_cache = {}
            
            # Set cache expiry to 9 AM ET next day
            from zoneinfo import ZoneInfo
            et_now = datetime.now(ZoneInfo("America/New_York"))
            tomorrow_9am = (et_now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            self.price_cache_expiry = tomorrow_9am
            
            # Ensure market_open_time is set
            if self.market_open_time is None:
                self.market_open_time = et_now.replace(hour=9, minute=0, second=0, microsecond=0)
                print(f"⚠️ Market open time was not set, using {self.market_open_time.strftime('%I:%M %p ET')}")
            
            stock_count = 0
            etf_count = 0
            interval_count = 0
            
            # Precompute for 24 hours in 5-minute intervals (288 intervals)
            print("  📈 Computing prices for 288 intervals (24 hours × 12 intervals/hour)...")
            
            for minute_offset in range(0, 1440, 5):  # 0, 5, 10, ..., 1435
                target_time = self.market_open_time + timedelta(minutes=minute_offset)
                interval_count += 1
                
                if interval_count % 24 == 0:  # Progress every 2 hours
                    print(f"    ⏳ Progress: {interval_count}/288 intervals ({minute_offset/60:.0f} hours)")
                
                # Step 1: Calculate all stock prices for this time
                for category_data in self.categories.values():
                    for stock in category_data["stocks"]:
                        symbol = stock["symbol"]
                        try:
                            price = self.calculate_price_at_time(symbol, target_time)
                            
                            # Initialize symbol dict if needed
                            if symbol not in self.stock_price_cache_5min:
                                self.stock_price_cache_5min[symbol] = {}
                                stock_count += 1
                            
                            # Store price for this interval
                            self.stock_price_cache_5min[symbol][minute_offset] = price
                            
                            # Update current price if this is the current interval
                            if minute_offset == 0:
                                stock["current_price"] = price
                                stock["price"] = price
                                
                        except Exception as e:
                            print(f"    ❌ Error computing price for {symbol} at offset {minute_offset}: {e}")
                
                # Step 2: Calculate ETF prices using the stock prices from this interval
                for etf_symbol in self.etfs:
                    try:
                        price = self._calculate_etf_price_from_interval(etf_symbol, minute_offset)
                        
                        # Initialize ETF dict if needed
                        if etf_symbol not in self.etf_price_cache_5min:
                            self.etf_price_cache_5min[etf_symbol] = {}
                            etf_count += 1
                        
                        # Store price for this interval
                        self.etf_price_cache_5min[etf_symbol][minute_offset] = price
                        
                        # Update current price if this is the current interval
                        if minute_offset == 0:
                            self.etfs[etf_symbol]["current_price"] = price
                            
                    except Exception as e:
                        print(f"    ❌ Error computing ETF price for {etf_symbol} at offset {minute_offset}: {e}")
            
            # Also populate the legacy caches with current prices
            current_time = datetime.now(timezone.utc)
            for symbol, intervals in self.stock_price_cache_5min.items():
                if 0 in intervals:
                    self.stock_price_cache[symbol] = {
                        'price': intervals[0],
                        'timestamp': current_time
                    }
            
            for symbol, intervals in self.etf_price_cache_5min.items():
                if 0 in intervals:
                    self.etf_price_cache[symbol] = {
                        'price': intervals[0],
                        'timestamp': current_time
                    }
            
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"✅ Precomputed {stock_count} stocks × 288 intervals = {stock_count * 288:,} stock prices")
            print(f"✅ Precomputed {etf_count} ETFs × 288 intervals = {etf_count * 288:,} ETF prices")
            print(f"⏱️ Total computation time: {elapsed:.2f} seconds")
            print(f"📅 Cache valid until {tomorrow_9am.strftime('%Y-%m-%d %I:%M %p ET')}")
            
        except Exception as e:
            print(f"❌ Error precomputing prices: {e}")
            import traceback
            traceback.print_exc()
    
    def _calculate_etf_price_from_interval(self, etf_symbol: str, minute_offset: int) -> float:
        """Calculate ETF price using stock prices from a specific 5-minute interval"""
        if etf_symbol not in self.etfs:
            raise ValueError(f"ETF {etf_symbol} not found")
            
        etf = self.etfs[etf_symbol]
        
        # For sector ETFs, calculate based on sector average
        if etf["type"] == "sector":
            sector_name = etf.get("sector")
            if sector_name and sector_name in self.categories:
                total_price = 0.0
                count = 0
                stocks = self.categories[sector_name]["stocks"]
                for stock in stocks:
                    symbol = stock["symbol"]
                    if symbol in self.stock_price_cache_5min and minute_offset in self.stock_price_cache_5min[symbol]:
                        total_price += self.stock_price_cache_5min[symbol][minute_offset]
                        count += 1
                if count > 0:
                    base_price = total_price / count
                else:
                    base_price = etf.get("price", 100.0)
            else:
                base_price = etf.get("price", 100.0)
        
        # For market cap weighted ETFs
        elif etf["type"] == "market_cap_weighted":
            total_value = 0.0
            total_weight = 0.0
            
            for stock_symbol, weight in etf.get("holdings", {}).items():
                if stock_symbol in self.stock_price_cache_5min and minute_offset in self.stock_price_cache_5min[stock_symbol]:
                    stock_price = self.stock_price_cache_5min[stock_symbol][minute_offset]
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
                    if stock_symbol in self.stock_price_cache_5min and minute_offset in self.stock_price_cache_5min[stock_symbol]:
                        stock_price = self.stock_price_cache_5min[stock_symbol][minute_offset]
                        total_price += stock_price
                        valid_holdings += 1
                
                if valid_holdings > 0:
                    # Equal weight means average of all holdings
                    base_price = total_price / valid_holdings
                else:
                    base_price = etf.get("price", 100.0)
            else:
                base_price = etf.get("price", 100.0)
        
        # For bond ETFs
        elif etf["type"] == "bond":
            base_price = etf.get("price", 105.0)
            market_sentiment = self.market_params.get("market_sentiment", 0.5)
            market_volatility = self.market_params.get("volatility", 0.5)
            sentiment_factor = 1.0 - (market_sentiment - 0.5) * 0.1
            volatility_factor = 1.0 + (market_volatility - 0.5) * 0.05
            base_price = base_price * sentiment_factor * volatility_factor
        
        # For other ETF types
        else:
            base_price = etf.get("price", 100.0)
        
        # Apply ETF-specific volatility with deterministic seed
        etf_volatility = etf.get("volatility", 0.02)
        # Use minute offset as part of seed for different values at different times
        seed_string = f"{etf_symbol}_{self.current_trading_day or datetime.now(timezone.utc).strftime('%Y-%m-%d')}_{minute_offset}"
        random_factor = 1.0 + (self.deterministic_hash(seed_string) % 100 - 50) / 5000 * etf_volatility
        
        final_price = base_price * random_factor
        
        # Apply soft caps if needed
        if hasattr(self, 'softcap_config') and self.softcap_config.get("enabled", True):
            daily_low = etf.get("daily_low", base_price * 0.95)
            daily_high = etf.get("daily_high", base_price * 1.05)
            
            if final_price < daily_low:
                undershoot = (daily_low - final_price) / daily_low
                if undershoot > 0.02:
                    resistance = min(undershoot / 0.02, 1.0)
                    final_price = daily_low - (daily_low - final_price) * (1 - resistance * self.softcap_config["max_resistance"])
            elif final_price > daily_high:
                overshoot = (final_price - daily_high) / daily_high
                if overshoot > 0.02:
                    resistance = min(overshoot / 0.02, 1.0)
                    final_price = daily_high + (final_price - daily_high) * (1 - resistance * self.softcap_config["max_resistance"])
        
        return round(final_price, 2)
    
    def precompute_etf_prices(self) -> None:
        """Legacy method - redirects to precompute_all_prices"""
        self.precompute_all_prices()
    
    def get_cached_etf_price(self, symbol: str) -> Optional[float]:
        """Get ETF price from cache ONLY - never recalculate"""
        try:
            # Check if we have a cached price
            if symbol in self.etf_price_cache:
                return self.etf_price_cache[symbol]['price']
            
            # Fallback to current_price field if available
            if symbol in self.etfs:
                return self.etfs[symbol].get('current_price')
            
            # AIDEV-NOTE: No recalculation - cache only to prevent recursion
            return None
            
        except Exception as e:
            print(f"❌ Error getting cached ETF price for {symbol}: {e}")
            return None
    
    def get_etf_price(self, symbol: str) -> Optional[float]:
        """Get current ETF price from cache"""
        if symbol in self.etfs:
            # Use cached price only - no recalculation
            return self.get_cached_etf_price(symbol)
        return None
    
    def calculate_price_at_time(self, symbol: str, target_time: datetime = None) -> float:
        """Calculate stock price at any given time using Perlin noise and AI parameters
        
        AIDEV-NOTE: pure-perlin-calc; Prices generated from Perlin params only
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
        
        # Get Perlin parameters for this stock
        if symbol not in self.stock_perlin_params:
            # Use defaults if not set
            self.stock_perlin_params[symbol] = {
                "trend_strength": 0.5,
                "trend_direction": 0.0,
                "volatility": 0.5,
                "noise_scale": 1.0,
                "cycle_frequency": 1.0,
                "sector_correlation": 1.0
            }
        
        params = self.stock_perlin_params[symbol]
        
        # Use current stock price as base (or initial price if at market open)
        base_price = stock.get("price", 100.0)
        
        # Generate seeds for different time scales
        trading_day = self.current_trading_day or target_time.strftime("%Y-%m-%d")
        
        # Economic report seed (weekly trends) - changes only with economic reports
        economic_seed = self.deterministic_hash(symbol + "economic_2024") % 10000
        
        # Daily seeds for shorter-term movements
        daily_seed = self.deterministic_hash(symbol + trading_day) % 10000
        
        # MULTI-SCALE PERLIN NOISE SYSTEM with AI-controlled frequencies
        # Scale 1: Weekly macro trends (40% weight) - economic report driven
        weekly_noise = self.perlin_noise(weeks_elapsed * 2.0 * params["cycle_frequency"], economic_seed)
        
        # Scale 2: Multi-day trends (30% weight) - economic report driven  
        multiday_noise = self.perlin_noise(days_elapsed * 0.8 * params["cycle_frequency"], economic_seed + 1000)
        
        # Scale 3: Daily movements (20% weight) - day specific
        daily_noise = self.perlin_noise(hours_elapsed * 0.3 * params["cycle_frequency"], daily_seed + 2000)
        
        # Scale 4: Intraday fluctuations (10% weight) - day specific
        intraday_noise = self.perlin_noise(hours_elapsed * 2.0 * params["cycle_frequency"], daily_seed + 3000)
        
        # Combine noise layers with proper weights
        combined_noise = (
            weekly_noise * 0.4 + 
            multiday_noise * 0.3 + 
            daily_noise * 0.2 + 
            intraday_noise * 0.1
        )
        
        # Apply AI-controlled noise scale
        combined_noise *= params["noise_scale"]
        
        # Use AI-controlled volatility for this specific stock
        base_volatility = 0.005 + (params["volatility"] * 0.045)  # 0.5% to 5% range
        
        # Get invisible factors
        invisible = self.invisible_factors
        
        # Use AI-controlled trend parameters
        trend_component = params["trend_direction"] * params["trend_strength"] * 0.0015 * hours_elapsed
        
        # Long-term economic drift influenced by market-wide trend and sector correlation
        economic_drift = self.market_params["trend_direction"] * params["sector_correlation"] * 0.0004 * days_elapsed
        
        # Volatility adjustments (more dramatic)
        liquidity_adj = (2.0 - invisible["liquidity_factor"]) * 0.8  # Increased impact
        risk_adj = (1.0 - invisible["risk_appetite"]) * 0.6  # Increased impact
        volatility_multiplier = base_volatility * (1.0 + liquidity_adj + risk_adj)
        
        # Market factors with increased impact, adjusted by sector correlation
        institutional_component = invisible["institutional_flow"] * params["sector_correlation"] * 0.003 * abs(combined_noise)
        news_amplifier = 1.0 + (invisible["news_velocity"] * 0.8 * abs(combined_noise))
        sector_flow = invisible["sector_rotation"] * self._get_sector_rotation_factor(cat_name) * params["sector_correlation"] * 0.002
        sentiment_bias = (self.market_params["market_sentiment"] - 0.5) * params["sector_correlation"] * 0.006
        
        # Calculate total price change
        base_change = combined_noise * volatility_multiplier * news_amplifier
        total_change = (
            base_change + 
            trend_component + 
            economic_drift +
            institutional_component + 
            sector_flow + 
            sentiment_bias
        )
        
        # Apply change to base price
        calculated_price = base_price * (1 + total_change)
        
        # AIDEV-NOTE: extreme-price-protection; Repurposed softcap for extreme movements only
        # Extreme price protection (only for >50% daily moves)
        extreme_threshold = 0.5  # 50% daily move threshold
        price_change_ratio = abs(calculated_price - base_price) / base_price
        
        if price_change_ratio > extreme_threshold:
            # Apply progressive resistance for extreme movements
            excess_ratio = (price_change_ratio - extreme_threshold) / extreme_threshold
            resistance = 1 - math.exp(-excess_ratio * 5)  # Exponential resistance
            
            # Pull price back towards threshold
            if calculated_price > base_price:
                max_price = base_price * (1 + extreme_threshold)
                calculated_price = max_price + (calculated_price - max_price) * (1 - resistance)
            else:
                min_price = base_price * (1 - extreme_threshold)
                calculated_price = min_price - (min_price - calculated_price) * (1 - resistance)
        
        # Final safety check
        calculated_price = max(calculated_price, 0.01)
        
        return calculated_price
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get price from nearest 5-minute interval cache
        
        AIDEV-NOTE: Primary price getter - uses 5min cache for deterministic prices
        """
        try:
            # Ensure market_open_time is set
            if self.market_open_time is None:
                print(f"⚠️ Market open time not set, cannot get current price for {symbol}")
                return None
            
            # Calculate current minute offset from market open
            time_elapsed = (datetime.now(timezone.utc) - self.market_open_time).total_seconds()
            minute_offset = int(time_elapsed / 60)
            
            # Handle negative offsets (before market open)
            if minute_offset < 0:
                minute_offset = 0
            
            # Round to nearest 5-minute interval
            nearest_5min = (minute_offset // 5) * 5
            
            # Cap at 23:55 (1435 minutes)
            if nearest_5min > 1435:
                nearest_5min = 1435
            
            # Check stock cache first
            if symbol in self.stock_price_cache_5min:
                if nearest_5min in self.stock_price_cache_5min[symbol]:
                    return self.stock_price_cache_5min[symbol][nearest_5min]
                # If exact interval not found, try offset 0
                elif 0 in self.stock_price_cache_5min[symbol]:
                    return self.stock_price_cache_5min[symbol][0]
            
            # Check ETF cache
            if symbol in self.etf_price_cache_5min:
                if nearest_5min in self.etf_price_cache_5min[symbol]:
                    return self.etf_price_cache_5min[symbol][nearest_5min]
                # If exact interval not found, try offset 0
                elif 0 in self.etf_price_cache_5min[symbol]:
                    return self.etf_price_cache_5min[symbol][0]
            
            # Fallback to base price
            return self._get_base_price(symbol)
            
        except Exception as e:
            print(f"❌ Error getting current price for {symbol}: {e}")
            return None
    
    def _get_base_price(self, symbol: str) -> Optional[float]:
        """Get base price for a symbol from categories or ETFs"""
        # Check stocks
        for category_data in self.categories.values():
            for stock in category_data["stocks"]:
                if stock["symbol"] == symbol:
                    return stock.get("current_price", stock.get("price", 100.0))
        
        # Check ETFs
        if hasattr(self, 'etfs') and symbol in self.etfs:
            return self.etfs[symbol].get("current_price", self.etfs[symbol].get("price", 100.0))
        
        return None
    
    def get_stock_price(self, symbol: str) -> Optional[float]:
        """Get current price for a stock from cache
        
        DEPRECATED: Use get_current_price() instead for 5-minute interval caching
        AIDEV-NOTE: legacy-compat; redirects to get_current_price
        """
        return self.get_current_price(symbol)
    
    
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
                base_seed = self.deterministic_hash(symbol + trading_day) % 10000
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
        # AIDEV-NOTE: ai-price-entry-point; AI sets opening prices daily here
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
        
        # STEP 1: Get previous trading day data for continuity
        log_to_file("STEP 1: Getting previous trading day data for AI context")
        previous_data = self.get_previous_trading_day_data()
        
        # Extract previous parameters if available, otherwise use neutral defaults
        if previous_data and "market_state" in previous_data and "parameters" in previous_data["market_state"]:
            previous_params = previous_data["market_state"]["parameters"]
            log_to_file(f"Previous parameters from {previous_data.get('timestamp', 'unknown')[:10]}: {json.dumps(previous_params, indent=2)}")
            print(f"📊 Using previous market parameters from {previous_data.get('timestamp', 'unknown')[:10]}")
        else:
            # Use neutral defaults if no previous data
            previous_params = {
                "trend_direction": 0.0,
                "volatility": 0.5,
                "momentum": 0.5,
                "market_sentiment": 0.5,
                "long_term_outlook": 0.5
            }
            log_to_file("No previous parameters found, using neutral defaults")
            print("📊 No previous parameters found, using neutral defaults for AI")
        
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
        log_to_file("STEP 3: Running AI analysis with structured output")
        
        ai_retry_count = 0
        max_ai_retries = 3
        
        while ai_retry_count < max_ai_retries:
            try:
                # Create structured output schema
                market_analysis_schema = self._create_market_analysis_schema()
                log_to_file("Created structured output schema for market analysis")
                
                # Build prompt for structured output
                analysis_prompt = self.build_structured_analysis_prompt(all_messages, previous_params)
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
                parsed_result = self.parse_structured_market_analysis(response.text, previous_params, log_file)
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
                        "previous_market_params": previous_params,
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
    
    
    
    def _create_market_analysis_schema(self) -> Dict[str, Any]:
        """Create JSON schema for structured market analysis output"""
        
        # AIDEV-NOTE: perlin-schema; AI sets Perlin parameters, not prices
        # Create schema for per-stock Perlin parameters
        stock_perlin_properties = {}
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                stock_perlin_properties[stock["symbol"]] = {
                    "type": "object",
                    "properties": {
                        "trend_strength": {"type": "number"},      # 0-1
                        "trend_direction": {"type": "number"},     # -1 to 1
                        "volatility": {"type": "number"},          # 0-1
                        "noise_scale": {"type": "number"},         # 0.5-2.0
                        "cycle_frequency": {"type": "number"},     # 0.5-2.0
                        "sector_correlation": {"type": "number"}   # 0-1
                    },
                    "required": ["trend_strength", "trend_direction", "volatility", "noise_scale", "cycle_frequency", "sector_correlation"]
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
                "perlin_parameters": {
                    "type": "object",
                    "properties": stock_perlin_properties,
                    "required": list(stock_perlin_properties.keys())
                },
                "sector_outlook": {
                    "type": "object",
                    "properties": sector_outlook_properties,
                    "required": list(sector_outlook_properties.keys())
                }
            },
            "required": ["reasoning", "parameters", "invisible_factors", "perlin_parameters", "sector_outlook"]
        }
        
        return schema
    
    def build_structured_analysis_prompt(self, messages: List[Dict], previous_params: Dict[str, float]) -> str:
        """Build prompt specifically for structured JSON output"""
        
        # Get current economic indicators from files
        try:
            economic_data_dir = ECONOMIC_DATA_DIR
            
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

**PREVIOUS MARKET PARAMETERS:**
{json.dumps(previous_params, indent=2)}

**PARAMETER SETTING GUIDELINES:**
You have full control to set market parameters based on your analysis of economic conditions and Discord activity.
- trend_direction: Set based on GDP growth ({gdp_change}%), economic momentum, and Discord sentiment
- volatility: Set based on inflation ({inflation_rate}% vs 2.0% target), uncertainty in Discord, and market conditions
- market_sentiment: Set based on market confidence ({market_confidence}%) and Discord activity tone
- momentum: Set based on economic growth, employment ({unemployment_rate}%), and activity levels
- long_term_outlook: Adjust gradually based on fundamental changes (previous: {previous_params.get('long_term_outlook', 0.5):.3f})

**DISCORD ACTIVITY ANALYSIS (last 24 hours):**
Total messages analyzed: {len(messages)}
"""
        
        for cat_name, cat_messages in categorized_messages.items():
            prompt += f"\n{cat_name}: {len(cat_messages)} messages"
            if cat_messages:
                sample_content = " | ".join([msg['content'][:50] for msg in cat_messages[:2]])
                prompt += f" - Sample: {sample_content}..."
        
        prompt += f"""

**STOCK UNIVERSE (all stocks need Perlin parameters):**
{', '.join([f"{stock['symbol']}" for cat_data in self.categories.values() for stock in cat_data['stocks']])}

**PERLIN PARAMETER GUIDELINES:**
For each stock, set the following parameters based on sector, economic data, and Discord activity:
- trend_strength (0-1): How strongly the stock follows its trend. 0=random walk, 1=strong trend
- trend_direction (-1 to 1): -1=bearish, 0=neutral, 1=bullish. Based on sector outlook and specific news
- volatility (0-1): Individual stock volatility. Tech stocks typically 0.6-0.9, utilities 0.2-0.4
- noise_scale (0.5-2.0): Amplitude of price movements. 1.0=normal, 2.0=double amplitude
- cycle_frequency (0.5-2.0): How fast the stock cycles. 1.0=normal, 2.0=twice as fast
- sector_correlation (0-1): How closely it follows its sector. 1.0=perfect correlation

**ANALYSIS REQUIREMENTS:**
1. Set market-wide parameters based on economic indicators and Discord activity
2. Set Perlin parameters for ALL 24 stocks (NO PRICES - just trend/volatility parameters)
3. Set invisible market factors (institutional flow, liquidity, etc.)
4. Give sector-specific outlooks for all 8 sectors
5. Provide detailed reasoning for all decisions

**OUTPUT FORMAT:** The response will be automatically formatted as JSON matching the required schema. Focus on setting realistic trend and volatility parameters based on the economic data and Discord activity."""
        
        return prompt
    
    def parse_structured_market_analysis(self, ai_response: str, previous_params: Dict[str, float], log_file) -> Dict[str, Any]:
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
                "long_term_outlook": max(0.0, min(1.0, float(params.get("long_term_outlook", previous_params.get("long_term_outlook", 0.5)))))
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
            
            # AIDEV-NOTE: perlin-params-required; AI must provide Perlin parameters
            # CRITICAL: Perlin parameters are REQUIRED
            if "perlin_parameters" not in analysis:
                log_to_file("❌ CRITICAL: No perlin_parameters provided by AI")
                raise ValueError("AI analysis must provide perlin_parameters for all stocks")
            
            # Validate all stocks have parameters
            required_symbols = {stock["symbol"] for cat in self.categories.values() for stock in cat["stocks"]}
            provided_symbols = set(analysis["perlin_parameters"].keys())
            missing_symbols = required_symbols - provided_symbols
            
            if missing_symbols:
                log_to_file(f"❌ CRITICAL: Missing Perlin parameters for stocks: {missing_symbols}")
                raise ValueError(f"AI must provide Perlin parameters for all stocks. Missing: {missing_symbols}")
            
            # Validate Perlin parameter structure
            for symbol, param_data in analysis["perlin_parameters"].items():
                required_fields = ["trend_strength", "trend_direction", "volatility", "noise_scale", "cycle_frequency", "sector_correlation"]
                missing_fields = [field for field in required_fields if field not in param_data]
                if missing_fields:
                    raise ValueError(f"Stock {symbol} missing required Perlin fields: {missing_fields}")
            
            log_to_file(f"✅ Validated Perlin parameters for {len(provided_symbols)} stocks")
            self._apply_ai_perlin_parameters(analysis["perlin_parameters"])
            
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
                
                # Apply Perlin parameters if provided
                if "perlin_parameters" in analysis:
                    self._apply_ai_perlin_parameters(analysis["perlin_parameters"])
                    print("✅ AI-provided Perlin parameters applied")
                else:
                    print("⚠️ No Perlin parameters in AI response, using defaults")
                
                print("✅ AI market analysis parsed successfully")
                return analysis
            else:
                raise ValueError("No valid JSON found in AI response")
                
        except Exception as e:
            print(f"❌ Error parsing AI analysis: {e}")
            raise Exception(f"Failed to parse AI analysis: {e}")
    
    def _apply_ai_perlin_parameters(self, perlin_params: Dict[str, Dict[str, float]]) -> None:
        """Apply AI-provided Perlin parameters for stock behavior"""
        print("🔄 Applying AI-provided Perlin parameters...")
        
        # AIDEV-NOTE: perlin-param-application; AI controls trends and volatility
        # Clear any existing parameters
        self.stock_perlin_params = {}
        
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                symbol = stock["symbol"]
                if symbol in perlin_params:
                    param_data = perlin_params[symbol]
                    
                    # Validate and clamp parameters to valid ranges
                    trend_strength = max(0.0, min(1.0, float(param_data.get("trend_strength", 0.5))))
                    trend_direction = max(-1.0, min(1.0, float(param_data.get("trend_direction", 0.0))))
                    volatility = max(0.0, min(1.0, float(param_data.get("volatility", 0.5))))
                    noise_scale = max(0.5, min(2.0, float(param_data.get("noise_scale", 1.0))))
                    cycle_frequency = max(0.5, min(2.0, float(param_data.get("cycle_frequency", 1.0))))
                    sector_correlation = max(0.0, min(1.0, float(param_data.get("sector_correlation", 1.0))))
                    
                    # Store parameters for this stock
                    self.stock_perlin_params[symbol] = {
                        "trend_strength": trend_strength,
                        "trend_direction": trend_direction,
                        "volatility": volatility,
                        "noise_scale": noise_scale,
                        "cycle_frequency": cycle_frequency,
                        "sector_correlation": sector_correlation
                    }
                    
                    # Remove deprecated fields from stock
                    if "ai_opening_price" in stock:
                        del stock["ai_opening_price"]
                    if "daily_range_low" in stock:
                        del stock["daily_range_low"]
                    if "daily_range_high" in stock:
                        del stock["daily_range_high"]
                    
                    print(f"📊 {symbol}: trend={trend_direction:+.2f} (str={trend_strength:.2f}), "
                          f"vol={volatility:.2f}, scale={noise_scale:.2f}, freq={cycle_frequency:.2f}")
                else:
                    # No parameters provided, use defaults
                    self.stock_perlin_params[symbol] = {
                        "trend_strength": 0.5,
                        "trend_direction": 0.0,
                        "volatility": 0.5,
                        "noise_scale": 1.0,
                        "cycle_frequency": 1.0,
                        "sector_correlation": 1.0
                    }
                    print(f"⚠️ {symbol}: Using default Perlin parameters")
        
        print(f"✅ Applied Perlin parameters for {len(self.stock_perlin_params)} stocks")
    
    # REMOVED: correct_out_of_range_prices
    # No longer needed - Perlin system doesn't use daily ranges
    
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
                latest_inflation = economic_data["inflation"][-1]["data"]
                prompt += f"\n**CURRENT INFLATION DATA**:\n"
                prompt += f"- Current Rate: {latest_inflation.get('rate', 'N/A')}%\n"
                prompt += f"- Federal Funds Rate: {latest_inflation.get('federal_funds_rate', 'N/A')}%\n"
                prompt += f"- Trend: {latest_inflation.get('trend', 'N/A')}\n"
                prompt += f"- Policy Impact: {latest_inflation.get('policy_impact', 'N/A')[:150]}...\n"
            
            # Include GDP data
            if "gdp" in economic_data and economic_data["gdp"]:
                latest_gdp = economic_data["gdp"][-1]["data"]
                prompt += f"\n**CURRENT GDP DATA**:\n"
                prompt += f"- GDP: ${latest_gdp.get('value', 'N/A')}T\n"
                prompt += f"- Growth Rate: {latest_gdp.get('change_percent', 'N/A')}%\n"
                prompt += f"- Quarterly Growth: {latest_gdp.get('quarterly_growth', 'N/A')}%\n"
                prompt += f"- Outlook: {latest_gdp.get('outlook', 'N/A')[:150]}...\n"
            
            # Include sentiment data
            if "sentiment" in economic_data and economic_data["sentiment"]:
                latest_sentiment = economic_data["sentiment"][-1]["data"]
                prompt += f"\n**CURRENT MARKET SENTIMENT DATA**:\n"
                prompt += f"- Market Confidence: {latest_sentiment.get('market_confidence', 'N/A')}%\n"
                prompt += f"- Business Sentiment: {latest_sentiment.get('business_sentiment', 'N/A')}%\n"
                prompt += f"- Consumer Confidence: {latest_sentiment.get('consumer_confidence', 'N/A')}%\n"
                prompt += f"- Inflation Anxiety: {latest_sentiment.get('inflation_anxiety', 'N/A')}%\n"
                prompt += f"- Outlook: {latest_sentiment.get('outlook', 'N/A')[:150]}...\n"
            
            # Include unemployment data
            if "unemployment" in economic_data and economic_data["unemployment"]:
                latest_unemployment = economic_data["unemployment"][-1]["data"]
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
        # AIDEV-NOTE: hourly-price-update; Perlin noise generates price from AI opening
        print(f"📊 Calculating prices on-demand for update period {hour_index}")
        
        # Update all stock prices using on-demand calculation
        price_updates = {}
        
        for cat_name, cat_data in self.categories.items():
            for stock in cat_data["stocks"]:
                symbol = stock["symbol"]
                old_price = stock["price"]
                
                # AIDEV-NOTE: pure-perlin-update; No AI opening price needed
                # Calculate new price on-demand using Perlin parameters
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
            # Use cached price to prevent recursion
            cached_price = self.get_cached_etf_price(etf_symbol)
            etf_prices[etf_symbol] = cached_price if cached_price is not None else self.etfs[etf_symbol].get("price", 100.0)
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
    
    def generate_stock_chart_from_history(self, symbol: str, hours_back: int = 48) -> Optional[bytes]:
        """Generate chart from SAVED historical data only
        
        AIDEV-NOTE: chart-from-history; reads actual prices from stock_history.json
        """
        try:
            # Read historical data
            history_file = self.data_dir / "stock_history.json"
            if not history_file.exists():
                print(f"⚠️ No historical data file found")
                return None
            
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            if not history:
                print(f"⚠️ Historical data is empty")
                return None
            
            # Extract prices for requested symbol
            prices = []
            timestamps = []
            
            # Get last N hourly snapshots (history is saved hourly)
            for entry in history[-hours_back:]:
                data = entry.get("data", {})
                timestamp_str = entry.get("timestamp", "")
                
                # Check individual stocks first
                if symbol in data.get("individual_stocks", {}):
                    prices.append(data["individual_stocks"][symbol])
                    timestamps.append(timestamp_str)
                # Then check ETF prices
                elif symbol in data.get("etf_prices", {}):
                    prices.append(data["etf_prices"][symbol])
                    timestamps.append(timestamp_str)
            
            if len(prices) < 2:
                print(f"⚠️ Not enough historical data for {symbol} (found {len(prices)} points)")
                return None
            
            # Generate chart from actual historical prices
            print(f"📊 Generating chart for {symbol} with {len(prices)} historical data points")
            return self.generate_stock_chart(symbol, prices)
            
        except Exception as e:
            print(f"❌ Error generating historical chart for {symbol}: {e}")
            import traceback
            traceback.print_exc()
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
        # return 9 <= et_now.hour < 17  # 9 AM to 4:59 PM (Commented out - Trading is 24/7)
        return True
    
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
            
            # Run a quick AI analysis (no fallback - per CLAUDE.md principles)
            try:
                analysis = await self.stock_market.get_daily_market_analysis()
                self.stock_market.save_daily_analysis(analysis)
                print("✅ Emergency AI analysis completed")
            except Exception as e:
                print(f"❌ Emergency AI analysis failed: {e}")
                # AIDEV-NOTE: no-fallback; system requires AI - no fake data generation
                raise Exception(f"Cannot initialize market without AI analysis: {e}")
            
            # Update market parameters
            self.stock_market.market_params = analysis.get("parameters", self.stock_market.market_params)
            
            # Precompute all prices for 5-minute intervals
            self.stock_market.precompute_all_prices()
            
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
        # AIDEV-NOTE: hourly-trigger; triggers Perlin price updates from AI opening
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
        """Post hourly update using ONLY cached prices from 5-minute intervals
        
        AIDEV-NOTE: hourly-cache-update; pulls from precomputed 5min cache only
        """
        et_now = self.get_et_now()
        
        # Ensure market open time is set and from today
        if not self.stock_market.market_open_time:
            print("⚠️ Market open time not set, initializing...")
            success = await self.force_daily_initialization()
            if not success:
                print("❌ Could not initialize market, skipping update")
                return
        else:
            # Check if market_open_time is from today
            try:
                from zoneinfo import ZoneInfo
                et_tz = ZoneInfo("America/New_York")
            except ImportError:
                import pytz
                et_tz = pytz.timezone("America/New_York")
            
            market_open_et = self.stock_market.market_open_time.astimezone(et_tz)
            
            if market_open_et.date() != et_now.date():
                print(f"⚠️ Market open time is stale (from {market_open_et.date()}), reinitializing...")
                success = await self.force_daily_initialization()
                if not success:
                    print("❌ Could not reinitialize market, skipping update")
                    return
        
        print(f"📊 Posting hourly update at {et_now.strftime('%I:%M %p ET')} [24/7 Trading]")
        
        # Calculate exact hour offset and corresponding minute offset
        time_elapsed = (et_now - self.stock_market.market_open_time).total_seconds()
        hour_offset = int(time_elapsed / 3600)
        minute_offset = hour_offset * 60  # Exact hour mark
        
        # Ensure we're within bounds
        if minute_offset < 0:
            minute_offset = 0
        elif minute_offset > 1435:
            minute_offset = 1435
        
        # Get prices from cache for this exact hour
        price_updates = {}
        
        for cat_data in self.stock_market.categories.values():
            for stock in cat_data["stocks"]:
                symbol = stock["symbol"]
                old_price = stock.get("price", stock.get("ai_opening_price", 100.0))
                
                try:
                    # Get price from 5-minute cache at exact hour offset
                    if symbol in self.stock_market.stock_price_cache_5min:
                        if minute_offset in self.stock_market.stock_price_cache_5min[symbol]:
                            new_price = self.stock_market.stock_price_cache_5min[symbol][minute_offset]
                        else:
                            # Fallback to nearest 5-minute interval
                            nearest_5min = (minute_offset // 5) * 5
                            new_price = self.stock_market.stock_price_cache_5min[symbol].get(nearest_5min, old_price)
                    else:
                        print(f"⚠️ No cached prices for {symbol}")
                        new_price = old_price
                    
                    # Update the price field
                    stock["price"] = new_price
                    
                    price_updates[symbol] = {
                        "old_price": old_price,
                        "new_price": new_price,
                        "change": new_price - old_price,
                        "change_pct": ((new_price - old_price) / old_price) * 100 if old_price > 0 else 0
                    }
                except Exception as e:
                    print(f"⚠️ Error getting cached price for {symbol}: {e}")
        
        # Calculate category prices from cached stock prices
        category_prices = self.stock_market.calculate_category_prices()
        
        # Get ETF prices from cache
        etf_prices = {}
        for etf_symbol in self.stock_market.etfs.keys():
            try:
                if etf_symbol in self.stock_market.etf_price_cache_5min:
                    if minute_offset in self.stock_market.etf_price_cache_5min[etf_symbol]:
                        etf_prices[etf_symbol] = self.stock_market.etf_price_cache_5min[etf_symbol][minute_offset]
                    else:
                        # Fallback to nearest 5-minute interval
                        nearest_5min = (minute_offset // 5) * 5
                        etf_prices[etf_symbol] = self.stock_market.etf_price_cache_5min[etf_symbol].get(
                            nearest_5min, 
                            self.stock_market.etfs[etf_symbol].get("price", 100.0)
                        )
                else:
                    etf_prices[etf_symbol] = self.stock_market.etfs[etf_symbol].get("price", 100.0)
                
                # Update ETF current_price
                self.stock_market.etfs[etf_symbol]["current_price"] = etf_prices[etf_symbol]
                
            except Exception as e:
                print(f"⚠️ Error getting cached ETF price for {etf_symbol}: {e}")
        
        # Save historical snapshot
        timestamp = datetime.now(timezone.utc).isoformat()
        hour_index = max(0, hour_offset) % 24  # Cap at 0-23 for display
        
        historical_data = {
            "individual_stocks": {symbol: price_updates[symbol]["new_price"] 
                                for symbol in price_updates},
            "category_prices": category_prices,
            "etf_prices": etf_prices,
            "market_params": self.stock_market.market_params,
            "trading_hour": hour_index,
            "hour_offset": hour_offset,
            "minute_offset": minute_offset,
            "update_rate_minutes": self.stock_market.price_update_rate_minutes
        }
        
        # Save to history file
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
    # AIDEV-NOTE: stale-time-check; validate market_open_time is from today
    needs_initialization = False
    
    if not stock_market.market_open_time or not stock_market.current_trading_day:
        needs_initialization = True
        print("🔄 No market open time found, running daily market initialization...")
    else:
        # Check if market_open_time is from today
        et_now = stock_scheduler.get_et_now()
        
        # Convert market_open_time to ET using same approach as get_et_now
        try:
            from zoneinfo import ZoneInfo
            et_tz = ZoneInfo("America/New_York")
        except ImportError:
            import pytz
            et_tz = pytz.timezone("America/New_York")
        
        market_open_et = stock_market.market_open_time.astimezone(et_tz)
        
        if market_open_et.date() != et_now.date():
            needs_initialization = True
            print(f"🔄 Market open time is stale (from {market_open_et.date()}), running daily market initialization...")
    
    if needs_initialization:
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