"""
Stock Market Hub Commands
Provides consolidated stock market interfaces with interactive buttons
"""

import discord
from discord import app_commands
from typing import Optional
from datetime import datetime, timezone
from functools import wraps
from stock_market import get_stock_market, stock_scheduler, is_scheduler_running, stop_scheduler
from stock_trading import get_stock_trading_system
from config import Roles, BOT_HELPER_CHANNEL
import stock_commands

def has_any_role(*roles):
    """Decorator to check if user has any of the specified roles"""
    def predicate(interaction: discord.Interaction) -> bool:
        if not hasattr(interaction.user, 'roles'):
            return False
        user_roles = [role.name for role in interaction.user.roles]
        return any(role in user_roles for role in roles)
    return app_commands.check(predicate)

def handle_errors(error_message: str):
    """Decorator to handle command errors gracefully"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                interaction = args[0] if args else None
                if interaction and hasattr(interaction, 'followup'):
                    try:
                        await interaction.followup.send(f"❌ {error_message}: {str(e)}")
                    except:
                        print(f"Error in {func.__name__}: {e}")
                else:
                    print(f"Error in {func.__name__}: {e}")
        return wrapper
    return decorator

class StockHubView(discord.ui.View):
    """Interactive view for stock market hub"""
    
    def __init__(self, user: discord.User):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user = user
        
    @discord.ui.button(label="📊 Market Overview", style=discord.ButtonStyle.primary, row=0)
    async def market_overview(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing stocks_overview logic (it handles its own defer)
        await stock_commands.stocks_overview.callback(interaction)
        
    @discord.ui.button(label="📈 Stock Prices", style=discord.ButtonStyle.primary, row=0)
    async def stock_prices(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        await interaction.response.send_message("Enter a stock symbol in chat (e.g., AAPL, MSFT, GOOGL)", ephemeral=True)
        
    @discord.ui.button(label="🏦 View Sectors", style=discord.ButtonStyle.primary, row=0)
    async def view_sectors(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_categories.callback(interaction)
        
    @discord.ui.button(label="📉 48h History", style=discord.ButtonStyle.primary, row=1)
    async def history_48h(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        await interaction.response.send_message("Enter a stock symbol in chat to see its 48h history", ephemeral=True)
        
    @discord.ui.button(label="💰 Trading Menu", style=discord.ButtonStyle.success, row=1)
    async def trading_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Create trading submenu
        view = TradingView(self.user)
        embed = discord.Embed(
            title="💰 Trading Menu",
            description="Select a trading action:",
            color=0x00ff88
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    @discord.ui.button(label="📋 List All Stocks", style=discord.ButtonStyle.secondary, row=1)
    async def list_stocks(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_list.callback(interaction)

class TradingView(discord.ui.View):
    """Trading submenu view"""
    
    def __init__(self, user: discord.User):
        super().__init__(timeout=180)
        self.user = user
        
    @discord.ui.button(label="💵 Buy Stocks", style=discord.ButtonStyle.success)
    async def buy_stocks(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        await interaction.response.send_message(
            "To buy stocks, use: `/stocks_buy [symbol] [quantity]`\nExample: `/stocks_buy AAPL 10`",
            ephemeral=True
        )
        
    @discord.ui.button(label="💸 Sell Stocks", style=discord.ButtonStyle.danger)
    async def sell_stocks(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        await interaction.response.send_message(
            "To sell stocks, use: `/stocks_sell [symbol] [quantity]`\nExample: `/stocks_sell AAPL 5`",
            ephemeral=True
        )
        
    @discord.ui.button(label="📊 View Portfolio", style=discord.ButtonStyle.primary)
    async def view_portfolio(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_portfolio.callback(interaction)

class StockAdminView(discord.ui.View):
    """Admin view for stock market management"""
    
    def __init__(self, user: discord.User):
        super().__init__(timeout=300)
        self.user = user
        
    @discord.ui.button(label="▶️ Start Market", style=discord.ButtonStyle.success, row=0)
    async def start_market(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.start_stock_market.callback(interaction, initialize=False)
        
    @discord.ui.button(label="⏹️ Stop Market", style=discord.ButtonStyle.danger, row=0)
    async def stop_market(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stop_stock_market.callback(interaction)
        
    @discord.ui.button(label="📊 View Status", style=discord.ButtonStyle.primary, row=0)
    async def view_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_status.callback(interaction)
        
    @discord.ui.button(label="🔄 Force Update", style=discord.ButtonStyle.secondary, row=0)
    async def force_update(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_force_update.callback(interaction)
        
    @discord.ui.button(label="🛠️ Market Parameters", style=discord.ButtonStyle.primary, row=1)
    async def market_params(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="🛠️ Market Parameters",
            description="Use these commands to adjust parameters:",
            color=0x0099ff
        )
        embed.add_field(
            name="Available Commands",
            value=(
                "`/stocks_set_market [param] [value]` - Set market parameter\n"
                "`/stocks_set_update_rate [minutes]` - Set update interval\n"
                "\n**Parameters:**\n"
                "• trend_direction (-1 to 1)\n"
                "• volatility (0 to 1)\n"
                "• momentum (0 to 1)\n"
                "• market_sentiment (0 to 1)\n"
                "• long_term_outlook (0 to 1)"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @discord.ui.button(label="➕ Add Stock", style=discord.ButtonStyle.success, row=1)
    async def add_stock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        await interaction.response.send_message(
            "Use: `/stocks_add [sector] [symbol] [name] [price] [industry]`",
            ephemeral=True
        )
        
    @discord.ui.button(label="🔄 Sync Economy", style=discord.ButtonStyle.secondary, row=1)
    async def sync_economy(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_sync_econ.callback(interaction)
        
    @discord.ui.button(label="🔄 Force Init", style=discord.ButtonStyle.danger, row=2)
    async def force_init(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_force_init.callback(interaction)
        
    @discord.ui.button(label="🗑️ Clear History", style=discord.ButtonStyle.danger, row=2)
    async def clear_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_clear_history.callback(interaction)
        
    @discord.ui.button(label="🔐 Toggle Admin Trading", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_admin_trading(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_toggle_admin_trading.callback(interaction)

# Hub Commands

@app_commands.command(name="stocks_hub", description="Stock market hub - all stock features in one place")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to display stock hub")
async def stocks_hub(interaction: discord.Interaction):
    """Main stock market hub with interactive buttons"""
    embed = discord.Embed(
        title="📈 Stock Market Hub",
        description="Access all stock market features from one place",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    stock_market = get_stock_market()
    is_running = is_scheduler_running()
    
    # Quick status
    status_text = f"**Market**: {'🟢 Open' if stock_market.is_trading_day else '🔴 Closed'}\n"
    status_text += f"**Scheduler**: {'✅ Running' if is_running else '⏹️ Stopped'}\n"
    status_text += f"**Update Rate**: Every {stock_market.price_update_rate_minutes} minutes"
    
    embed.add_field(name="📊 Quick Status", value=status_text, inline=False)
    
    # Feature descriptions
    features = (
        "• **Market Overview** - View current market parameters and ETFs\n"
        "• **Stock Prices** - Get current price for any stock\n"
        "• **View Sectors** - Browse stocks by economic sector\n"
        "• **48h History** - View detailed price charts\n"
        "• **Trading Menu** - Buy/sell stocks and view portfolio\n"
        "• **List All Stocks** - See all 24 available stocks"
    )
    embed.add_field(name="🎯 Available Features", value=features, inline=False)
    
    embed.set_footer(text="Buttons will timeout after 5 minutes")
    
    view = StockHubView(interaction.user)
    await interaction.response.send_message(embed=embed, view=view)

@app_commands.command(name="stocks_admin", description="Stock market admin hub - management controls")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to display admin hub")
async def stocks_admin(interaction: discord.Interaction):
    """Admin stock market hub with management controls"""
    embed = discord.Embed(
        title="⚙️ Stock Market Admin Hub",
        description="Administrative controls for stock market management",
        color=0xff6b6b,
        timestamp=datetime.now(timezone.utc)
    )
    
    stock_market = get_stock_market()
    is_running = is_scheduler_running()
    
    # System status
    status_text = f"**Scheduler**: {'✅ Running' if is_running else '⏹️ Stopped'}\n"
    status_text += f"**Market Day**: {stock_market.current_trading_day or 'Not set'}\n"
    status_text += f"**Update Rate**: {stock_market.price_update_rate_minutes} minutes\n"
    
    # Current parameters
    params = stock_market.market_params
    status_text += f"\n**Market Parameters:**\n"
    status_text += f"Trend: {params['trend_direction']:+.2f}\n"
    status_text += f"Volatility: {params['volatility']:.2f}\n"
    status_text += f"Sentiment: {params['market_sentiment']:.2f}"
    
    embed.add_field(name="📊 System Status", value=status_text, inline=False)
    
    # Control descriptions
    controls = (
        "• **Start/Stop** - Control market scheduler\n"
        "• **View Status** - Detailed scheduler status\n"
        "• **Force Update** - Trigger immediate analysis\n"
        "• **Market Parameters** - Adjust market behavior\n"
        "• **Add Stock** - Add new stocks to market\n"
        "• **Sync Economy** - Sync with economic data\n"
        "• **Force Init** - Complete re-initialization\n"
        "• **Clear History** - Clear price history\n"
        "• **Toggle Admin Trading** - Restrict trading"
    )
    embed.add_field(name="🛠️ Admin Controls", value=controls, inline=False)
    
    embed.set_footer(text="⚠️ Admin controls - use with caution")
    
    view = StockAdminView(interaction.user)
    await interaction.response.send_message(embed=embed, view=view)