# AIDEV-NOTE: Centralized data layer - prevents inconsistencies, caches JSON files
"""
Data Managers - Single Source of Truth for Economic and Stock Data

This module provides centralized data access to ensure consistency across the entire system.
All economic and stock data access MUST go through these managers.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import os
from config import ECONOMIC_DATA_DIR, STOCK_DATA_DIR

class EconomicDataManager:
    """Single source of truth for all economic data"""
    
    def __init__(self):
        self.data_dir = ECONOMIC_DATA_DIR
        self._cache = {}
        self._cache_timestamp = None
        self._cache_duration = 60  # Cache for 60 seconds
        
    def _refresh_cache_if_needed(self):
        """Refresh cache if it's stale"""
        now = datetime.now(timezone.utc)
        if (self._cache_timestamp is None or 
            (now - self._cache_timestamp).total_seconds() > self._cache_duration):
            self._load_all_data()
            self._cache_timestamp = now
    
    def _load_all_data(self):
        """Load all economic data files into cache"""
        self._cache = {}
        
        # Load each category
        categories = ["gdp", "inflation", "unemployment", "sentiment", "parameters"]
        
        for category in categories:
            file_path = self.data_dir / f"{category}.json"
            if file_path.exists() and file_path.stat().st_size > 0:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        if data and len(data) > 0:
                            # ALWAYS get the LATEST entry (last in array)
                            if category == "parameters":
                                # Parameters file has different structure
                                self._cache[category] = data
                            else:
                                # Data files have array structure
                                latest_entry = data[-1]
                                self._cache[category] = latest_entry.get('data', {})
                                self._cache[f"{category}_timestamp"] = latest_entry.get('timestamp')
                except Exception as e:
                    print(f"⚠️ Error loading {category}.json: {e}")
    
    def get_current_gdp(self) -> Dict[str, Any]:
        """Get current GDP data"""
        self._refresh_cache_if_needed()
        gdp_data = self._cache.get('gdp')
        if not gdp_data:
            # Return None if no data exists, don't mask with defaults
            return None
        return gdp_data
    
    def get_current_inflation(self) -> Dict[str, Any]:
        """Get current inflation data"""
        self._refresh_cache_if_needed()
        inflation_data = self._cache.get('inflation')
        if not inflation_data:
            # Return None if no data exists, don't mask with defaults
            return None
        return inflation_data
    
    def get_current_unemployment(self) -> Dict[str, Any]:
        """Get current unemployment data"""
        self._refresh_cache_if_needed()
        return self._cache.get('unemployment', {
            'rate': 4.0,
            'trend': 'stable'
        })
    
    def get_current_sentiment(self) -> Dict[str, Any]:
        """Get current market sentiment"""
        self._refresh_cache_if_needed()
        return self._cache.get('sentiment', {
            'market_confidence': 50,
            'inflation_anxiety': 50,
            'policy_uncertainty': 50
        })
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get economic simulation parameters"""
        self._refresh_cache_if_needed()
        return self._cache.get('parameters', {})
    
    def get_all_current_data(self) -> Dict[str, Any]:
        """Get all current economic data in one call"""
        self._refresh_cache_if_needed()
        return {
            'gdp': self.get_current_gdp(),
            'inflation': self.get_current_inflation(),
            'unemployment': self.get_current_unemployment(),
            'sentiment': self.get_current_sentiment(),
            'timestamp': self._cache.get('gdp_timestamp', datetime.now(timezone.utc).isoformat())
        }


class StockDataManager:
    """Single source of truth for all stock market data"""
    
    def __init__(self):
        self.data_dir = STOCK_DATA_DIR
        self._market_data = None
        self._market_params = None
        self._daily_analysis = None
        self._last_load_time = None
        self._reload_interval = 5  # Reload every 5 seconds if needed
        
    def _load_if_needed(self):
        """Load data if not loaded or if stale"""
        now = datetime.now(timezone.utc)
        if (self._last_load_time is None or 
            (now - self._last_load_time).total_seconds() > self._reload_interval):
            self._load_all_data()
            self._last_load_time = now
    
    def _load_all_data(self):
        """Load all stock market data files"""
        # Load market data
        market_file = self.data_dir / "market_data.json"
        if market_file.exists():
            try:
                with open(market_file, 'r') as f:
                    self._market_data = json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading market_data.json: {e}")
                self._market_data = {}
        
        # Load market parameters
        params_file = self.data_dir / "market_params.json"
        if params_file.exists():
            try:
                with open(params_file, 'r') as f:
                    self._market_params = json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading market_params.json: {e}")
        
        # If no params file, get from market data
        if self._market_params is None and self._market_data:
            self._market_params = self._market_data.get('market_params', {})
        
        # Load daily analysis
        analysis_file = self.data_dir / "daily_analysis.json"
        if analysis_file.exists():
            try:
                with open(analysis_file, 'r') as f:
                    self._daily_analysis = json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading daily_analysis.json: {e}")
    
    def get_stock_price(self, symbol: str) -> Optional[float]:
        """Get current price for a stock - SINGLE source of truth"""
        self._load_if_needed()
        
        if not self._market_data:
            return None
            
        # Search through categories for the stock
        for category in self._market_data.get('categories', {}).values():
            for stock in category.get('stocks', []):
                if stock['symbol'] == symbol:
                    # Return the ONE true price (not current_price or any other field)
                    return stock.get('price')
        
        return None
    
    def get_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get all data for a stock"""
        self._load_if_needed()
        
        if not self._market_data:
            return None
            
        # Search through categories for the stock
        for category in self._market_data.get('categories', {}).values():
            for stock in category.get('stocks', []):
                if stock['symbol'] == symbol:
                    # Return copy to prevent accidental modification
                    return stock.copy()
        
        return None
    
    def get_all_stocks(self) -> List[Dict[str, Any]]:
        """Get all stocks as a flat list"""
        self._load_if_needed()
        
        stocks = []
        if self._market_data:
            for category in self._market_data.get('categories', {}).values():
                stocks.extend(category.get('stocks', []))
        
        return stocks
    
    def get_market_params(self) -> Dict[str, Any]:
        """Get current market parameters"""
        self._load_if_needed()
        
        return self._market_params or {
            'trend_direction': 0.0,
            'volatility': 0.5,
            'momentum': 0.5,
            'market_sentiment': 0.5,
            'long_term_outlook': 0.5
        }
    
    def get_daily_analysis(self) -> Optional[Dict[str, Any]]:
        """Get the most recent daily analysis"""
        self._load_if_needed()
        return self._daily_analysis
    
    def get_category_etf_price(self, category_name: str) -> float:
        """Calculate ETF price for a category"""
        self._load_if_needed()
        
        if not self._market_data:
            return 0.0
            
        category = self._market_data.get('categories', {}).get(category_name)
        if not category:
            return 0.0
            
        stocks = category.get('stocks', [])
        if not stocks:
            return 0.0
            
        # Simple equal-weighted average
        total_price = sum(stock.get('price', 0) for stock in stocks)
        return total_price / len(stocks)
    
    def get_all_category_etf_prices(self) -> Dict[str, float]:
        """Get all category ETF prices"""
        self._load_if_needed()
        
        prices = {}
        if self._market_data:
            for cat_name in self._market_data.get('categories', {}).keys():
                prices[cat_name] = self.get_category_etf_price(cat_name)
        
        return prices


# Global singleton instances
_economic_data_manager = None
_stock_data_manager = None

def get_economic_data_manager() -> EconomicDataManager:
    """Get the singleton economic data manager"""
    global _economic_data_manager
    if _economic_data_manager is None:
        _economic_data_manager = EconomicDataManager()
    return _economic_data_manager

def get_stock_data_manager() -> StockDataManager:
    """Get the singleton stock data manager"""
    global _stock_data_manager
    if _stock_data_manager is None:
        _stock_data_manager = StockDataManager()
    return _stock_data_manager