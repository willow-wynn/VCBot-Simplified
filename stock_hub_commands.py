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
            
        # Defer to prevent timeout during StockSelectionView creation
        await interaction.response.defer(ephemeral=True)
        
        # Create stock selection dropdown
        view = StockSelectionView(self.user, "price")
        embed = discord.Embed(
            title="📈 Stock Price Lookup",
            description="Select a stock to view its current price:",
            color=0x00ff88
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    @discord.ui.button(label="🏦 View Sectors", style=discord.ButtonStyle.primary, row=0)
    async def view_sectors(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_categories.callback(interaction)
        
    @discord.ui.button(label="📉 Price History", style=discord.ButtonStyle.primary, row=1)
    async def price_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Create history type selection view
        view = HistorySelectionView(self.user)
        embed = discord.Embed(
            title="📉 Stock Price History",
            description="Select the time range for price history:",
            color=0x00ff88
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
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
        
    @discord.ui.button(label="📊 View ETFs", style=discord.ButtonStyle.primary, row=1)
    async def view_etfs(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_etfs.callback(interaction)
        
    @discord.ui.button(label="📋 List All Stocks", style=discord.ButtonStyle.secondary, row=2)
    async def list_stocks(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_list.callback(interaction)

class StockSelectionView(discord.ui.View):
    """View for selecting stocks with dropdown menu"""
    
    def __init__(self, user: discord.User, action: str):
        super().__init__(timeout=180)
        self.user = user
        self.action = action  # "price" or "history"
        
        # Get all available stocks from stock market
        stock_market = get_stock_market()
        options = []
        
        # Create dropdown options for all stocks
        for category_name, category_data in stock_market.categories.items():
            for stock in category_data["stocks"]:
                label = f"{stock['symbol']} - {stock['name']}"
                # Truncate label if too long (Discord limit is 100 chars)
                if len(label) > 90:
                    label = f"{stock['symbol']} - {stock['name'][:80]}..."
                
                options.append(discord.SelectOption(
                    label=label,
                    value=stock['symbol'],
                    description=f"{category_name} sector - ${stock['price']:.2f}",
                    emoji="📈"
                ))
        
        # Add ETF options if available
        if hasattr(stock_market, 'etfs'):
            for etf_symbol, etf_data in stock_market.etfs.items():
                label = f"{etf_data['symbol']} - {etf_data['name']}"
                if len(label) > 90:
                    label = f"{etf_data['symbol']} - {etf_data['name'][:80]}..."
                
                # Use cached price method for better performance
                price = stock_market.get_cached_etf_price(etf_symbol)
                
                etf_type = "Index ETF" if etf_data['type'] in ['market_cap_weighted', 'equal_weighted'] else "Sector ETF"
                
                options.append(discord.SelectOption(
                    label=label,
                    value=etf_data['symbol'],
                    description=f"{etf_type} - ${price:.2f}",
                    emoji="📊"
                ))
        
        # Sort options by symbol
        options.sort(key=lambda x: x.value)
        
        # Discord has a limit of 25 options per select menu
        # If we have more stocks, we'll need to split them
        if len(options) <= 25:
            self.add_item(StockSelect(options, self.action))
        else:
            # Split into multiple select menus if needed
            mid_point = len(options) // 2
            self.add_item(StockSelect(options[:mid_point], self.action, "A-M"))
            self.add_item(StockSelect(options[mid_point:], self.action, "N-Z"))

class StockSelect(discord.ui.Select):
    """Select dropdown for stock symbols"""
    
    def __init__(self, options: list, action: str, label_suffix: str = ""):
        placeholder = f"Select a stock{f' ({label_suffix})' if label_suffix else ''}..."
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        )
        self.action = action
        
    async def callback(self, interaction: discord.Interaction):
        selected_symbol = self.values[0]
        
        if self.action == "price":
            # Use existing stocks_price command
            await stock_commands.stocks_price.callback(interaction, symbol=selected_symbol)
        elif self.action == "history":
            # Use existing stocks_history_48h command
            await stock_commands.stocks_history_48h.callback(interaction, symbol=selected_symbol)
        elif self.action == "history_7d":
            # Use stocks_history with 7 day parameter
            await stock_commands.stocks_history.callback(interaction, days_back=7, symbol=selected_symbol)
        elif self.action == "history_30d":
            # Use stocks_history with 30 day parameter
            await stock_commands.stocks_history.callback(interaction, days_back=30, symbol=selected_symbol)
        elif self.action == "history_all":
            # Use stocks_history with maximum 30 days (API limit)
            await stock_commands.stocks_history.callback(interaction, days_back=30, symbol=selected_symbol)
        elif self.action == "peek_future":
            # Use stocks_admin_peek with default 24 hours
            await stock_commands.stocks_admin_peek.callback(interaction, symbol=selected_symbol, hours=24)
        elif self.action == "admin_detail":
            # Use stocks_admin_detail command
            await stock_commands.stocks_admin_detail.callback(interaction, symbol=selected_symbol)

class HistorySelectionView(discord.ui.View):
    """View for selecting history time range"""
    
    def __init__(self, user: discord.User):
        super().__init__(timeout=180)
        self.user = user
        
    @discord.ui.button(label="📊 48 Hours", style=discord.ButtonStyle.primary, row=0)
    async def history_48h(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Defer to prevent timeout during StockSelectionView creation
        await interaction.response.defer(ephemeral=True)
        
        view = StockSelectionView(self.user, "history")
        embed = discord.Embed(
            title="📊 48-Hour Price History",
            description="Select a stock to view its 48-hour price chart:",
            color=0x00ff88
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    @discord.ui.button(label="📈 7 Days", style=discord.ButtonStyle.primary, row=0)
    async def history_7d(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Defer to prevent timeout during StockSelectionView creation
        await interaction.response.defer(ephemeral=True)
        
        view = StockSelectionView(self.user, "history_7d")
        embed = discord.Embed(
            title="📈 7-Day Price History",
            description="Select a stock to view its 7-day price chart:",
            color=0x00ff88
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    @discord.ui.button(label="📉 30 Days", style=discord.ButtonStyle.primary, row=0)
    async def history_30d(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Defer to prevent timeout during StockSelectionView creation
        await interaction.response.defer(ephemeral=True)
        
        view = StockSelectionView(self.user, "history_30d")
        embed = discord.Embed(
            title="📉 30-Day Price History",
            description="Select a stock to view its 30-day price chart:",
            color=0x00ff88
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    @discord.ui.button(label="📅 30 Days Max", style=discord.ButtonStyle.secondary, row=1)
    async def history_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Defer to prevent timeout during StockSelectionView creation
        await interaction.response.defer(ephemeral=True)
        
        view = StockSelectionView(self.user, "history_all")
        embed = discord.Embed(
            title="📅 30-Day Price History",
            description="Select a stock to view its 30-day price history (maximum available):",
            color=0x00ff88
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

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
        
    @discord.ui.button(label="💎 Trade ETFs", style=discord.ButtonStyle.secondary, row=1)
    async def trade_etfs(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Get ETF info
        stock_market = get_stock_market()
        if not hasattr(stock_market, 'etfs') or not stock_market.etfs:
            await interaction.response.send_message("❌ ETFs are not available", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="💎 ETF Trading",
            description="Available ETFs:\n",
            color=0x00ff88
        )
        
        # Sort ETFs by type for better organization
        index_etfs = []
        sector_etfs = []
        other_etfs = []
        
        for symbol, etf in stock_market.etfs.items():
            price = stock_market.get_cached_etf_price(symbol)
            
            if etf['type'] in ['market_cap_weighted', 'equal_weighted']:
                index_etfs.append((symbol, etf, price))
            elif etf['type'] == 'sector':
                sector_etfs.append((symbol, etf, price))
            else:
                other_etfs.append((symbol, etf, price))
        
        # Add index ETFs
        if index_etfs:
            index_text = ""
            for symbol, etf, price in sorted(index_etfs, key=lambda x: x[0]):
                index_text += f"**{symbol}** - ${price:.2f}\n{etf['name']}\n"
            embed.add_field(name="📊 Index ETFs", value=index_text.strip(), inline=False)
        
        # Add sector ETFs
        if sector_etfs:
            sector_text = ""
            for symbol, etf, price in sorted(sector_etfs, key=lambda x: x[0]):
                sector = etf.get('sector', 'Unknown')
                sector_text += f"**{symbol}** - ${price:.2f} ({sector})\n"
            embed.add_field(name="🏭 Sector ETFs", value=sector_text.strip(), inline=False)
        
        # Add other ETFs
        if other_etfs:
            other_text = ""
            for symbol, etf, price in sorted(other_etfs, key=lambda x: x[0]):
                other_text += f"**{symbol}** - ${price:.2f}\n{etf['name']}\n"
            embed.add_field(name="💎 Specialty ETFs", value=other_text.strip(), inline=False)
            
        embed.add_field(
            name="How to Trade ETFs",
            value=(
                "**Buy**: `/stocks_buy [ETF_SYMBOL] [quantity]`\n"
                "**Sell**: `/stocks_sell [ETF_SYMBOL] [quantity]`\n"
                "Example: `/stocks_buy SPY 10`"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
        
    @discord.ui.button(label="💾 Save Structure", style=discord.ButtonStyle.primary, row=2)
    async def save_structure(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_save_structure.callback(interaction)
        
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
    
    @discord.ui.button(label="🔍 Stock Details", style=discord.ButtonStyle.primary, row=3)
    async def stock_details(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Defer to prevent timeout during StockSelectionView creation
        await interaction.response.defer(ephemeral=True)
        
        # Create stock selection dropdown for admin details
        view = StockSelectionView(self.user, "admin_detail")
        embed = discord.Embed(
            title="🔍 Stock Details",
            description="Select a stock to view detailed parameters:",
            color=0xff6b6b
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🔮 Peek Future", style=discord.ButtonStyle.primary, row=3)
    async def peek_future(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Defer to prevent timeout during StockSelectionView creation
        await interaction.response.defer(ephemeral=True)
        
        # Create stock selection dropdown for future peek
        view = StockSelectionView(self.user, "peek_future")
        embed = discord.Embed(
            title="🔮 Peek Future Prices",
            description="Select a stock to preview its future price movements:",
            color=0xff6b6b
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🐛 Debug Info", style=discord.ButtonStyle.secondary, row=3)
    async def debug_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        # Use existing command logic (it handles its own defer)
        await stock_commands.stocks_admin_debug.callback(interaction)

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
    stock_count = sum(len(cat['stocks']) for cat in stock_market.categories.values())
    etf_count = len(stock_market.etfs) if hasattr(stock_market, 'etfs') else 0
    
    features = (
        f"• **Market Overview** - View current market parameters and {etf_count} ETFs\n"
        f"• **Stock Prices** - Get current price for any of {stock_count} stocks\n"
        "• **View Sectors** - Browse stocks by economic sector\n"
        "• **Price History** - View charts for 48h, 7d, or 30d (max available)\n"
        "• **View ETFs** - See all available ETFs including S&P, sector, and specialty funds\n"
        "• **Trading Menu** - Buy/sell stocks and view portfolio\n"
        f"• **List All Stocks** - See all {stock_count} available stocks"
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
        "• **Save Structure** - Save current market structure to disk\n"
        "• **Clear History** - Clear price history\n"
        "• **Toggle Admin Trading** - Restrict trading\n"
        "• **Stock Details** - View detailed stock parameters\n"
        "• **Peek Future** - Preview future price movements\n"
        "• **Debug Info** - View system internals"
    )
    embed.add_field(name="🛠️ Admin Controls", value=controls, inline=False)
    
    embed.set_footer(text="⚠️ Admin controls - use with caution")
    
    view = StockAdminView(interaction.user)
    await interaction.response.send_message(embed=embed, view=view)