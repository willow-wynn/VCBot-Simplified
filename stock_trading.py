"""
Stock Trading Integration with UnbelievaBoat
Handles buying/selling stocks using UnbelievaBoat balances and portfolio management.
"""

import json
import os
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import discord
from unbelievaboat import Client
from config import UNBELIEVABOAT_API_KEY, GUILD_ID, STOCK_DATA_DIR
from stock_market import StockMarket

# AIDEV-NOTE: Trading system - integrates UnbelievaBoat economy with stock market
class StockTradingSystem:
    """Manages stock trading with UnbelievaBoat integration"""
    
    def __init__(self):
        self.data_dir = STOCK_DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
        self.portfolio_file = self.data_dir / "user_portfolios.json"
        self.unb_client = None
        self.guild_id = GUILD_ID
        
        # Initialize portfolio data
        self._load_portfolios()
        print("💼 Stock Trading System initialized")
    
    def _load_portfolios(self) -> None:
        """Load user portfolios from JSON file"""
        if self.portfolio_file.exists():
            try:
                with open(self.portfolio_file, 'r') as f:
                    self.portfolios = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                self.portfolios = {}
        else:
            self.portfolios = {}
    
    def _save_portfolios(self) -> None:
        """Save user portfolios to JSON file"""
        with open(self.portfolio_file, 'w') as f:
            json.dump(self.portfolios, f, indent=2)
    
    # AIDEV-NOTE: UnbelievaBoat client - manages Discord server economy balance
    async def _get_unb_client(self) -> Client:
        """Get or create UnbelievaBoat client"""
        if self.unb_client is None:
            self.unb_client = Client(UNBELIEVABOAT_API_KEY)
        return self.unb_client
    
    async def get_user_balance(self, user_id: int) -> Optional[float]:
        """Get user's UnbelievaBoat balance"""
        try:
            client = await self._get_unb_client()
            guild = await client.get_guild(self.guild_id)
            user = await guild.get_user_balance(user_id)
            return float(user.cash)  # Use cash balance for trading
        except Exception as e:
            print(f"❌ Error getting user balance for {user_id}: {e}")
            return None
    
    async def update_user_balance(self, user_id: int, amount: float) -> bool:
        """Update user's UnbelievaBoat balance (positive = add, negative = subtract)"""
        try:
            client = await self._get_unb_client()
            guild = await client.get_guild(self.guild_id)
            user = await guild.get_user_balance(user_id)
            
            # Use the correct API method - user.update() with cash parameter
            await user.update(cash=int(amount))
            return True
        except Exception as e:
            print(f"❌ Error updating user balance for {user_id}: {e}")
            # Log more details for debugging
            if hasattr(e, 'response'):
                print(f"Response status: {e.response.status}")
                try:
                    error_text = await e.response.text()
                    print(f"Response text: {error_text}")
                    if "403" in str(e.response.status):
                        print("💡 Hint: Make sure the UnbelievaBoat application is authorized in your Discord server")
                        print("   Visit: https://unbelievaboat.com/dashboard/applications to get your app ID")
                        print("   Then authorize at: https://unbelievaboat.com/applications/authorize?app_id=YOUR_APP_ID&guild_id=654458344781774879")
                except:
                    pass
            return False
    
    def get_user_portfolio(self, user_id: int) -> Dict[str, int]:
        """Get user's stock portfolio"""
        return self.portfolios.get(str(user_id), {})
    
    def get_user_stock_quantity(self, user_id: int, symbol: str) -> int:
        """Get quantity of specific stock owned by user"""
        portfolio = self.get_user_portfolio(user_id)
        return portfolio.get(symbol, 0)
    
    def add_stock_to_portfolio(self, user_id: int, symbol: str, quantity: int) -> None:
        """Add stocks to user's portfolio"""
        user_id_str = str(user_id)
        if user_id_str not in self.portfolios:
            self.portfolios[user_id_str] = {}
        
        current_quantity = self.portfolios[user_id_str].get(symbol, 0)
        self.portfolios[user_id_str][symbol] = current_quantity + quantity
        self._save_portfolios()
    
    def remove_stock_from_portfolio(self, user_id: int, symbol: str, quantity: int) -> bool:
        """Remove stocks from user's portfolio. Returns True if successful, False if insufficient stocks"""
        user_id_str = str(user_id)
        if user_id_str not in self.portfolios:
            return False
        
        current_quantity = self.portfolios[user_id_str].get(symbol, 0)
        if current_quantity < quantity:
            return False
        
        new_quantity = current_quantity - quantity
        if new_quantity == 0:
            del self.portfolios[user_id_str][symbol]
        else:
            self.portfolios[user_id_str][symbol] = new_quantity
        
        self._save_portfolios()
        return True
    
    async def buy_stock(self, user_id: int, symbol: str, quantity: int, stock_market: StockMarket) -> Tuple[bool, str]:
        """
        Buy stocks for a user
        Returns (success: bool, message: str)
        """
        # Validate stock/ETF exists
        all_assets = stock_market.get_all_tradeable_assets()
        stock_info = None
        for asset in all_assets:
            if asset['symbol'].upper() == symbol.upper():
                stock_info = asset
                break
        
        if not stock_info:
            return False, f"❌ Stock/ETF symbol '{symbol}' not found!"
        
        # Calculate total cost
        stock_price = stock_info['price']
        total_cost = stock_price * quantity
        
        # Check user balance
        user_balance = await self.get_user_balance(user_id)
        if user_balance is None:
            return False, "❌ Unable to check your balance. Please try again."
        
        if user_balance < total_cost:
            return False, f"❌ Insufficient funds! You need ${total_cost:,.2f} but only have ${user_balance:,.2f}"
        
        # Process transaction
        success = await self.update_user_balance(user_id, -total_cost)
        if not success:
            return False, "❌ Failed to process payment. Please try again."
        
        # Add stocks to portfolio
        self.add_stock_to_portfolio(user_id, symbol.upper(), quantity)
        
        return True, f"✅ Successfully purchased {quantity} shares of {stock_info['name']} ({symbol.upper()}) for ${total_cost:,.2f}!"
    
    async def sell_stock(self, user_id: int, symbol: str, quantity: int, stock_market: StockMarket) -> Tuple[bool, str]:
        """
        Sell stocks for a user
        Returns (success: bool, message: str)
        """
        # Validate stock/ETF exists
        all_assets = stock_market.get_all_tradeable_assets()
        stock_info = None
        for asset in all_assets:
            if asset['symbol'].upper() == symbol.upper():
                stock_info = asset
                break
        
        if not stock_info:
            return False, f"❌ Stock/ETF symbol '{symbol}' not found!"
        
        # Check if user has enough stocks
        owned_quantity = self.get_user_stock_quantity(user_id, symbol.upper())
        if owned_quantity < quantity:
            return False, f"❌ You only own {owned_quantity} shares of {symbol.upper()}, cannot sell {quantity}!"
        
        # Calculate total sale value
        stock_price = stock_info['price']
        total_value = stock_price * quantity
        
        # Remove stocks from portfolio
        success = self.remove_stock_from_portfolio(user_id, symbol.upper(), quantity)
        if not success:
            return False, "❌ Failed to remove stocks from portfolio."
        
        # Add money to user balance
        payment_success = await self.update_user_balance(user_id, total_value)
        if not payment_success:
            # Rollback portfolio change
            self.add_stock_to_portfolio(user_id, symbol.upper(), quantity)
            return False, "❌ Failed to process payment. Transaction rolled back."
        
        return True, f"✅ Successfully sold {quantity} shares of {stock_info['name']} ({symbol.upper()}) for ${total_value:,.2f}!"
    
    def get_portfolio_value(self, user_id: int, stock_market: StockMarket) -> Tuple[float, Dict[str, Dict[str, Any]]]:
        """
        Calculate total portfolio value and detailed breakdown
        Returns (total_value: float, breakdown: Dict[symbol: {quantity, price, value, name}])
        """
        portfolio = self.get_user_portfolio(user_id)
        all_assets = stock_market.get_all_tradeable_assets()
        
        # Create lookup dict for stock/ETF info
        stock_lookup = {asset['symbol']: asset for asset in all_assets}
        
        total_value = 0.0
        breakdown = {}
        
        for symbol, quantity in portfolio.items():
            if symbol in stock_lookup:
                stock_info = stock_lookup[symbol]
                stock_price = stock_info['price']
                stock_value = stock_price * quantity
                total_value += stock_value
                
                breakdown[symbol] = {
                    'quantity': quantity,
                    'price': stock_price,
                    'value': stock_value,
                    'name': stock_info['name'],
                    'category': stock_info.get('category', 'Unknown')
                }
        
        return total_value, breakdown

# Global instance
_stock_trading_system = None

def get_stock_trading_system() -> StockTradingSystem:
    """Get the global stock trading system instance"""
    global _stock_trading_system
    if _stock_trading_system is None:
        _stock_trading_system = StockTradingSystem()
    return _stock_trading_system