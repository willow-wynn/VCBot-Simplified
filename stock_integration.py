"""
Stock Market Integration for VCBot
Provides integration between stock market system and Discord bot commands
"""

import discord
from discord.ext import commands
from stock_market import initialize_stock_market
from stock_commands import (
    stocks_overview, stocks_sector, stocks_stock, stocks_channel,
    stocks_add, stocks_remove, stocks_modify, stocks_params, stocks_history
)

async def setup_stock_market(client):
    """Initialize the stock market system with the Discord client"""
    try:
        await initialize_stock_market(client)
        print("📈 Stock market integration complete")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize stock market: {e}")
        return False

def add_stock_commands_to_tree(tree):
    """Add all stock market commands to the command tree"""
    print("📊 Adding stock market commands to command tree...")
    
    # Add all stock commands
    tree.add_command(stocks_overview)
    tree.add_command(stocks_sector)
    tree.add_command(stocks_stock)
    tree.add_command(stocks_channel)
    tree.add_command(stocks_add)
    tree.add_command(stocks_remove)
    tree.add_command(stocks_modify)
    tree.add_command(stocks_params)
    tree.add_command(stocks_history)
    
    print(f"✅ Added {9} stock market commands")

# Integration instructions for bot.py
INTEGRATION_INSTRUCTIONS = """
To integrate the stock market system with bot.py, add these lines:

1. At the top of bot.py, add:
   import stock_integration

2. In the on_ready() function, add:
   await stock_integration.setup_stock_market(client)

3. After creating the command tree, add:
   stock_integration.add_stock_commands_to_tree(tree)

4. Make sure matplotlib is installed:
   pip install matplotlib

The stock market system will then be fully integrated with:
- 9 Discord commands for stock management
- Automated daily market analysis at 8:40 AM ET
- Hourly price updates during trading hours (9 AM - 5 PM ET)
- AI-powered market parameter setting
- Integration with economic system data
- Matplotlib chart generation for price movements
"""

if __name__ == "__main__":
    print("📈 VCBot Stock Market Integration Module")
    print("=" * 50)
    print(INTEGRATION_INSTRUCTIONS)