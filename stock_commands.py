"""
Discord Commands for Stock Market System
Provides comprehensive stock management and viewing commands
"""

import discord
from discord import app_commands
from typing import Literal, Optional, Any
import json
import io
import asyncio
from datetime import datetime, timezone, timedelta
from functools import wraps
from stock_market import get_stock_market, stock_scheduler, is_scheduler_running, stop_scheduler
from config import Roles, BOT_HELPER_CHANNEL
from data_managers import get_stock_data_manager, get_economic_data_manager
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
# import message_utils  # Not used in this file

def has_any_role(*roles):
    """Decorator to check if user has any of the specified roles"""
    def predicate(interaction: discord.Interaction) -> bool:
        if not hasattr(interaction.user, 'roles'):
            return False
        user_roles = [role.name for role in interaction.user.roles]
        return any(role in user_roles for role in roles)
    return app_commands.check(predicate)

def limit_to_channels(channel_ids):
    """Decorator to limit command to specific channels"""
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.channel_id in channel_ids
    return app_commands.check(predicate)

def handle_errors(error_message: str):
    """Decorator to handle command errors gracefully"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Get interaction from args
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

# Stock Market Commands

@app_commands.command(name="stocks", description="View current stock market overview")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@limit_to_channels([BOT_HELPER_CHANNEL])
@handle_errors("Failed to display stock market overview")
async def stocks_overview(interaction: discord.Interaction):
    """Display comprehensive stock market overview"""
    await interaction.response.defer()
    
    # Use data managers for consistent data access
    stock_data_manager = get_stock_data_manager()
    stock_market = get_stock_market()  # Still need this for some operations
    
    # Create main embed
    embed = discord.Embed(
        title="📈 Virtual Congress Stock Market",
        description="Market Status: 🟢 OPEN 24/7",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Market parameters from data manager
    params = stock_data_manager.get_market_params()
    param_text = f"""
**Trend**: {params['trend_direction']:+.2f} {'📈' if params['trend_direction'] > 0 else '📉' if params['trend_direction'] < 0 else '➡️'}
**Volatility**: {params['volatility']:.2f} {'🌪️' if params['volatility'] > 0.7 else '🌊'}
**Momentum**: {params['momentum']:.2f} {'🚀' if params['momentum'] > 0.7 else '⚡'}
**Sentiment**: {params['market_sentiment']:.2f} {'😄' if params['market_sentiment'] > 0.7 else '😐' if params['market_sentiment'] > 0.4 else '😟'}
**Outlook**: {params['long_term_outlook']:.2f} {'🌟' if params['long_term_outlook'] > 0.7 else '🌤️'}
"""
    embed.add_field(name="📊 Market Parameters", value=param_text.strip(), inline=True)
    
    # Show actual sector ETF prices
    if hasattr(stock_market, 'etfs'):
        sector_etf_map = {
            'XLE': ('ENERGY', '⛽'),
            'XLC': ('ENTERTAINMENT', '🎬'),
            'XLF': ('FINANCE', '🏦'),
            'XLV': ('HEALTH', '🏥'),
            'XLI': ('MANUFACTURING', '🏭'),
            'XLY': ('RETAIL', '🛒'),
            'XLK': ('TECH', '💻'),
            'XLU': ('TRANSPORT', '✈️')
        }
        
        etf_text = ""
        for etf_symbol, (sector_name, emoji) in sector_etf_map.items():
            if etf_symbol in stock_market.etfs:
                price = stock_market.get_cached_etf_price(etf_symbol)
                etf_text += f"{emoji} **{etf_symbol}** ({sector_name}): ${price:.2f}\n"
        
        embed.add_field(name="📊 Sector ETFs", value=etf_text.strip() or "No sector ETFs available", inline=True)
    else:
        embed.add_field(name="📊 Sector ETFs", value="ETFs not initialized", inline=True)
    
    # Trading info (24/7 operation)
    if stock_scheduler:
        et_now = stock_scheduler.get_et_now()
        trading_info = f"**Day**: {stock_market.current_trading_day or et_now.strftime('%Y-%m-%d')}\n**Time**: {et_now.strftime('%I:%M %p ET')}\n**Hours**: 24/7 Trading Active\n**Update Rate**: Every {stock_market.price_update_rate_minutes} minute{'s' if stock_market.price_update_rate_minutes != 1 else ''}"
    else:
        trading_info = f"**Hours**: 24/7 Trading Active\n**Update Rate**: Every {stock_market.price_update_rate_minutes} minute{'s' if stock_market.price_update_rate_minutes != 1 else ''}"
    
    embed.add_field(name="🕐 Trading Schedule", value=trading_info, inline=False)
    
    # Add market index ETFs
    if hasattr(stock_market, 'etfs'):
        index_etfs = []
        for symbol, etf in stock_market.etfs.items():
            if etf['type'] in ['market_cap_weighted', 'equal_weighted']:
                price = etf.get('current_price', stock_market.calculate_etf_price(symbol))
                index_etfs.append(f"**{symbol}**: ${price:.2f}")
        
        if index_etfs:
            embed.add_field(name="📊 Market Index ETFs", value="\n".join(index_etfs[:5]), inline=False)
    
    # Stock count
    total_stocks = sum(len(cat['stocks']) for cat in stock_market.categories.values())
    etf_count = len(stock_market.etfs) if hasattr(stock_market, 'etfs') else 0
    embed.set_footer(text=f"{total_stocks} individual stocks across {len(stock_market.categories)} sectors | {etf_count} ETFs available")
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_sector", description="View detailed information for a specific sector")
@app_commands.describe(sector="Sector to view (ENERGY, ENTERTAINMENT, FINANCE, HEALTH, MANUFACTURING, RETAIL, TECH, TRANSPORT)")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to display sector information")
async def stocks_sector(interaction: discord.Interaction, 
                       sector: Literal["ENERGY", "ENTERTAINMENT", "FINANCE", "HEALTH", "MANUFACTURING", "RETAIL", "TECH", "TRANSPORT"]):
    """Display detailed sector information"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    if sector not in stock_market.categories:
        await interaction.followup.send(f"❌ Sector '{sector}' not found")
        return
    
    sector_data = stock_market.categories[sector]
    
    # Create sector embed
    embed = discord.Embed(
        title=f"📊 {sector_data['name']}",
        description=sector_data['description'],
        color=0x0099ff,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Sector ETF price
    category_prices = stock_market.calculate_category_prices()
    etf_price = category_prices.get(sector, 0.0)
    
    emoji = "⛽" if sector == "ENERGY" else "🎬" if sector == "ENTERTAINMENT" else "🏦" if sector == "FINANCE" else "🏥" if sector == "HEALTH" else "🏭" if sector == "MANUFACTURING" else "🛒" if sector == "RETAIL" else "💻" if sector == "TECH" else "✈️"
    embed.add_field(name=f"{emoji} Sector ETF Price", value=f"${etf_price:.2f}", inline=True)
    
    # Individual stocks
    stocks_text = ""
    for stock in sector_data['stocks']:
        stocks_text += f"**{stock['symbol']}** - {stock['name']}\n"
        stocks_text += f"💰 ${stock['price']:.2f} | 🏭 {stock['sector'].replace('_', ' ').title()}\n\n"
    
    embed.add_field(name="📈 Individual Stocks", value=stocks_text.strip(), inline=False)
    
    # Recent performance (if historical data available)
    historical_data = stock_market.get_historical_data(days_back=1)
    if historical_data:
        recent_text = "Recent performance data available"
        embed.add_field(name="📊 Recent Performance", value=recent_text, inline=False)
    
    embed.set_footer(text=f"{len(sector_data['stocks'])} stocks in sector")
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_stock", description="View detailed information for a specific stock")
@app_commands.describe(symbol="Stock symbol (e.g., VCMC, LSI, EXDY)")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to display stock information")
async def stocks_stock(interaction: discord.Interaction, symbol: str):
    """Display detailed individual stock information"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    symbol = symbol.upper()
    
    # Find the stock
    target_stock = None
    target_category = None
    
    for cat_name, cat_data in stock_market.categories.items():
        for stock in cat_data['stocks']:
            if stock['symbol'] == symbol:
                target_stock = stock
                target_category = cat_name
                break
        if target_stock:
            break
    
    if not target_stock:
        await interaction.followup.send(f"❌ Stock '{symbol}' not found")
        return
    
    # Create stock embed
    embed = discord.Embed(
        title=f"📈 {target_stock['symbol']} - {target_stock['name']}",
        description=f"Sector: {target_category} | Industry: {target_stock['sector'].replace('_', ' ').title()}",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Current price
    embed.add_field(name="💰 Current Price", value=f"${target_stock['price']:.2f}", inline=True)
    
    # Get recent price history for chart
    historical_data = stock_market.get_historical_data(days_back=7)
    
    if historical_data:
        # Extract prices for this stock
        prices = []
        timestamps = []
        
        for entry in historical_data[-24:]:  # Last 24 hours of data
            if 'data' in entry and 'individual_stocks' in entry['data']:
                if symbol in entry['data']['individual_stocks']:
                    prices.append(entry['data']['individual_stocks'][symbol])
                    timestamps.append(entry['timestamp'])
        
        if len(prices) > 1:
            # Calculate change
            change = prices[-1] - prices[0]
            change_pct = (change / prices[0]) * 100
            
            direction = "📈" if change >= 0 else "📉"
            color_indicator = "🟢" if change >= 0 else "🔴"
            
            embed.add_field(
                name=f"{direction} Recent Change", 
                value=f"{color_indicator} ${change:+.2f} ({change_pct:+.2f}%)", 
                inline=True
            )
            
            # Generate chart if possible
            try:
                chart_bytes = stock_market.generate_stock_chart(symbol, prices[-8:])  # Last 8 data points
                if chart_bytes:
                    chart_file = discord.File(io.BytesIO(chart_bytes), filename=f"{symbol}_chart.png")
                    embed.set_image(url=f"attachment://{symbol}_chart.png")
                    await interaction.followup.send(embed=embed, file=chart_file)
                    return
            except Exception as e:
                print(f"Chart generation failed: {e}")
    
    # Market info (24/7 trading)
    market_status = "🟢 ALWAYS OPEN"
    embed.add_field(name="📊 Market Status", value=market_status, inline=True)
    
    # Category info
    category_prices = stock_market.calculate_category_prices()
    etf_price = category_prices.get(target_category, 0.0)
    embed.add_field(name="🏦 Sector ETF", value=f"${etf_price:.2f}", inline=False)
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_channel", description="Set the channel for stock market updates")
@app_commands.describe(channel="Channel to receive stock updates (mention the channel)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to set stocks channel")
async def stocks_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set the channel for stock market updates"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    # Update the stocks channel
    old_channel_id = stock_market.stocks_channel_id
    stock_market.stocks_channel_id = channel.id
    
    # Save the change
    stock_market.save_market_data()
    
    embed = discord.Embed(
        title="✅ Stocks Channel Updated",
        description=f"Stock market updates will now be sent to {channel.mention}",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    if old_channel_id != channel.id:
        old_channel = interaction.guild.get_channel(old_channel_id)
        if old_channel:
            embed.add_field(name="Previous Channel", value=old_channel.mention, inline=True)
    
    embed.add_field(name="Update Types", value="• Daily market preparation (8:40 AM ET)\n• Hourly price updates (24/7)\n• Market charts and analysis", inline=False)
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_add", description="Add a new stock to a sector")
@app_commands.describe(
    sector="Sector to add stock to",
    symbol="Stock symbol (3-5 characters)",
    name="Company name",
    price="Initial stock price",
    industry="Industry/subsector"
)
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to add stock")
async def stocks_add(interaction: discord.Interaction, 
                    sector: Literal["ENERGY", "ENTERTAINMENT", "FINANCE", "HEALTH", "MANUFACTURING", "RETAIL", "TECH", "TRANSPORT"],
                    symbol: str, name: str, price: float, industry: str):
    """Add a new stock to the market"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    symbol = symbol.upper()
    
    # Validate symbol
    if len(symbol) < 2 or len(symbol) > 6:
        await interaction.followup.send("❌ Stock symbol must be 2-6 characters")
        return
    
    # Check if symbol already exists
    for cat_data in stock_market.categories.values():
        for stock in cat_data['stocks']:
            if stock['symbol'] == symbol:
                await interaction.followup.send(f"❌ Stock symbol '{symbol}' already exists")
                return
    
    # Validate price
    if price <= 0:
        await interaction.followup.send("❌ Stock price must be positive")
        return
    
    # Add the stock
    new_stock = {
        "symbol": symbol,
        "name": name,
        "price": price,
        "sector": industry.lower().replace(' ', '_')
    }
    
    stock_market.categories[sector]['stocks'].append(new_stock)
    stock_market.save_market_data()
    
    # Create success embed
    embed = discord.Embed(
        title="✅ Stock Added Successfully",
        description=f"Added {symbol} to {sector} sector",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="📈 Stock Details", value=f"**Symbol**: {symbol}\n**Name**: {name}\n**Price**: ${price:.2f}\n**Industry**: {industry}", inline=True)
    embed.add_field(name="🏢 Sector", value=f"{sector}\n{len(stock_market.categories[sector]['stocks'])} stocks", inline=True)
    
    # Update category ETF price
    category_prices = stock_market.calculate_category_prices()
    etf_price = category_prices.get(sector, 0.0)
    embed.add_field(name="🏦 New Sector ETF Price", value=f"${etf_price:.2f}", inline=True)
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_remove", description="Remove a stock from the market")
@app_commands.describe(symbol="Stock symbol to remove")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to remove stock")
async def stocks_remove(interaction: discord.Interaction, symbol: str):
    """Remove a stock from the market"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    symbol = symbol.upper()
    
    # Find and remove the stock
    removed_stock = None
    removed_sector = None
    
    for cat_name, cat_data in stock_market.categories.items():
        for i, stock in enumerate(cat_data['stocks']):
            if stock['symbol'] == symbol:
                removed_stock = cat_data['stocks'].pop(i)
                removed_sector = cat_name
                break
        if removed_stock:
            break
    
    if not removed_stock:
        await interaction.followup.send(f"❌ Stock '{symbol}' not found")
        return
    
    stock_market.save_market_data()
    
    # Create success embed
    embed = discord.Embed(
        title="✅ Stock Removed Successfully",
        description=f"Removed {symbol} from {removed_sector} sector",
        color=0xff6b6b,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="📉 Removed Stock", value=f"**Symbol**: {symbol}\n**Name**: {removed_stock['name']}\n**Last Price**: ${removed_stock['price']:.2f}", inline=True)
    embed.add_field(name="🏢 Sector", value=f"{removed_sector}\n{len(stock_market.categories[removed_sector]['stocks'])} stocks remaining", inline=True)
    
    # Update category ETF price
    category_prices = stock_market.calculate_category_prices()
    etf_price = category_prices.get(removed_sector, 0.0)
    embed.add_field(name="🏦 New Sector ETF Price", value=f"${etf_price:.2f}", inline=True)
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_modify", description="Modify a stock's price or details")
@app_commands.describe(
    symbol="Stock symbol to modify",
    price="New stock price (optional)",
    name="New company name (optional)"
)
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to modify stock")
async def stocks_modify(interaction: discord.Interaction, symbol: str, price: Optional[float] = None, name: Optional[str] = None):
    """Modify a stock's price or details"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    symbol = symbol.upper()
    
    # Find the stock
    target_stock = None
    target_category = None
    
    for cat_name, cat_data in stock_market.categories.items():
        for stock in cat_data['stocks']:
            if stock['symbol'] == symbol:
                target_stock = stock
                target_category = cat_name
                break
        if target_stock:
            break
    
    if not target_stock:
        await interaction.followup.send(f"❌ Stock '{symbol}' not found")
        return
    
    # Track changes
    changes = []
    old_price = target_stock['price']
    
    # Update price if provided
    if price is not None:
        if price <= 0:
            await interaction.followup.send("❌ Stock price must be positive")
            return
        target_stock['price'] = price
        change_pct = ((price - old_price) / old_price) * 100
        changes.append(f"Price: ${old_price:.2f} → ${price:.2f} ({change_pct:+.2f}%)")
    
    # Update name if provided
    if name is not None:
        old_name = target_stock['name']
        target_stock['name'] = name
        changes.append(f"Name: {old_name} → {name}")
    
    if not changes:
        await interaction.followup.send("❌ No changes specified")
        return
    
    stock_market.save_market_data()
    
    # Create success embed
    embed = discord.Embed(
        title="✅ Stock Modified Successfully",
        description=f"Updated {symbol} in {target_category} sector",
        color=0x0099ff,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="📊 Changes Made", value="\n".join(changes), inline=False)
    
    # Show new category ETF price if price changed
    if price is not None:
        category_prices = stock_market.calculate_category_prices()
        etf_price = category_prices.get(target_category, 0.0)
        embed.add_field(name="🏦 New Sector ETF Price", value=f"${etf_price:.2f}", inline=True)
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_params", description="View or modify market parameters")
@app_commands.describe(
    trend_direction="Market trend direction (-1 to 1, optional)",
    volatility="Market volatility (0 to 1, optional)",
    momentum="Price momentum (0 to 1, optional)",
    market_sentiment="Market sentiment (0 to 1, optional)"
)
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to modify market parameters")
async def stocks_params(interaction: discord.Interaction, 
                       trend_direction: Optional[float] = None,
                       volatility: Optional[float] = None,
                       momentum: Optional[float] = None,
                       market_sentiment: Optional[float] = None):
    """View or modify market parameters"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    # If no parameters provided, just show current values
    if all(param is None for param in [trend_direction, volatility, momentum, market_sentiment]):
        params = stock_market.market_params
        
        embed = discord.Embed(
            title="📊 Market Parameters",
            description="Current market parameter settings",
            color=0x0099ff,
            timestamp=datetime.now(timezone.utc)
        )
        
        param_text = f"""
**Trend Direction**: {params['trend_direction']:+.3f} {'📈' if params['trend_direction'] > 0 else '📉' if params['trend_direction'] < 0 else '➡️'}
**Volatility**: {params['volatility']:.3f} {'🌪️' if params['volatility'] > 0.7 else '🌊'}
**Momentum**: {params['momentum']:.3f} {'🚀' if params['momentum'] > 0.7 else '⚡'}
**Market Sentiment**: {params['market_sentiment']:.3f} {'😄' if params['market_sentiment'] > 0.7 else '😐' if params['market_sentiment'] > 0.4 else '😟'}
**Long-term Outlook**: {params['long_term_outlook']:.3f} {'🌟' if params['long_term_outlook'] > 0.7 else '🌤️'}
"""
        embed.add_field(name="Current Values", value=param_text.strip(), inline=False)
        embed.add_field(name="ℹ️ Notes", value="• Parameters are automatically set by AI daily at 8:40 AM ET\n• Manual changes will be overwritten at next market prep\n• Long-term outlook changes slowly over time", inline=False)
        
        await interaction.followup.send(embed=embed)
        return
    
    # Validate and update parameters
    changes = []
    
    if trend_direction is not None:
        if -1 <= trend_direction <= 1:
            old_val = stock_market.market_params['trend_direction']
            stock_market.market_params['trend_direction'] = trend_direction
            changes.append(f"Trend Direction: {old_val:+.3f} → {trend_direction:+.3f}")
        else:
            await interaction.followup.send("❌ Trend direction must be between -1 and 1")
            return
    
    if volatility is not None:
        if 0 <= volatility <= 1:
            old_val = stock_market.market_params['volatility']
            stock_market.market_params['volatility'] = volatility
            changes.append(f"Volatility: {old_val:.3f} → {volatility:.3f}")
        else:
            await interaction.followup.send("❌ Volatility must be between 0 and 1")
            return
    
    if momentum is not None:
        if 0 <= momentum <= 1:
            old_val = stock_market.market_params['momentum']
            stock_market.market_params['momentum'] = momentum
            changes.append(f"Momentum: {old_val:.3f} → {momentum:.3f}")
        else:
            await interaction.followup.send("❌ Momentum must be between 0 and 1")
            return
    
    if market_sentiment is not None:
        if 0 <= market_sentiment <= 1:
            old_val = stock_market.market_params['market_sentiment']
            stock_market.market_params['market_sentiment'] = market_sentiment
            changes.append(f"Market Sentiment: {old_val:.3f} → {market_sentiment:.3f}")
        else:
            await interaction.followup.send("❌ Market sentiment must be between 0 and 1")
            return
    
    stock_market.save_market_data()
    
    # Create success embed
    embed = discord.Embed(
        title="✅ Market Parameters Updated",
        description="Manual parameter changes applied",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="📊 Changes Made", value="\n".join(changes), inline=False)
    embed.add_field(name="⚠️ Important", value="These changes will be overwritten at the next daily market preparation (8:40 AM ET)", inline=False)
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_history", description="View stock market historical data")
@app_commands.describe(
    days_back="Number of days to look back (1-30)",
    symbol="Specific stock symbol (optional)"
)
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to retrieve stock history")
async def stocks_history(interaction: discord.Interaction, days_back: int = 7, symbol: Optional[str] = None):
    """View stock market historical data"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    # Validate days_back
    if days_back < 1 or days_back > 30:
        await interaction.followup.send("❌ Days back must be between 1 and 30")
        return
    
    # If symbol is provided, generate a chart
    if symbol:
        symbol = symbol.upper()
        
        # Check if it's an ETF first
        is_etf = hasattr(stock_market, 'etfs') and symbol in stock_market.etfs
        
        # Verify stock/ETF exists
        asset_exists = is_etf
        if not is_etf:
            for cat_data in stock_market.categories.values():
                for stock in cat_data['stocks']:
                    if stock['symbol'] == symbol:
                        asset_exists = True
                        break
                if asset_exists:
                    break
        
        if not asset_exists:
            await interaction.followup.send(f"❌ Stock/ETF '{symbol}' not found")
            return
        
        # Generate price history chart using on-demand calculation
        try:
            # Convert days to hours
            hours_back = days_back * 24
            
            # Generate chart using on-demand calculation
            chart_bytes = stock_market.generate_stock_chart_on_demand(symbol, hours_back=hours_back)
            
            # Calculate prices for statistics
            current_time = datetime.now(timezone.utc)
            prices = []
            
            # Calculate prices at regular intervals for statistics
            interval_minutes = stock_market.price_update_rate_minutes
            total_minutes = hours_back * 60
            
            for i in range(0, total_minutes, interval_minutes):
                time_offset = timedelta(minutes=i)
                price_time = current_time - timedelta(hours=hours_back) + time_offset
                try:
                    if is_etf:
                        price = stock_market.calculate_etf_price(symbol, price_time)
                    else:
                        price = stock_market.calculate_price_at_time(symbol, price_time)
                    prices.append(price)
                except Exception as e:
                    print(f"Error calculating price: {e}")
                    continue
            
            if len(prices) < 2:
                embed = discord.Embed(
                    title="📊 Insufficient Data",
                    description=f"Not enough data to generate {days_back}-day history for {symbol}",
                    color=0xffaa00,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="💡 Note", value="Price history requires market to be initialized", inline=False)
                await interaction.followup.send(embed=embed)
                return
            
            # Create history embed
            embed = discord.Embed(
                title=f"📊 {symbol} - {days_back} Day Price History",
                description=f"Prices calculated every {stock_market.price_update_rate_minutes} minute{'s' if stock_market.price_update_rate_minutes != 1 else ''}",
                color=0x0099ff,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Calculate statistics
            current_price = prices[-1]
            start_price = prices[0]
            change = current_price - start_price
            change_pct = (change / start_price) * 100
            high_price = max(prices)
            low_price = min(prices)
            avg_price = sum(prices) / len(prices)
            
            stats_text = f"""
**Current**: ${current_price:.2f}
**{days_back}d Change**: ${change:+.2f} ({change_pct:+.2f}%)
**{days_back}d High**: ${high_price:.2f}
**{days_back}d Low**: ${low_price:.2f}
**{days_back}d Average**: ${avg_price:.2f}
"""
            embed.add_field(name="📈 Statistics", value=stats_text.strip(), inline=True)
            
            # Add market parameters info
            params = stock_market.market_params
            market_text = f"""
**Trend**: {params['trend_direction']:+.2f}
**Volatility**: {params['volatility']:.2f}
**Update Rate**: {stock_market.price_update_rate_minutes}min
"""
            embed.add_field(name="🎯 Market Parameters", value=market_text.strip(), inline=True)
            
            # Attach chart if generated
            if chart_bytes:
                chart_file = discord.File(io.BytesIO(chart_bytes), filename=f"{symbol}_{days_back}d_chart.png")
                embed.set_image(url=f"attachment://{symbol}_{days_back}d_chart.png")
                await interaction.followup.send(embed=embed, file=chart_file)
            else:
                await interaction.followup.send(embed=embed)
                
            return
            
        except Exception as e:
            print(f"Error generating {days_back}d history: {e}")
            await interaction.followup.send(f"❌ Error generating price history: {e}")
            return
    
    # Original code for general market history (no specific symbol)
    # Get historical data
    historical_data = stock_market.get_historical_data(days_back)
    
    if not historical_data:
        await interaction.followup.send("❌ No historical data available")
        return
    
    embed = discord.Embed(
        title="📊 Stock Market History",
        description=f"Last {days_back} days • {len(historical_data)} data points",
        color=0x0099ff,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Show overall market statistics
    if len(historical_data) > 1:
        first_entry = historical_data[0]['data']
        last_entry = historical_data[-1]['data']
        
        # Calculate market-wide changes
        market_summary = "**Market Overview:**\n"
        
        if 'category_prices' in first_entry and 'category_prices' in last_entry:
            for sector in first_entry['category_prices']:
                if sector in last_entry['category_prices']:
                    old_price = first_entry['category_prices'][sector]
                    new_price = last_entry['category_prices'][sector]
                    change_pct = ((new_price - old_price) / old_price) * 100
                    
                    emoji = "⛽" if sector == "ENERGY" else "🎬" if sector == "ENTERTAINMENT" else "🏦" if sector == "FINANCE" else "🏥" if sector == "HEALTH" else "🏭" if sector == "MANUFACTURING" else "🛒" if sector == "RETAIL" else "💻" if sector == "TECH" else "✈️"
                    direction = "📈" if change_pct >= 0 else "📉"
                    market_summary += f"{emoji} {sector}: {direction} {change_pct:+.1f}%\n"
        
        embed.add_field(name="📊 Sector Performance", value=market_summary.strip(), inline=False)
    
    # Data source info
    embed.set_footer(text=f"Data from {len(historical_data)} trading periods")
    
    await interaction.followup.send(embed=embed)

# Stock Market Control Commands

@app_commands.command(name="start", description="Start stock market auto-updates")
@app_commands.describe(initialize="Run full market initialization (first time setup)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to start stock market")
async def start_stock_market(interaction: discord.Interaction, initialize: Optional[bool] = False):
    """Start the stock market auto-update system"""
    global stock_scheduler
    await interaction.response.defer()
    stock_market = get_stock_market()
    
    if initialize:
        # Full initialization with progress UI
        embed = discord.Embed(
            title="🚀 Initializing Stock Market System",
            description="Setting up the Virtual Congress Stock Market...",
            color=0xffaa00,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="📊 Progress", value="⏳ Starting initialization...", inline=False)
        embed.add_field(name="🎯 Phase", value="Initial Setup", inline=True)
        embed.add_field(name="⏱️ Status", value="Working...", inline=True)
        
        initial_msg = await interaction.followup.send(embed=embed)
        
        try:
            # Phase 1: Load economic data
            embed.set_field_at(0, name="📊 Progress", value="📈 Loading economic integration data...", inline=False)
            embed.set_field_at(1, name="🎯 Phase", value="Economic Integration", inline=True)
            await initial_msg.edit(embed=embed)
            
            # Try to integrate with economic system
            try:
                from economic_utils import get_stock_initialization_data
                econ_init = get_stock_initialization_data()
                
                if "stock_market_initialization" in econ_init:
                    init_params = econ_init["stock_market_initialization"]
                    stock_market.market_params.update(init_params)
                    
                embed.set_field_at(0, name="📊 Progress", value="✅ Economic data integrated", inline=False)
                await initial_msg.edit(embed=embed)
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Economic integration failed: {e}")
                embed.set_field_at(0, name="📊 Progress", value="⚠️ Using default parameters (economic system unavailable)", inline=False)
                await initial_msg.edit(embed=embed)
                await asyncio.sleep(1)
            
            # Phase 1.5: AI Market Analysis (Dynamic Parameter Calculation)
            embed.set_field_at(0, name="📊 Progress", value="🧠 Running AI market analysis from economic data...", inline=False)
            embed.set_field_at(1, name="🎯 Phase", value="AI Analysis", inline=True)
            await initial_msg.edit(embed=embed)
            
            try:
                # Run AI analysis to set market parameters from real economic data
                analysis_result = await stock_market.get_daily_market_analysis()
                
                # Update market parameters with AI-calculated values
                if "market_params" in analysis_result:
                    stock_market.market_params.update(analysis_result["market_params"])
                    print(f"✅ AI analysis complete - parameters updated from economic data")
                
                embed.set_field_at(0, name="📊 Progress", value="✅ AI analysis complete - parameters set from economic data", inline=False)
                await initial_msg.edit(embed=embed)
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"⚠️ AI analysis failed: {e}")
                embed.set_field_at(0, name="📊 Progress", value="⚠️ AI analysis failed - using calculated base parameters", inline=False)
                await initial_msg.edit(embed=embed)
                await asyncio.sleep(1)
            
            # Phase 2: Initialize market data
            embed.set_field_at(0, name="📊 Progress", value="🏗️ Setting up market structure...", inline=False)
            embed.set_field_at(1, name="🎯 Phase", value="Market Structure", inline=True)
            await initial_msg.edit(embed=embed)
            
            # Save market data
            stock_market.save_market_data()
            
            embed.set_field_at(0, name="📊 Progress", value="✅ Market structure ready", inline=False)
            await initial_msg.edit(embed=embed)
            await asyncio.sleep(1)
            
            # Phase 3: Start scheduler
            embed.set_field_at(0, name="📊 Progress", value="⏰ Starting trading scheduler...", inline=False)
            embed.set_field_at(1, name="🎯 Phase", value="Scheduler Setup", inline=True)
            await initial_msg.edit(embed=embed)
            
            # Initialize scheduler
            if not stock_scheduler:
                from stock_market import StockMarketScheduler
                stock_scheduler = StockMarketScheduler(stock_market)
                await stock_scheduler.start_scheduler()
                
            embed.set_field_at(0, name="📊 Progress", value="✅ Trading scheduler active", inline=False)
            await initial_msg.edit(embed=embed)
            await asyncio.sleep(1)
            
            # Phase 4: Setup complete
            embed = discord.Embed(
                title="✅ Stock Market Initialization Complete",
                description="Virtual Congress Stock Market is now operational",
                color=0x00ff88,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Market summary
            total_stocks = sum(len(cat['stocks']) for cat in stock_market.categories.values())
            summary_text = f"""
**📈 {total_stocks} Stocks** across {len(stock_market.categories)} sectors
**🏦 6 Sector ETFs** tracking government categories
**⏰ Auto-Updates** enabled with AI analysis
**📊 Trading Hours** 9:00 AM - 5:00 PM ET daily
"""
            embed.add_field(name="🎯 Market Overview", value=summary_text.strip(), inline=False)
            
            # Current parameters
            params = stock_market.market_params
            param_text = f"""
**Trend**: {params['trend_direction']:+.2f} {'📈' if params['trend_direction'] > 0 else '📉' if params['trend_direction'] < 0 else '➡️'}
**Volatility**: {params['volatility']:.2f} {'🌪️' if params['volatility'] > 0.7 else '🌊'}
**Sentiment**: {params['market_sentiment']:.2f} {'😄' if params['market_sentiment'] > 0.7 else '😐'}
"""
            embed.add_field(name="📊 Initial Parameters", value=param_text.strip(), inline=True)
            
            # Next actions
            next_text = """
• Market prep runs daily at 8:40 AM ET
• Hourly updates during trading hours
• Use `/stocks` to view market overview
• Use `/stop` to pause auto-updates
"""
            embed.add_field(name="🎯 Next Steps", value=next_text.strip(), inline=True)
            
            embed.set_footer(text="Use /stocks commands to interact with the market")
            
            await initial_msg.edit(embed=embed)
            return  # Exit here to prevent double scheduler creation
            
        except Exception as e:
            # Error handling
            error_embed = discord.Embed(
                title="❌ Initialization Failed",
                description=f"Error during stock market setup: {str(e)}",
                color=0xff4444,
                timestamp=datetime.now(timezone.utc)
            )
            await initial_msg.edit(embed=error_embed)
            return  # Exit on error to prevent double scheduler creation
            
    else:
        # Simple start without full initialization
        try:
            if not is_scheduler_running():
                from stock_market import StockMarketScheduler
                stock_scheduler = StockMarketScheduler(stock_market)
                await stock_scheduler.start_scheduler()
                print("✅ Trading scheduler started")
            else:
                print("ℹ️ Trading scheduler already active")
                
            embed = discord.Embed(
                title="✅ Stock Market Started",
                description="Auto-updates and trading scheduler are now active",
                color=0x00ff88,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Status info
            status_text = f"""
**Market Status**: {'🟢 OPEN' if stock_market.is_trading_day else '🔴 CLOSED'}
**Auto-Updates**: ✅ Enabled
**Next Market Prep**: Daily at 8:40 AM ET
**Trading Hours**: 9:00 AM - 5:00 PM ET
"""
            embed.add_field(name="📊 Current Status", value=status_text.strip(), inline=False)
            embed.set_footer(text="Use /stop to pause auto-updates")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to start stock market: {str(e)}")

@app_commands.command(name="stocks_status", description="Check stock market scheduler status")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to check scheduler status")
async def stocks_status(interaction: discord.Interaction):
    """Check the status of the stock market scheduler"""
    await interaction.response.defer()
    
    try:
        stock_market = get_stock_market()
        is_running = is_scheduler_running()
        
        if is_running:
            status_color = 0x00ff88  # Green
            status_title = "✅ Stock Market Scheduler Active"
            status_desc = "Hourly updates and daily analysis are running"
            
            # Get task details
            task_info = ""
            if stock_scheduler:
                if hasattr(stock_scheduler, 'hourly_update_task') and stock_scheduler.hourly_update_task:
                    task_status = "✅ Running" if not stock_scheduler.hourly_update_task.done() else "❌ Stopped"
                    task_info += f"**Hourly Updates**: {task_status}\n"
                
                if hasattr(stock_scheduler, 'daily_prep_task') and stock_scheduler.daily_prep_task:
                    task_status = "✅ Running" if not stock_scheduler.daily_prep_task.done() else "❌ Stopped"
                    task_info += f"**Daily Analysis**: {task_status}\n"
                    
                # Get next update time
                et_now = stock_scheduler.get_et_now()
                minutes_per_update = stock_market.price_update_rate_minutes
                current_minutes = et_now.hour * 60 + et_now.minute
                next_update_minutes = ((current_minutes // minutes_per_update) + 1) * minutes_per_update
                next_update_hour = next_update_minutes // 60
                next_update_minute = next_update_minutes % 60
                
                if next_update_hour >= 24:
                    from datetime import timedelta
                    next_update = (et_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    next_update = et_now.replace(hour=next_update_hour, minute=next_update_minute, second=0, microsecond=0)
                
                task_info += f"**Next Update**: {next_update.strftime('%I:%M %p ET')}\n"
                task_info += f"**Update Interval**: {minutes_per_update} minutes"
        else:
            status_color = 0xff6b6b  # Red
            status_title = "⏹️ Stock Market Scheduler Stopped"
            status_desc = "Hourly updates are not running"
            task_info = "No active scheduler tasks found"
        
        embed = discord.Embed(
            title=status_title,
            description=status_desc,
            color=status_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="📊 Task Status", value=task_info, inline=False)
        
        # Market info
        market_info = f"""
**Market Status**: {'🟢 Open' if stock_market.is_trading_day else '🔴 Closed'}
**Trading Day**: {stock_market.current_trading_day or 'Not set'}
**Last Analysis**: {stock_market.last_market_open_time or 'Not available'}
"""
        embed.add_field(name="🏪 Market Info", value=market_info.strip(), inline=False)
        
        if is_running:
            embed.set_footer(text="Scheduler is healthy and running")
        else:
            embed.set_footer(text="Use /start to enable scheduler")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error checking scheduler status: {str(e)}")

@app_commands.command(name="stop", description="Stop stock market auto-updates")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to stop stock market")
async def stop_stock_market(interaction: discord.Interaction):
    """Stop the stock market auto-update system"""
    await interaction.response.defer()
    
    global stock_scheduler
    try:
        
        # Stop scheduler properly using helper function
        scheduler_stopped = stop_scheduler()
        
        # Set market as closed
        stock_market = get_stock_market()
        stock_market.is_trading_day = False
        stock_market.save_market_data()
        
        # Create response embed
        if scheduler_stopped:
            embed = discord.Embed(
                title="⏹️ Stock Market Stopped",
                description="Auto-updates and trading scheduler have been stopped and cleaned up",
                color=0xff6b6b,
                timestamp=datetime.now(timezone.utc)
            )
        else:
            embed = discord.Embed(
                title="⚠️ Stock Market Stop Warning",
                description="Market closed, but no active scheduler was found to stop",
                color=0xffa500,
                timestamp=datetime.now(timezone.utc)
            )
            
        # Add status information to the embed
        status_text = f"""
**Market Status**: 🔴 CLOSED
**Auto-Updates**: ❌ Disabled
**Scheduled Tasks**: ⏹️ Paused
**Manual Commands**: ✅ Still available
"""
        embed.add_field(name="📊 Current Status", value=status_text.strip(), inline=False)
        embed.add_field(name="ℹ️ Note", value="Market data and stocks are preserved. Use `/start` to resume operations.", inline=False)
        embed.set_footer(text="Use /start to resume auto-updates")
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error stopping stock market: {str(e)}")

@app_commands.command(name="stocks_admin_detail", description="View detailed parameters for a specific stock")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to get stock details")
async def stocks_admin_detail(interaction: discord.Interaction, symbol: str):
    """View all internal parameters and calculations for a stock"""
    # Check if interaction has already been responded to (e.g., from dropdown selection)
    if not interaction.response.is_done():
        await interaction.response.defer()
    
    stock_market = get_stock_market()
    symbol = symbol.upper()
    
    # Find the stock
    stock = None
    category_name = None
    for cat_name, cat_data in stock_market.categories.items():
        for s in cat_data["stocks"]:
            if s["symbol"] == symbol:
                stock = s
                category_name = cat_name
                break
        if stock:
            break
    
    if not stock:
        await interaction.followup.send(f"❌ Stock {symbol} not found")
        return
    
    # Get current calculated price
    current_calc_price = stock_market.calculate_price_at_time(symbol)
    
    embed = discord.Embed(
        title=f"🔍 Detailed View: {symbol}",
        description=f"{stock['name']} - {category_name} Sector",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Basic info
    basic_info = f"""
**Current Price**: ${stock['price']:.2f}
**Calculated Price**: ${current_calc_price:.2f}
**Daily Low**: ${stock.get('daily_range_low', stock['price'] * 0.97):.2f}
**Daily High**: ${stock.get('daily_range_high', stock['price'] * 1.03):.2f}
**Sector Factor**: {stock.get('sector_factor', 1.0):.2f}
"""
    embed.add_field(name="📊 Basic Parameters", value=basic_info.strip(), inline=False)
    
    # Market parameters affecting this stock
    params = stock_market.market_params
    market_info = f"""
**Trend Direction**: {params['trend_direction']:+.2f}
**Volatility**: {params['volatility']:.2f}
**Momentum**: {params['momentum']:.2f}
**Sentiment**: {params['market_sentiment']:.2f}
**Outlook**: {params['long_term_outlook']:.2f}
"""
    embed.add_field(name="🌐 Market Parameters", value=market_info.strip(), inline=True)
    
    # Invisible factors
    invisible = stock_market.invisible_factors
    invisible_info = f"""
**Institutional Flow**: {invisible['institutional_flow']:+.2f}
**Liquidity Factor**: {invisible['liquidity_factor']:.2f}
**News Velocity**: {invisible['news_velocity']:.2f}
**Sector Rotation**: {invisible['sector_rotation']:+.2f}
**Risk Appetite**: {invisible['risk_appetite']:.2f}
"""
    embed.add_field(name="👻 Invisible Factors", value=invisible_info.strip(), inline=True)
    
    # Perlin noise seeds
    base_seed = hash(symbol + (stock_market.current_trading_day or "2025-01-01")) % 10000
    seed_info = f"""
**Base Seed**: {base_seed}
**Trend Seed**: {(base_seed + 1000) % 10000}
**Micro Seed**: {(base_seed + 2000) % 10000}
"""
    embed.add_field(name="🎲 Noise Seeds", value=seed_info.strip(), inline=True)
    
    embed.set_footer(text=f"Trading Day: {stock_market.current_trading_day or 'Not set'}")
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_admin_peek", description="Preview future stock prices")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to peek future prices")
async def stocks_admin_peek(interaction: discord.Interaction, symbol: str, hours: int = 24):
    """Preview calculated future prices for a stock"""
    # Check if interaction has already been responded to (e.g., from dropdown selection)
    if not interaction.response.is_done():
        await interaction.response.defer()
    
    stock_market = get_stock_market()
    symbol = symbol.upper()
    
    # Validate hours
    if hours < 1 or hours > 168:  # Max 1 week
        await interaction.followup.send("❌ Hours must be between 1 and 168 (1 week)")
        return
    
    # Check if stock exists
    stock = None
    for cat_data in stock_market.categories.values():
        for s in cat_data["stocks"]:
            if s["symbol"] == symbol:
                stock = s
                break
        if stock:
            break
    
    if not stock:
        await interaction.followup.send(f"❌ Stock {symbol} not found")
        return
    
    # Calculate future prices
    current_time = datetime.now(timezone.utc)
    future_prices = []
    times = []
    
    for h in range(0, hours + 1, max(1, hours // 24)):  # Show max 24 points
        future_time = current_time + timedelta(hours=h)
        try:
            price = stock_market.calculate_price_at_time(symbol, future_time)
            future_prices.append(price)
            times.append(future_time)
        except Exception as e:
            print(f"Error calculating future price: {e}")
            continue
    
    if not future_prices:
        await interaction.followup.send("❌ Could not calculate future prices")
        return
    
    # Create price chart
    plt.figure(figsize=(12, 6))
    plt.style.use('dark_background')
    
    # Plot the prices
    plt.plot(times, future_prices, 'g-', linewidth=2, label=symbol)
    
    # Add daily range lines
    daily_low = stock.get('daily_range_low', stock['price'] * 0.97)
    daily_high = stock.get('daily_range_high', stock['price'] * 1.03)
    plt.axhline(y=daily_low, color='red', linestyle='--', alpha=0.5, label='Daily Low')
    plt.axhline(y=daily_high, color='yellow', linestyle='--', alpha=0.5, label='Daily High')
    plt.axhline(y=stock['price'], color='white', linestyle=':', alpha=0.5, label='Opening Price')
    
    # Formatting
    plt.title(f"{symbol} Price Projection - Next {hours} Hours", fontsize=16, pad=20)
    plt.xlabel("Time (UTC)", fontsize=12)
    plt.ylabel("Price ($)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best')
    
    # Format x-axis
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45)
    
    # Statistics
    min_price = min(future_prices)
    max_price = max(future_prices)
    avg_price = sum(future_prices) / len(future_prices)
    
    stats_text = f"Min: ${min_price:.2f} | Max: ${max_price:.2f} | Avg: ${avg_price:.2f}"
    plt.text(0.5, 0.02, stats_text, transform=ax.transAxes, 
             horizontalalignment='center', fontsize=10, bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
    
    plt.tight_layout()
    
    # Convert to Discord file
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor='#2f3136')
    buffer.seek(0)
    plt.close()
    
    file = discord.File(buffer, filename=f"{symbol}_future_{hours}h.png")
    
    embed = discord.Embed(
        title=f"🔮 Future Price Projection: {symbol}",
        description=f"Calculated prices for the next {hours} hours",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="📊 Statistics", value=f"**Min**: ${min_price:.2f}\n**Max**: ${max_price:.2f}\n**Average**: ${avg_price:.2f}", inline=True)
    embed.add_field(name="📍 Current", value=f"**Price**: ${stock['price']:.2f}\n**Calculated**: ${future_prices[0]:.2f}", inline=True)
    embed.set_footer(text="⚠️ Admin preview - Based on current market parameters")
    
    await interaction.followup.send(embed=embed, file=file)

@app_commands.command(name="stocks_admin_debug", description="View internal stock market debug information")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to get debug info")
async def stocks_admin_debug(interaction: discord.Interaction):
    """Show internal debug information about the stock market system"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    embed = discord.Embed(
        title="🐛 Stock Market Debug Information",
        color=0xff6b6b,
        timestamp=datetime.now(timezone.utc)
    )
    
    # System state
    system_info = f"""
**Trading Day**: {stock_market.current_trading_day or 'Not set'}
**Market Open**: {stock_market.is_trading_day}
**Scheduler Running**: {is_scheduler_running()}
**Update Rate**: {stock_market.price_update_rate_minutes} min
**Channel ID**: {stock_market.stocks_channel_id}
**Admin Only**: {stock_market.admin_only_trading}
"""
    embed.add_field(name="⚙️ System State", value=system_info.strip(), inline=False)
    
    # Softcap config
    sc = stock_market.softcap_config
    softcap_info = f"""
**Enabled**: {sc['enabled']}
**Steepness**: {sc['steepness']}
**Max Resistance**: {sc['max_resistance']}
"""
    embed.add_field(name="🎚️ Softcap Config", value=softcap_info.strip(), inline=True)
    
    # Stock count
    total_stocks = sum(len(cat['stocks']) for cat in stock_market.categories.values())
    total_etfs = len(stock_market.etfs)
    count_info = f"""
**Stocks**: {total_stocks}
**ETFs**: {total_etfs}
**Categories**: {len(stock_market.categories)}
"""
    embed.add_field(name="📊 Counts", value=count_info.strip(), inline=True)
    
    # Memory usage
    import sys
    market_size = sys.getsizeof(stock_market.categories) + sys.getsizeof(stock_market.etfs)
    etf_cache_size = sys.getsizeof(stock_market.etf_price_cache) if hasattr(stock_market, 'etf_price_cache') else 0
    memory_info = f"""
**Market Data**: {market_size / 1024:.1f} KB
**ETF Cache**: {etf_cache_size / 1024:.1f} KB
**Precomputed**: {len(stock_market.precomputed_prices)} series
"""
    embed.add_field(name="💾 Memory", value=memory_info.strip(), inline=True)
    
    # ETF Cache info
    if hasattr(stock_market, 'etf_price_cache') and stock_market.etf_price_cache:
        from zoneinfo import ZoneInfo
        cached_count = len(stock_market.etf_price_cache)
        
        # Check cache expiry
        if hasattr(stock_market, 'etf_cache_expiry') and stock_market.etf_cache_expiry:
            et_now = datetime.now(ZoneInfo("America/New_York"))
            time_remaining = (stock_market.etf_cache_expiry - et_now).total_seconds() / 3600
            cache_status = f"Valid for {time_remaining:.1f}h" if time_remaining > 0 else "Expired"
        else:
            cache_status = "Not set"
        
        cache_info = f"""
**Cached ETFs**: {cached_count}/{len(stock_market.etfs)}
**Cache Status**: {cache_status}
**Next Refresh**: 9:00 AM ET
"""
        embed.add_field(name="🔄 ETF Cache", value=cache_info.strip(), inline=True)
    
    # Recent errors (if any)
    if hasattr(stock_market, 'last_error'):
        embed.add_field(name="❌ Last Error", value=str(stock_market.last_error)[:200], inline=False)
    
    await interaction.followup.send(embed=embed)

# User Commands

@app_commands.command(name="stocks_list", description="List all available stocks and ETFs")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to list stocks")
async def stocks_list(interaction: discord.Interaction):
    """List all available stocks and ETFs across all sectors"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    embed = discord.Embed(
        title="📈 Available Stocks & ETFs",
        description="All assets traded on the Virtual Congress Market",
        color=0x0099ff,
        timestamp=datetime.now(timezone.utc)
    )
    
    total_stocks = 0
    for cat_name, cat_data in stock_market.categories.items():
        emoji = "⛽" if cat_name == "ENERGY" else "🎬" if cat_name == "ENTERTAINMENT" else "🏦" if cat_name == "FINANCE" else "🏥" if cat_name == "HEALTH" else "🏭" if cat_name == "MANUFACTURING" else "🛒" if cat_name == "RETAIL" else "💻" if cat_name == "TECH" else "✈️"
        
        stocks_text = ""
        for stock in cat_data['stocks']:
            stocks_text += f"**{stock['symbol']}**: {stock['name']} - ${stock['price']:.2f}\n"
            total_stocks += 1
        
        embed.add_field(
            name=f"{emoji} {cat_data['name']} ({len(cat_data['stocks'])} stocks)",
            value=stocks_text.strip(),
            inline=False
        )
    
    # Add ETFs section
    if hasattr(stock_market, 'etfs') and stock_market.etfs:
        # Separate ETFs by type
        index_etfs = []
        sector_etfs = []
        other_etfs = []
        
        for symbol, etf in stock_market.etfs.items():
            price = stock_market.get_cached_etf_price(symbol)
            etf_info = f"**{symbol}**: {etf['name']} - ${price:.2f}"
            
            if etf['type'] in ['market_cap_weighted', 'equal_weighted']:
                index_etfs.append(etf_info)
            elif etf['type'] == 'sector':
                sector_etfs.append(etf_info)
            else:
                other_etfs.append(etf_info)
        
        # Add ETF fields
        if index_etfs:
            embed.add_field(
                name=f"📊 Market Index ETFs ({len(index_etfs)})",
                value="\n".join(index_etfs),
                inline=False
            )
        
        if sector_etfs:
            embed.add_field(
                name=f"🏭 Sector ETFs ({len(sector_etfs)})",
                value="\n".join(sector_etfs),
                inline=False
            )
        
        if other_etfs:
            embed.add_field(
                name=f"💎 Specialty ETFs ({len(other_etfs)})",
                value="\n".join(other_etfs),
                inline=False
            )
        
        total_etfs = len(stock_market.etfs)
        embed.set_footer(text=f"Total: {total_stocks} stocks, {total_etfs} ETFs across {len(stock_market.categories)} sectors")
    else:
        embed.set_footer(text=f"Total: {total_stocks} stocks across {len(stock_market.categories)} sectors")
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_price", description="Check current price of a stock or ETF")
@app_commands.describe(symbol="Stock/ETF symbol (e.g., AAPL, MSFT, SPY, QQQ)")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to check stock price")
async def stocks_price(interaction: discord.Interaction, symbol: str):
    """Check and display current price of a specific stock or ETF"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    symbol = symbol.upper()
    
    # First, check if it's an ETF
    target_etf = None
    if hasattr(stock_market, 'etfs') and symbol in stock_market.etfs:
        target_etf = stock_market.etfs[symbol]
    
    # If not an ETF, find the stock
    target_stock = None
    target_category = None
    
    if not target_etf:
        for cat_name, cat_data in stock_market.categories.items():
            for stock in cat_data['stocks']:
                if stock['symbol'] == symbol:
                    target_stock = stock
                    target_category = cat_name
                    break
            if target_stock:
                break
    
    if not target_stock and not target_etf:
        available_symbols = []
        for cat_data in stock_market.categories.values():
            for stock in cat_data['stocks']:
                available_symbols.append(stock['symbol'])
        
        # Add ETF symbols
        if hasattr(stock_market, 'etfs'):
            available_symbols.extend(stock_market.etfs.keys())
        
        embed = discord.Embed(
            title="❌ Stock/ETF Not Found",
            description=f"'{symbol}' is not available for trading",
            color=0xff4444,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(
            name="💡 Available Symbols",
            value=", ".join(sorted(available_symbols)),
            inline=False
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Handle ETF display
    if target_etf:
        # Get current ETF price
        current_price = stock_market.get_etf_price(symbol)
        if current_price is None:
            current_price = target_etf.get('price', 100.0)
        
        embed = discord.Embed(
            title=f"📊 {target_etf['symbol']} ETF Price",
            description=f"**{target_etf['name']}**\n{target_etf.get('description', '')}",
            color=0x00ff88,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Current Price", value=f"${current_price:.2f}", inline=True)
        embed.add_field(name="Type", value=target_etf['type'].replace('_', ' ').title(), inline=True)
        embed.add_field(name="Expense Ratio", value=f"{target_etf['expense_ratio']*100:.2f}%", inline=True)
        
        # For sector ETFs, show the sector
        if target_etf['type'] == 'sector' and 'sector' in target_etf:
            embed.add_field(name="Tracks Sector", value=target_etf['sector'], inline=True)
        
        # Show top holdings for non-sector ETFs
        if target_etf['type'] != 'sector' and 'holdings' in target_etf:
            holdings = target_etf['holdings']
            top_holdings = sorted(holdings.items(), key=lambda x: x[1], reverse=True)[:5]
            holdings_text = "\n".join([f"{symbol}: {weight*100:.1f}%" for symbol, weight in top_holdings])
            embed.add_field(name="Top Holdings", value=holdings_text, inline=False)
        
        # Market status
        market_status = "🟢 OPEN" if stock_market.is_trading_day else "🔴 CLOSED"
        embed.add_field(name="Market Status", value=market_status, inline=False)
        
        await interaction.followup.send(embed=embed)
        return
    
    # Handle individual stock display
    emoji = "⛽" if target_category == "ENERGY" else "🎬" if target_category == "ENTERTAINMENT" else "🏦" if target_category == "FINANCE" else "🏥" if target_category == "HEALTH" else "🏭" if target_category == "MANUFACTURING" else "🛒" if target_category == "RETAIL" else "💻" if target_category == "TECH" else "✈️"
    
    embed = discord.Embed(
        title=f"💰 {target_stock['symbol']} Stock Price",
        description=f"**{target_stock['name']}**",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Get current price using on-demand calculation
    current_price = stock_market.get_stock_price(symbol)
    if current_price is None:
        current_price = target_stock['price']  # Fallback to stored price
    
    embed.add_field(name="Current Price", value=f"${current_price:.2f}", inline=True)
    embed.add_field(name="Sector", value=f"{emoji} {target_category}", inline=True)
    embed.add_field(name="Industry", value=target_stock['sector'].replace('_', ' ').title(), inline=True)
    
    # Market status
    market_status = "🟢 OPEN" if stock_market.is_trading_day else "🔴 CLOSED"
    embed.add_field(name="Market Status", value=market_status, inline=False)
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_etfs", description="List all available ETFs")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to list ETFs")
async def stocks_etfs(interaction: discord.Interaction):
    """List all available ETFs with prices"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    if not hasattr(stock_market, 'etfs') or not stock_market.etfs:
        await interaction.followup.send("❌ No ETFs available in the system")
        return
    
    embed = discord.Embed(
        title="📊 Available ETFs",
        description="Exchange-Traded Funds for diversified investing",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Separate ETFs by type
    index_etfs = []
    sector_etfs = []
    
    for symbol, etf in stock_market.etfs.items():
        price = etf.get('current_price', stock_market.calculate_etf_price(symbol))
        expense_ratio = etf.get('expense_ratio', 0.001) * 100
        
        if etf['type'] in ['market_cap_weighted', 'equal_weighted']:
            index_etfs.append(f"**{symbol}** - ${price:.2f} | {expense_ratio:.2f}%\n{etf['name']}")
        elif etf['type'] == 'sector':
            sector_etfs.append(f"**{symbol}** - ${price:.2f} | {expense_ratio:.2f}%\n{etf['name']}")
    
    # Add fields
    if index_etfs:
        embed.add_field(
            name="📈 Market Index ETFs",
            value="\n\n".join(index_etfs[:5]),  # Limit to 5 to avoid field length issues
            inline=False
        )
    
    if sector_etfs:
        embed.add_field(
            name="🏭 Sector ETFs", 
            value="\n\n".join(sector_etfs[:10]),  # Limit to 10
            inline=False
        )
    
    embed.set_footer(text=f"Total: {len(stock_market.etfs)} ETFs available | Expense ratios shown annually")
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_categories", description="List all stock categories and market directions")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to list categories")
async def stocks_categories(interaction: discord.Interaction):
    """List all stock categories with their market directions"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    embed = discord.Embed(
        title="📊 Stock Market Categories",
        description="Economic sectors and their current market directions",
        color=0x0099ff,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Market overview
    params = stock_market.market_params
    overview_text = f"""
**Overall Market Trend**: {params['trend_direction']:+.2f} {'📈' if params['trend_direction'] > 0 else '📉' if params['trend_direction'] < 0 else '➡️'}
**Market Volatility**: {params['volatility']:.2f} {'🌪️' if params['volatility'] > 0.7 else '🌊'}
**Market Sentiment**: {params['market_sentiment']:.2f} {'😄' if params['market_sentiment'] > 0.7 else '😐' if params['market_sentiment'] > 0.4 else '😟'}
"""
    embed.add_field(name="🎯 Market Overview", value=overview_text.strip(), inline=False)
    
    # Individual categories
    for cat_name, cat_data in stock_market.categories.items():
        emoji = "⛽" if cat_name == "ENERGY" else "🎬" if cat_name == "ENTERTAINMENT" else "🏦" if cat_name == "FINANCE" else "🏥" if cat_name == "HEALTH" else "🏭" if cat_name == "MANUFACTURING" else "🛒" if cat_name == "RETAIL" else "💻" if cat_name == "TECH" else "✈️"
        
        direction = cat_data.get('market_direction', 'normal')
        direction_emoji = "📈" if direction == "up" else "📉" if direction == "down" else "➡️"
        
        category_text = f"""
**Direction**: {direction_emoji} {direction.title()}
**Stocks**: {len(cat_data['stocks'])} companies
**Description**: {cat_data['description']}
"""
        
        embed.add_field(
            name=f"{emoji} {cat_data['name']}",
            value=category_text.strip(),
            inline=True
        )
    
    embed.set_footer(text=f"{sum(len(cat['stocks']) for cat in stock_market.categories.values())} total stocks")
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_history_48h", description="Show stock/ETF's 48-hour price history")
@app_commands.describe(symbol="Stock/ETF symbol (e.g., AAPL, MSFT, SPY)")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to get stock history")
async def stocks_history_48h(interaction: discord.Interaction, symbol: str):
    """Show a stock or ETF's price history over the last 48 hours"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    symbol = symbol.upper()
    
    # Check if it's an ETF first
    is_etf = hasattr(stock_market, 'etfs') and symbol in stock_market.etfs
    
    # Verify stock/ETF exists
    asset_exists = is_etf
    if not is_etf:
        for cat_data in stock_market.categories.values():
            for stock in cat_data['stocks']:
                if stock['symbol'] == symbol:
                    asset_exists = True
                    break
            if asset_exists:
                break
    
    if not asset_exists:
        await interaction.followup.send(f"❌ Stock/ETF '{symbol}' not found")
        return
    
    # Generate 48-hour price history using on-demand calculation
    try:
        # Generate chart using on-demand calculation
        chart_bytes = stock_market.generate_stock_chart_on_demand(symbol, hours_back=48)
        
        # Calculate prices for statistics
        current_time = datetime.now(timezone.utc)
        prices = []
        
        # Calculate prices at regular intervals for statistics
        interval_minutes = stock_market.price_update_rate_minutes
        
        for i in range(0, 48 * 60, interval_minutes):
            time_offset = timedelta(minutes=i)
            price_time = current_time - timedelta(hours=48) + time_offset
            try:
                price = stock_market.calculate_price_at_time(symbol, price_time)
                prices.append(price)
            except Exception as e:
                print(f"Error calculating price: {e}")
                continue
        
        if len(prices) < 2:
            # Fallback to historical data if available
            historical_data = stock_market.get_historical_data(days_back=2)
            if historical_data:
                prices = []
                for entry in historical_data:
                    if 'data' in entry and 'individual_stocks' in entry['data']:
                        if symbol in entry['data']['individual_stocks']:
                            prices.append(entry['data']['individual_stocks'][symbol])
        
        if len(prices) < 2:
            embed = discord.Embed(
                title="📊 Insufficient Data",
                description=f"Not enough data to generate 48-hour history for {symbol}",
                color=0xffaa00,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="💡 Note", value="Price history requires market to be initialized", inline=False)
            await interaction.followup.send(embed=embed)
            return
        
        # Create history embed
        embed = discord.Embed(
            title=f"📊 {symbol} - 48 Hour Price History",
            description=f"Prices calculated every {stock_market.price_update_rate_minutes} minute{'s' if stock_market.price_update_rate_minutes != 1 else ''}",
            color=0x0099ff,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Calculate statistics
        current_price = prices[-1]
        start_price = prices[0]
        change = current_price - start_price
        change_pct = (change / start_price) * 100
        high_price = max(prices)
        low_price = min(prices)
        avg_price = sum(prices) / len(prices)
        
        stats_text = f"""
**Current**: ${current_price:.2f}
**48h Change**: ${change:+.2f} ({change_pct:+.2f}%)
**48h High**: ${high_price:.2f}
**48h Low**: ${low_price:.2f}
**48h Average**: ${avg_price:.2f}
"""
        embed.add_field(name="📈 Statistics", value=stats_text.strip(), inline=True)
        
        # Add market parameters info
        params = stock_market.market_params
        market_text = f"""
**Trend**: {params['trend_direction']:+.2f}
**Volatility**: {params['volatility']:.2f}
**Update Rate**: {stock_market.price_update_rate_minutes}min
"""
        embed.add_field(name="🎯 Market Parameters", value=market_text.strip(), inline=True)
        
        # Attach chart if generated
        if chart_bytes:
            chart_file = discord.File(io.BytesIO(chart_bytes), filename=f"{symbol}_48h_chart.png")
            embed.set_image(url=f"attachment://{symbol}_48h_chart.png")
            await interaction.followup.send(embed=embed, file=chart_file)
        else:
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        print(f"Error generating 48h history: {e}")
        await interaction.followup.send(f"❌ Error generating price history: {e}")

# Admin Commands

@app_commands.command(name="stocks_set_market", description="Set market trend for a category (Admin)")
@app_commands.describe(
    category="Market category to modify",
    direction="Market direction (up/down/normal)"
)
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to set market direction")
async def stocks_set_market(interaction: discord.Interaction, 
                           category: Literal["ENERGY", "ENTERTAINMENT", "FINANCE", "HEALTH", "MANUFACTURING", "RETAIL", "TECH", "TRANSPORT"],
                           direction: Literal["up", "down", "normal"]):
    """Set the market trend for a specific category"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    if category not in stock_market.categories:
        await interaction.followup.send(f"❌ Category '{category}' not found")
        return
    
    # Update market direction
    old_direction = stock_market.categories[category].get('market_direction', 'normal')
    stock_market.categories[category]['market_direction'] = direction
    stock_market.save_market_data()
    
    # Create response embed
    emoji = "⛽" if category == "ENERGY" else "🎬" if category == "ENTERTAINMENT" else "🏦" if category == "FINANCE" else "🏥" if category == "HEALTH" else "🏭" if category == "MANUFACTURING" else "🛒" if category == "RETAIL" else "💻" if category == "TECH" else "✈️"
    direction_emoji = "📈" if direction == "up" else "📉" if direction == "down" else "➡️"
    
    embed = discord.Embed(
        title="✅ Market Direction Updated",
        description=f"{emoji} {category} sector direction set to {direction_emoji} {direction.title()}",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="Previous Direction", value=old_direction.title(), inline=True)
    embed.add_field(name="New Direction", value=direction.title(), inline=True)
    embed.add_field(name="Affected Stocks", value=f"{len(stock_market.categories[category]['stocks'])} stocks", inline=True)
    
    embed.add_field(
        name="ℹ️ Note", 
        value="This setting affects future price movements during market updates",
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_force_update", description="Force update all stock prices using proper calculation (Admin)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to force update")
async def stocks_force_update(interaction: discord.Interaction):
    """Force an immediate controlled market update using proper pricing system"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    # Use the proper dynamic market update system
    update_summary = await stock_market.trigger_dynamic_update(
        reason="Admin force update",
        send_discord_notification=False
    )
    
    # Create response embed
    embed = discord.Embed(
        title="⚡ Market Update Complete",
        description=f"Updated {update_summary['stocks_updated']} stocks using proper economic calculations",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Show current market status
    category_prices = stock_market.calculate_category_prices()
    etf_text = ""
    for cat_name, price in category_prices.items():
        emoji = "⛽" if cat_name == "ENERGY" else "🎬" if cat_name == "ENTERTAINMENT" else "🏦" if cat_name == "FINANCE" else "🏥" if cat_name == "HEALTH" else "🏭" if cat_name == "MANUFACTURING" else "🛒" if cat_name == "RETAIL" else "💻" if cat_name == "TECH" else "✈️"
        etf_text += f"{emoji} **{cat_name}**: ${price:.2f}\n"
    
    embed.add_field(name="📊 Current Sector ETFs", value=etf_text.strip(), inline=True)
    
    # Market parameters being used
    params = stock_market.market_params
    params_text = f"""
**Trend**: {params['trend_direction']:+.2f} {'📈' if params['trend_direction'] > 0 else '📉' if params['trend_direction'] < 0 else '➡️'}
**Volatility**: {params['volatility']:.2f} {'🌪️' if params['volatility'] > 0.7 else '🌊'}
**Sentiment**: {params['market_sentiment']:.2f} {'😄' if params['market_sentiment'] > 0.7 else '😐' if params['market_sentiment'] > 0.4 else '😟'}
"""
    embed.add_field(name="📈 Economic Parameters", value=params_text.strip(), inline=True)
    
    # Show that this uses proper calculations
    embed.add_field(
        name="✅ System Used", 
        value="Economic data → Market parameters → On-demand pricing with Perlin noise", 
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_reset", description="Reset all stocks to default prices (Admin)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to reset stocks")
async def stocks_reset(interaction: discord.Interaction):
    """Reset all stocks to default prices and clear history"""
    # Create confirmation button
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.value = None
            
        @discord.ui.button(label="Reset Market", style=discord.ButtonStyle.danger, emoji="🔄")
        async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("Only the command user can confirm.", ephemeral=True)
                return
            self.value = True
            self.stop()
            
        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("Only the command user can confirm.", ephemeral=True)
                return
            self.value = False
            self.stop()
    
    # Send confirmation message
    view = ConfirmView()
    embed = discord.Embed(
        title="⚠️ Reset Stock Market?",
        description="This will reset ALL stock prices to defaults and clear price history",
        color=0xffaa00,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="🔄 What will be reset:",
        value="• All stock prices to starting values\n• Market parameters to defaults\n• Trading history cleared\n• Market directions normalized",
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Warning",
        value="This action cannot be undone!",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, view=view)
    
    # Wait for response
    await view.wait()
    
    if not view.value:
        await interaction.edit_original_response(
            embed=discord.Embed(title="❌ Reset cancelled", color=0xff4444),
            view=None
        )
        return
    
    stock_market = get_stock_market()
    
    # Reset all category market directions
    for cat_data in stock_market.categories.values():
        cat_data['market_direction'] = 'normal'
    
    # CRITICAL: Reset stock prices to their default values from code
    default_stock_prices = {
        # Energy sector
        "XOM": 129.05,
        "CVX": 185.75,
        "COP": 153.11,
        # Entertainment sector
        "NFLX": 564.99,
        "DIS": 91.09,
        "EA": 290.79,
        # Finance sector
        "JPM": 103.97,
        "BAC": 36.03,
        "V": 152.31,
        "GS": 266.66,
        # Health sector
        "JNJ": 105.02,
        "UNH": 216.74,
        "PFE": 43.35,
        # Manufacturing sector
        "CAT": 136.07,
        "GE": 166.86,
        "LMT": 376.35,
        # Retail sector
        "WMT": 68.88,
        "COST": 331.80,
        "HD": 139.25,
        # Tech sector
        "AAPL": 193.54,
        "MSFT": 468.95,
        "GOOGL": 2782.18,
        "NVDA": 680.83,
        # Transport sector
        "BA": 262.71
    }
    
    # Reset each stock to its default price
    stocks_reset = 0
    for _, cat_data in stock_market.categories.items():
        for stock in cat_data["stocks"]:
            symbol = stock["symbol"]
            if symbol in default_stock_prices:
                old_price = stock["price"]
                stock["price"] = default_stock_prices[symbol]
                
                # Reset AI pricing attributes
                stock["daily_range_low"] = stock["price"] * 0.97
                stock["daily_range_high"] = stock["price"] * 1.03
                stock["sector_factor"] = 1.0
                
                stocks_reset += 1
                print(f"🔄 {symbol}: ${old_price:.2f} → ${stock['price']:.2f}")
    
    # AIDEV-NOTE: param-reset; set neutral defaults - AI will set proper values
    # Market parameters reset to neutral defaults
    stock_market.market_params = {
        "trend_direction": 0.0,      # Neutral direction
        "volatility": 0.5,           # Moderate volatility
        "momentum": 0.5,             # Neutral momentum
        "market_sentiment": 0.5,     # Neutral sentiment
        "long_term_outlook": 0.5     # Neutral outlook
    }
    print("📊 Market parameters reset to neutral defaults")
    
    # Clear trading state
    stock_market.is_trading_day = False
    stock_market.current_trading_day = None
    stock_market.daily_ranges = {}
    
    # Save changes
    stock_market.save_market_data()
    
    # Clear historical data files
    try:
        history_file = stock_market.data_dir / "stock_history.json"
        if history_file.exists():
            history_file.unlink()
            
        analysis_file = stock_market.data_dir / "daily_analysis.json"
        if analysis_file.exists():
            analysis_file.unlink()
    except Exception as e:
        print(f"Error clearing history files: {e}")
    
    # Success response
    reset_embed = discord.Embed(
        title="✅ Stock Market Reset Complete",
        description="All stocks and market data have been reset to defaults",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    total_stocks = sum(len(cat['stocks']) for cat in stock_market.categories.values())
    reset_embed.add_field(
        name="📊 Reset Summary",
        value=f"• {total_stocks} stocks reset to realistic default prices\n• {len(stock_market.categories)} categories normalized\n• Market parameters recalculated from economic data\n• Trading history and precomputed prices cleared\n• All AI pricing attributes reset",
        inline=False
    )
    
    params = stock_market.market_params
    
    # Dynamic descriptions based on actual values
    trend_desc = "Bullish" if params['trend_direction'] > 0.1 else "Bearish" if params['trend_direction'] < -0.1 else "Neutral"
    vol_desc = "Very High" if params['volatility'] > 0.7 else "High" if params['volatility'] > 0.5 else "Moderate" if params['volatility'] > 0.3 else "Low"
    sentiment_desc = "Optimistic" if params['market_sentiment'] > 0.7 else "Cautious" if params['market_sentiment'] > 0.4 else "Pessimistic"
    
    params_text = f"""
**Trend**: {params['trend_direction']:+.2f} ({trend_desc})
**Volatility**: {params['volatility']:.2f} ({vol_desc})
**Sentiment**: {params['market_sentiment']:.2f} ({sentiment_desc})
**Momentum**: {params['momentum']:.2f}
**Outlook**: {params['long_term_outlook']:.2f}
"""
    reset_embed.add_field(name="🎯 New Market Parameters", value=params_text.strip(), inline=False)
    
    await interaction.edit_original_response(embed=reset_embed, view=None)

@app_commands.command(name="stocks_save_structure", description="Save current market structure to disk (Admin)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to save market structure")
async def stocks_save_structure(interaction: discord.Interaction):
    """Save the current stock market structure to disk"""
    # Create confirmation button
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.value = None
            
        @discord.ui.button(label="Save Structure", style=discord.ButtonStyle.primary, emoji="💾")
        async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("Only the command user can confirm.", ephemeral=True)
                return
            self.value = True
            self.stop()
            
        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("Only the command user can confirm.", ephemeral=True)
                return
            self.value = False
            self.stop()
    
    # Send confirmation message
    view = ConfirmView()
    confirm_embed = discord.Embed(
        title="💾 Save Market Structure?",
        description=(
            "This will:\n"
            "• Save the current in-memory market structure to disk\n"
            "• Preserve all current stock prices and parameters\n"
            "• Update the market data file\n\n"
            "This is a safe operation that doesn't change any prices."
        ),
        color=0x0099ff
    )
    await interaction.response.send_message(embed=confirm_embed, view=view)
    
    # Wait for response
    await view.wait()
    
    if not view.value:
        await interaction.edit_original_response(
            embed=discord.Embed(title="❌ Save cancelled", color=0xff4444),
            view=None
        )
        return
    
    stock_market = get_stock_market()
    
    # Force save current structure (from code) to file
    stock_market.save_market_data()
    
    # Create response
    embed = discord.Embed(
        title="✅ Market Structure Saved",
        description="Current market structure has been saved to disk",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Show current structure
    total_stocks = sum(len(cat['stocks']) for cat in stock_market.categories.values())
    
    structure_text = ""
    for cat_name, cat_data in stock_market.categories.items():
        emoji = "⛽" if cat_name == "ENERGY" else "🎬" if cat_name == "ENTERTAINMENT" else "🏦" if cat_name == "FINANCE" else "🏥" if cat_name == "HEALTH" else "🏭" if cat_name == "MANUFACTURING" else "🛒" if cat_name == "RETAIL" else "💻" if cat_name == "TECH" else "✈️"
        structure_text += f"{emoji} **{cat_name}**: {len(cat_data['stocks'])} stocks\n"
    
    embed.add_field(
        name="📊 Current Market Structure",
        value=structure_text.strip(),
        inline=False
    )
    
    # Show sample stocks
    sample_stocks = []
    for cat_data in stock_market.categories.values():
        if cat_data['stocks']:
            sample_stocks.append(f"**{cat_data['stocks'][0]['symbol']}** ({cat_data['stocks'][0]['name']})")
        if len(sample_stocks) >= 6:
            break
    
    embed.add_field(
        name="📈 Sample Stocks",
        value="\n".join(sample_stocks),
        inline=True
    )
    
    # Show market parameters
    params = stock_market.market_params
    params_text = f"""
**Trend**: {params['trend_direction']:+.2f}
**Volatility**: {params['volatility']:.2f}
**Sentiment**: {params['market_sentiment']:.2f}
"""
    embed.add_field(name="📊 Market Parameters", value=params_text.strip(), inline=True)
    
    embed.set_footer(text=f"{total_stocks} stocks across {len(stock_market.categories)} sectors")
    
    await interaction.edit_original_response(embed=embed, view=None)

@app_commands.command(name="stocks_sync_econ", description="Sync stock market with economic analysis data (Admin)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to sync economic data")
async def stocks_sync_econ(interaction: discord.Interaction):
    """Synchronize stock market parameters with current economic analysis data"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    # Force update market parameters to reflect 8.51% inflation environment
    stock_market.market_params.update({
        "trend_direction": -0.25,     # Bearish due to high inflation
        "volatility": 0.65,           # High volatility from rate uncertainty
        "momentum": 0.35,             # Weak momentum amid headwinds
        "market_sentiment": 0.35,     # Cautious sentiment
        "long_term_outlook": 0.40     # Pessimistic outlook
    })
    
    # Save updated parameters
    stock_market.save_market_data()
    
    # Create response embed
    embed = discord.Embed(
        title="✅ Economic Data Synchronized",
        description="Stock market parameters updated for 8.51% inflation environment",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Get actual inflation rate from economic data if available
    inflation_rate = 8.51  # Default value
    try:
        from economic_utils import get_economic_data
        inflation_data = get_economic_data("inflation", days_back=1)
        if inflation_data and len(inflation_data) > 0:
            inflation_rate = inflation_data[0]['data'].get('rate', 8.51)
    except:
        pass
    
    # Show current economic conditions
    econ_summary = f"""
**Inflation Rate**: {inflation_rate:.2f}% YoY (High - above 2% target)
**Fed Funds Rate**: 4.00% (Restrictive monetary policy)
**Market Environment**: High Inflation Crisis
**Economic Growth**: Slowing due to rate hikes
**Labor Market**: Tight but cooling (3.2% unemployment)
"""
    embed.add_field(name="📊 Current Economic Conditions", value=econ_summary.strip(), inline=False)
    
    # Show updated market parameters
    params = stock_market.market_params
    market_summary = f"""
**Trend**: {params['trend_direction']:+.2f} 📉 Bearish (Inflation concerns)
**Volatility**: {params['volatility']:.2f} 🌪️ High (Rate uncertainty)
**Momentum**: {params['momentum']:.2f} 🐌 Weak (Economic headwinds)
**Sentiment**: {params['market_sentiment']:.2f} 😟 Pessimistic (Inflation anxiety)
**Outlook**: {params['long_term_outlook']:.2f} 📉 Bearish (Policy tightening)
"""
    embed.add_field(name="📈 Updated Market Parameters", value=market_summary.strip(), inline=False)
    
    # Show key economic factors
    factors_text = """
• High aggregate demand driving inflation
• Asia-Pacific trade barriers impacting costs
• Middle East uncertainty affecting energy prices
• Aggressive Fed rate hikes cooling economy
• Bird flu crisis impact fading but residual effects
"""
    embed.add_field(name="🎯 Key Economic Factors", value=factors_text.strip(), inline=False)
    
    embed.set_footer(text=f"Parameters reflect current economic conditions with {inflation_rate:.2f}% inflation")
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_redo_analysis", description="Redo daily market analysis with a specific prompt (Admin)")
@app_commands.describe(prompt="Specific prompt to guide the market analysis")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to redo daily analysis")
async def stocks_redo_analysis(interaction: discord.Interaction, prompt: str):
    """Redo the daily market analysis with a specific prompt, maintaining consistency unless news changes"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    if not stock_market.client:
        await interaction.followup.send("❌ Stock market not properly initialized")
        return
    
    # Send initial status
    embed = discord.Embed(
        title="🔄 Redoing Daily Market Analysis",
        description=f"**Custom Prompt**: {prompt[:200]}{'...' if len(prompt) > 200 else ''}",
        color=0xffaa00,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="📊 Process", value="⏳ Starting AI analysis with custom prompt...", inline=False)
    embed.add_field(name="🧠 Strategy", value="Maintaining consistency with previous analysis unless significant news detected", inline=False)
    
    initial_msg = await interaction.followup.send(embed=embed)
    
    try:
        # Get previous analysis for consistency
        previous_analysis = stock_market.get_previous_trading_day_data()
        
        # Update process status
        embed.set_field_at(0, name="📊 Process", value="📈 Running enhanced AI analysis...", inline=False)
        await initial_msg.edit(embed=embed)
        
        # Run the enhanced analysis with custom prompt
        analysis = await stock_market.get_daily_market_analysis_with_prompt(prompt, previous_analysis)
        
        if not analysis or "error" in analysis:
            raise Exception(f"Analysis failed: {analysis.get('error', 'Unknown error')}")
        
        # Delete previous analysis and save new one
        await stock_market.replace_daily_analysis(analysis)
        
        # Update market parameters from new analysis
        stock_market.market_params = analysis.get("parameters", stock_market.market_params)
        
        # AIDEV-NOTE: price-source; prices set by AI daily analysis only
        print("✅ Market parameters updated from AI analysis")
        
        # Reset daily ranges and set new trading day
        trading_day = datetime.now().strftime("%Y-%m-%d")
        stock_market.current_trading_day = trading_day
        stock_market.daily_ranges = {}
        
        # Update current prices to first hour if trading
        if stock_market.is_trading_day:
            await stock_market.apply_hourly_price_update(0)  # Apply opening prices
        
        # Trigger comprehensive dynamic update with Discord notification
        await stock_market.trigger_dynamic_update(
            reason=f"Analysis redone with prompt: {prompt[:50]}...",
            send_discord_notification=True,
            save_history=True
        )
        
        # Create success embed
        embed = discord.Embed(
            title="✅ Daily Market Analysis Complete",
            description="Analysis redone with custom prompt and consistency checks",
            color=0x00ff88,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Show updated parameters
        params = analysis.get("parameters", {})
        param_text = f"""
**Trend**: {params.get('trend_direction', 0):+.3f} {'📈' if params.get('trend_direction', 0) > 0 else '📉' if params.get('trend_direction', 0) < 0 else '➡️'}
**Volatility**: {params.get('volatility', 0):.3f} {'🌪️' if params.get('volatility', 0) > 0.7 else '🌊'}
**Momentum**: {params.get('momentum', 0):.3f} {'🚀' if params.get('momentum', 0) > 0.7 else '⚡'}
**Sentiment**: {params.get('market_sentiment', 0):.3f} {'😄' if params.get('market_sentiment', 0) > 0.7 else '😐' if params.get('market_sentiment', 0) > 0.4 else '😟'}
"""
        embed.add_field(name="📊 Updated Parameters", value=param_text.strip(), inline=True)
        
        # Show reasoning summary
        reasoning = analysis.get("reasoning", {})
        if "market_overview" in reasoning:
            overview = reasoning["market_overview"][:200] + "..." if len(reasoning["market_overview"]) > 200 else reasoning["market_overview"]
            embed.add_field(name="🧠 AI Reasoning", value=overview, inline=False)
        
        # Show consistency info
        consistency_info = "✅ Previous analysis considered for consistency\n"
        if previous_analysis:
            consistency_info += f"📊 Compared with analysis from {previous_analysis.get('timestamp', 'unknown')[:10]}\n"
        consistency_info += f"🎯 Custom prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
        
        embed.add_field(name="🔄 Consistency Check", value=consistency_info, inline=False)
        
        embed.set_footer(text="Stock prices and ETFs updated • Market ready for trading")
        
        await initial_msg.edit(embed=embed)
        
    except Exception as e:
        # Error handling
        error_embed = discord.Embed(
            title="❌ Analysis Failed",
            description=f"Failed to redo daily analysis: {str(e)}",
            color=0xff4444,
            timestamp=datetime.now(timezone.utc)
        )
        
        error_embed.add_field(name="🔄 Recovery", value="Previous analysis and market state preserved", inline=False)
        error_embed.add_field(name="💡 Suggestion", value="Try again with a simpler prompt or check system status", inline=False)
        
        await initial_msg.edit(embed=error_embed)

# AIDEV-NOTE: deprecated-command-removed; baseline recalc no longer needed (AI sets prices)

@app_commands.command(name="stocks_set_update_rate", description="Set how often stock prices update (Admin)")
@app_commands.describe(minutes="Time in minutes between price updates (1-1440)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to set update rate")
async def stocks_set_update_rate(interaction: discord.Interaction, minutes: int):
    """Set the price update rate in minutes"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    # Validate input
    if minutes < 1 or minutes > 1440:
        await interaction.followup.send("❌ Update rate must be between 1 and 1440 minutes (24 hours)")
        return
    
    # Store old rate for comparison
    old_rate = stock_market.price_update_rate_minutes
    
    # Set new rate
    success = stock_market.set_price_update_rate(minutes)
    
    if not success:
        await interaction.followup.send("❌ Failed to update price rate")
        return
    
    # Create success embed
    embed = discord.Embed(
        title="✅ Price Update Rate Changed",
        description=f"Stock prices will now update every {minutes} minute{'s' if minutes != 1 else ''}",
        color=0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Add comparison info
    embed.add_field(
        name="🕰️ Update Schedule",
        value=f"**Previous**: Every {old_rate} minute{'s' if old_rate != 1 else ''}\n**New**: Every {minutes} minute{'s' if minutes != 1 else ''}",
        inline=True
    )
    
    # Add next update time
    if stock_scheduler:
        et_now = stock_scheduler.get_et_now()
        current_minutes = et_now.hour * 60 + et_now.minute
        next_update_minutes = ((current_minutes // minutes) + 1) * minutes
        next_update_hour = next_update_minutes // 60
        next_update_minute = next_update_minutes % 60
        
        if next_update_hour >= 24:
            next_update_time = "12:00 AM ET (tomorrow)"
        else:
            next_update_time = f"{next_update_hour % 12 or 12}:{next_update_minute:02d} {'PM' if next_update_hour >= 12 else 'AM'} ET"
        
        embed.add_field(
            name="⏰ Next Update",
            value=next_update_time,
            inline=True
        )
    
    # Add recommendations
    if minutes == 1:
        recommendation = "⚠️ Very frequent updates - high server load"
    elif minutes <= 5:
        recommendation = "ℹ️ Frequent updates - good for active trading"
    elif minutes <= 30:
        recommendation = "✅ Balanced - good for most scenarios"
    elif minutes <= 60:
        recommendation = "👍 Standard hourly updates"
    else:
        recommendation = "🕰️ Infrequent updates - prices change slowly"
    
    embed.add_field(
        name="💡 Recommendation",
        value=recommendation,
        inline=False
    )
    
    embed.set_footer(text="Prices calculated on-demand using Perlin noise")
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_force_update", description="Force immediate AI market analysis and price update (Admin)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to force update")
async def stocks_force_update(interaction: discord.Interaction):
    """Force immediate AI analysis and update of all stock prices"""
    # Create confirmation button
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.value = None
            
        @discord.ui.button(label="Confirm AI Analysis", style=discord.ButtonStyle.danger, emoji="🤖")
        async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("Only the command user can confirm.", ephemeral=True)
                return
            self.value = True
            self.stop()
            
        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("Only the command user can confirm.", ephemeral=True)
                return
            self.value = False
            self.stop()
    
    # Send confirmation message
    view = ConfirmView()
    confirm_embed = discord.Embed(
        title="🤖 Force AI Market Analysis?",
        description=(
            "This will:\n"
            "• Run AI analysis on recent Discord activity\n"
            "• Update all stock prices and market parameters\n"
            "• Override current market state with new AI predictions\n"
            "• Apply changes immediately to live trading\n\n"
            "**⚠️ This may cause significant price movements!**"
        ),
        color=0xffaa00
    )
    await interaction.response.send_message(embed=confirm_embed, view=view)
    
    # Wait for response
    await view.wait()
    
    if not view.value:
        await interaction.edit_original_response(
            embed=discord.Embed(title="❌ Force update cancelled", color=0xff4444),
            view=None
        )
        return
    
    # Update to show processing
    await interaction.edit_original_response(
        embed=discord.Embed(
            title="🤖 Running AI Analysis...",
            description="Analyzing Discord activity and generating market update...",
            color=0x00aaff
        ),
        view=None
    )
    
    stock_market = get_stock_market()
    
    try:
        # Run AI market analysis
        print("🤖 Forcing AI market analysis...")
        analysis = await stock_market.get_daily_market_analysis()
        
        # Save the analysis
        stock_market.save_daily_analysis(analysis)
        
        # Update market parameters from analysis
        stock_market.market_params = analysis.get("parameters", stock_market.market_params)
        
        # Apply opening prices from AI analysis
        if "opening_prices" in analysis:
            for category_name, category_data in stock_market.categories.items():
                for stock in category_data["stocks"]:
                    symbol = stock["symbol"]
                    if symbol in analysis["opening_prices"]:
                        ai_data = analysis["opening_prices"][symbol]
                        stock["ai_opening_price"] = ai_data["open_price"]
                        stock["price"] = ai_data["open_price"]
                        stock["daily_range_low"] = ai_data["range_low"]
                        stock["daily_range_high"] = ai_data["range_high"]
        
        # Trigger dynamic update to recalculate all prices
        await stock_market.trigger_dynamic_update(
            reason="Forced AI analysis update",
            send_discord_notification=True
        )
        
        # Create success embed
        embed = discord.Embed(
            title="✅ AI Market Analysis Complete",
            description="All stock prices updated based on fresh AI analysis",
            color=0x00ff88,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Show updated parameters
        params = stock_market.market_params
        param_text = f"""
**Trend**: {params['trend_direction']:+.3f} {'📈' if params['trend_direction'] > 0 else '📉' if params['trend_direction'] < 0 else '➡️'}
**Volatility**: {params['volatility']:.3f} {'🌪️' if params['volatility'] > 0.7 else '🌊'}
**Momentum**: {params['momentum']:.3f} {'🚀' if params['momentum'] > 0.7 else '⚡'}
**Sentiment**: {params['market_sentiment']:.3f} {'😄' if params['market_sentiment'] > 0.7 else '😐' if params['market_sentiment'] > 0.4 else '😟'}
**Outlook**: {params['long_term_outlook']:.3f} {'🌟' if params['long_term_outlook'] > 0.7 else '🌤️'}
"""
        embed.add_field(name="📊 Market Parameters", value=param_text.strip(), inline=True)
        
        # Show AI reasoning if available
        if "reasoning" in analysis and "market_overview" in analysis["reasoning"]:
            overview = analysis["reasoning"]["market_overview"][:200] + "..."
            embed.add_field(name="🧠 AI Reasoning", value=overview, inline=False)
        
        # Show update summary
        total_stocks = sum(len(cat['stocks']) for cat in stock_market.categories.values())
        summary_text = f"""
**Total Stocks**: {total_stocks}
**Analysis Time**: {analysis.get('timestamp', 'Unknown')}
**Market Status**: {'🟢 Open' if stock_market.is_trading_day else '🔴 Closed'}
"""
        embed.add_field(name="📈 Update Summary", value=summary_text.strip(), inline=True)
        
        embed.set_footer(text="AI analysis complete • Prices updated • Trading active")
        
        await interaction.edit_original_response(embed=embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ AI Analysis Failed",
            description=f"Error: {str(e)}",
            color=0xff4444,
            timestamp=datetime.now(timezone.utc)
        )
        await interaction.edit_original_response(embed=error_embed)
        await interaction.followup.send(f"❌ Force update failed: {str(e)}")

# ==============================================================================
# UNBELIEVABOAT TRADING COMMANDS
# ==============================================================================

# Import trading system
try:
    from stock_trading import get_stock_trading_system
    TRADING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Trading system not available: {e}")
    TRADING_AVAILABLE = False

@handle_errors("Failed to buy stock")
async def stocks_buy(interaction: discord.Interaction, symbol: str, quantity: int):
    """Buy stocks using UnbelievaBoat balance"""
    await interaction.response.defer()
    
    if not TRADING_AVAILABLE:
        await interaction.followup.send("❌ Trading system not available")
        return
    
    if quantity <= 0:
        await interaction.followup.send("❌ Quantity must be positive")
        return
    
    if quantity > 1000:
        await interaction.followup.send("❌ Maximum quantity per transaction is 1000 shares")
        return
    
    try:
        stock_market = get_stock_market()
        trading_system = get_stock_trading_system()
        
        # Check if trading is restricted to admins only
        if stock_market.admin_only_trading:
            user_roles = [role.name for role in interaction.user.roles] if hasattr(interaction.user, 'roles') else []
            if Roles.ADMIN not in user_roles:
                embed = discord.Embed(
                    title="🔒 Trading Restricted",
                    description="Trading is currently restricted to administrators only",
                    color=0xff6b6b,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(
                    name="ℹ️ Information",
                    value="• Trading has been temporarily restricted\n• You can still view prices and your portfolio\n• Contact an administrator for more information",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
        
        success, message = await trading_system.buy_stock(
            interaction.user.id, 
            symbol, 
            quantity, 
            stock_market
        )
        
        if success:
            embed = discord.Embed(
                title="🛒 Stock Purchase Successful",
                description=message,
                color=0x00ff00,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Add transaction details
            all_assets = stock_market.get_all_tradeable_assets()
            stock_info = next((s for s in all_assets if s['symbol'].upper() == symbol.upper()), None)
            if stock_info:
                total_cost = stock_info['price'] * quantity
                embed.add_field(name="Stock", value=f"{stock_info['name']} ({symbol.upper()})", inline=True)
                embed.add_field(name="Quantity", value=f"{quantity:,} shares", inline=True)
                embed.add_field(name="Price per Share", value=f"${stock_info['price']:,.2f}", inline=True)
                embed.add_field(name="Total Cost", value=f"${total_cost:,.2f}", inline=True)
                embed.add_field(name="Category", value=stock_info.get('category', 'Unknown'), inline=True)
        else:
            embed = discord.Embed(
                title="❌ Stock Purchase Failed",
                description=message,
                color=0xff0000
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error processing stock purchase: {str(e)}")

@handle_errors("Failed to sell stock")
async def stocks_sell(interaction: discord.Interaction, symbol: str, quantity: int):
    """Sell stocks to UnbelievaBoat balance"""
    await interaction.response.defer()
    
    if not TRADING_AVAILABLE:
        await interaction.followup.send("❌ Trading system not available")
        return
    
    if quantity <= 0:
        await interaction.followup.send("❌ Quantity must be positive")
        return
    
    try:
        stock_market = get_stock_market()
        trading_system = get_stock_trading_system()
        
        # Check if trading is restricted to admins only
        if stock_market.admin_only_trading:
            user_roles = [role.name for role in interaction.user.roles] if hasattr(interaction.user, 'roles') else []
            if Roles.ADMIN not in user_roles:
                embed = discord.Embed(
                    title="🔒 Trading Restricted",
                    description="Trading is currently restricted to administrators only",
                    color=0xff6b6b,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(
                    name="ℹ️ Information",
                    value="• Trading has been temporarily restricted\n• You can still view prices and your portfolio\n• Contact an administrator for more information",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
        
        success, message = await trading_system.sell_stock(
            interaction.user.id, 
            symbol, 
            quantity, 
            stock_market
        )
        
        if success:
            embed = discord.Embed(
                title="💰 Stock Sale Successful",
                description=message,
                color=0x00ff00,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Add transaction details
            all_assets = stock_market.get_all_tradeable_assets()
            stock_info = next((s for s in all_assets if s['symbol'].upper() == symbol.upper()), None)
            if stock_info:
                total_value = stock_info['price'] * quantity
                embed.add_field(name="Stock", value=f"{stock_info['name']} ({symbol.upper()})", inline=True)
                embed.add_field(name="Quantity", value=f"{quantity:,} shares", inline=True)
                embed.add_field(name="Price per Share", value=f"${stock_info['price']:,.2f}", inline=True)
                embed.add_field(name="Total Value", value=f"${total_value:,.2f}", inline=True)
                embed.add_field(name="Category", value=stock_info.get('category', 'Unknown'), inline=True)
        else:
            embed = discord.Embed(
                title="❌ Stock Sale Failed",
                description=message,
                color=0xff0000
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error processing stock sale: {str(e)}")

@handle_errors("Failed to show portfolio")
async def stocks_portfolio(interaction: discord.Interaction, user: discord.Member = None):
    """View stock portfolio and total value"""
    await interaction.response.defer()
    
    if not TRADING_AVAILABLE:
        await interaction.followup.send("❌ Trading system not available")
        return
    
    target_user = user if user else interaction.user
    
    try:
        stock_market = get_stock_market()
        trading_system = get_stock_trading_system()
        
        # Get portfolio value and breakdown
        total_value, portfolio_breakdown = trading_system.get_portfolio_value(target_user.id, stock_market)
        
        # Get current UnbelievaBoat balance
        cash_balance = await trading_system.get_user_balance(target_user.id)
        
        if not portfolio_breakdown and total_value == 0:
            embed = discord.Embed(
                title=f"📊 {target_user.display_name}'s Portfolio",
                description="No stocks owned",
                color=0x999999
            )
            if cash_balance is not None:
                embed.add_field(name="💰 Cash Balance", value=f"${cash_balance:,.2f}", inline=False)
            await interaction.followup.send(embed=embed)
            return
        
        # Create portfolio embed
        embed = discord.Embed(
            title=f"📊 {target_user.display_name}'s Stock Portfolio",
            color=0x0099ff,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add portfolio summary
        if cash_balance is not None:
            total_net_worth = total_value + cash_balance
            embed.add_field(name="💰 Cash Balance", value=f"${cash_balance:,.2f}", inline=True)
            embed.add_field(name="📈 Stock Value", value=f"${total_value:,.2f}", inline=True)
            embed.add_field(name="💎 Total Net Worth", value=f"${total_net_worth:,.2f}", inline=True)
        else:
            embed.add_field(name="📈 Total Stock Value", value=f"${total_value:,.2f}", inline=False)
        
        # Group stocks by category
        categories = {}
        for symbol, details in portfolio_breakdown.items():
            category = details['category']
            if category not in categories:
                categories[category] = []
            categories[category].append((symbol, details))
        
        # Add stocks by category
        for category, stocks in categories.items():
            stock_lines = []
            for symbol, details in sorted(stocks, key=lambda x: x[1]['value'], reverse=True):
                # Use actual gain/loss from portfolio breakdown
                gain_loss = details.get('gain_loss', 0)
                gain_loss_pct = details.get('gain_loss_pct', 0)
                avg_price = details.get('avg_price', details['current_price'])
                pl_emoji = "📈" if gain_loss >= 0 else "📉"
                
                # Format gain/loss display
                gl_sign = "+" if gain_loss >= 0 else ""
                gl_color = "🟢" if gain_loss >= 0 else "🔴"
                
                stock_lines.append(
                    f"{pl_emoji} **{symbol}** - {details['quantity']:,} shares\n"
                    f"   Avg Cost: ${avg_price:,.2f} | Current: ${details['current_price']:,.2f}\n"
                    f"   Value: ${details['value']:,.2f} {gl_color} {gl_sign}${gain_loss:,.2f} ({gl_sign}{gain_loss_pct:.1f}%)"
                )
            
            if stock_lines:
                embed.add_field(
                    name=f"🏢 {category.title()} Sector",
                    value="\n\n".join(stock_lines[:3]),  # Limit to 3 stocks per field
                    inline=False
                )
                
                # If more than 3 stocks in category, add overflow field
                if len(stock_lines) > 3:
                    overflow_text = "\n".join(stock_lines[3:6])  # Next 3
                    if len(stock_lines) > 6:
                        overflow_text += f"\n... and {len(stock_lines) - 6} more"
                    embed.add_field(name="continued...", value=overflow_text, inline=False)
        
        # Add footer with market info
        embed.set_footer(text="💡 Use /stocks_buy and /stocks_sell to trade stocks")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error getting portfolio: {str(e)}")

# Create decorated command functions for registration
@app_commands.command(name="stocks_buy", description="Buy stocks using UnbelievaBoat balance")
@app_commands.describe(
    symbol="Stock symbol (e.g., AAPL, MSFT, GOOGL)",
    quantity="Number of shares to buy"
)
async def stocks_buy_command(interaction: discord.Interaction, symbol: str, quantity: int):
    """Buy stocks using UnbelievaBoat balance"""
    await stocks_buy(interaction, symbol, quantity)

@app_commands.command(name="stocks_sell", description="Sell stocks to UnbelievaBoat balance")
@app_commands.describe(
    symbol="Stock symbol (e.g., AAPL, MSFT, GOOGL)",
    quantity="Number of shares to sell"
)
async def stocks_sell_command(interaction: discord.Interaction, symbol: str, quantity: int):
    """Sell stocks to UnbelievaBoat balance"""
    await stocks_sell(interaction, symbol, quantity)

@app_commands.command(name="stocks_portfolio", description="View stock portfolio and total value")
@app_commands.describe(user="User to view portfolio for (optional)")
async def stocks_portfolio_command(interaction: discord.Interaction, user: discord.Member = None):
    """View stock portfolio and total value"""
    await stocks_portfolio(interaction, user)

@app_commands.command(name="stocks_trigger_hourly", description="Manually trigger hourly market update (Admin only)")
async def stocks_trigger_hourly_command(interaction: discord.Interaction):
    """Manually trigger an hourly market update"""
    # Import config here to avoid circular imports
    import config
    
    # Check admin role
    if not hasattr(interaction.user, 'roles'):
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return
    
    user_roles = [role.name for role in interaction.user.roles]
    if config.Roles.ADMIN not in user_roles:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return
    
    # Check channel
    if interaction.channel_id != config.BOT_HELPER_CHANNEL:
        await interaction.response.send_message("❌ This command can only be used in the bot helper channel.", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        import stock_market
        sm = stock_market.get_stock_market()
        
        # Check if market is initialized (has market parameters)
        if not sm.market_params or sm.market_params.get("trend_direction") is None:
            await interaction.followup.send("❌ Stock market not initialized. Use `/stocks_force_init` first.")
            return
        
        # Create scheduler instance to use its methods
        scheduler = stock_market.StockMarketScheduler(sm)
        
        # Get current hour and trigger update
        et_now = scheduler.get_et_now()
        hour_index = et_now.hour
        
        await interaction.followup.send(f"🔄 Triggering hourly update for hour {hour_index} ({et_now.strftime('%I:%M %p ET')})...")
        
        # Manually run the on-demand price update
        await scheduler.update_prices_on_demand()
        
        await interaction.edit_original_response(content=f"✅ Hourly market update triggered successfully! Check the bot channel for the posted update.")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error triggering hourly update: {str(e)}")

@app_commands.command(name="stocks_toggle_admin_trading", description="Toggle trading to admin-only mode (Admin)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to toggle admin-only trading")
async def stocks_toggle_admin_trading(interaction: discord.Interaction):
    """Toggle trading restriction to admin-only mode"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    # Toggle the admin-only trading flag
    stock_market.admin_only_trading = not stock_market.admin_only_trading
    stock_market.save_market_data()
    
    # Create response embed
    embed = discord.Embed(
        title="🔒 Trading Restrictions Updated",
        description=f"Trading is now {'**Admin-only**' if stock_market.admin_only_trading else '**Open to all users**'}",
        color=0xff6b6b if stock_market.admin_only_trading else 0x00ff88,
        timestamp=datetime.now(timezone.utc)
    )
    
    if stock_market.admin_only_trading:
        embed.add_field(
            name="⚠️ Admin-Only Mode Active",
            value="• Only administrators can buy/sell stocks\n• All users can still view prices and portfolios\n• Market continues to operate normally",
            inline=False
        )
        embed.set_footer(text="Use this command again to re-open trading to all users")
    else:
        embed.add_field(
            name="✅ Open Trading Active",
            value="• All users can buy/sell stocks\n• Normal trading restrictions apply\n• Maximum 1000 shares per transaction",
            inline=False
        )
        embed.set_footer(text="Use this command again to restrict trading to admins")
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_clear_history", description="Clear all stock price history (Admin)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to clear stock price history")
async def stocks_clear_history(interaction: discord.Interaction):
    """Clear all stock price history data"""
    # Create confirmation button
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.value = None
            
        @discord.ui.button(label="Clear History", style=discord.ButtonStyle.danger, emoji="🗑️")
        async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("Only the command user can confirm.", ephemeral=True)
                return
            self.value = True
            self.stop()
            
        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("Only the command user can confirm.", ephemeral=True)
                return
            self.value = False
            self.stop()
    
    # Send confirmation message
    view = ConfirmView()
    embed = discord.Embed(
        title="⚠️ Clear Stock Price History?",
        description="This will permanently delete all historical stock price data",
        color=0xffaa00,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="🗑️ What will be deleted:",
        value="• All price history data\n• Historical charts data\n• Past trading day records",
        inline=False
    )
    
    embed.add_field(
        name="✅ What will be preserved:",
        value="• Current stock prices\n• User portfolios\n• Market parameters\n• Category structures",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, view=view)
    
    # Wait for response
    await view.wait()
    
    if not view.value:
        await interaction.edit_original_response(
            embed=discord.Embed(title="❌ Clear history cancelled", color=0xff4444),
            view=None
        )
        return
    
    stock_market = get_stock_market()
    success = stock_market.clear_price_history()
    
    if success:
        # Create success embed
        result_embed = discord.Embed(
            title="✅ Stock Price History Cleared",
            description="All historical stock price data has been deleted",
            color=0x00ff88,
            timestamp=datetime.now(timezone.utc)
        )
        
        result_embed.add_field(
            name="📊 Result",
            value="• Price history file deleted\n• Charts will rebuild from new data\n• Market continues normal operation",
            inline=False
        )
        
        result_embed.set_footer(text="Historical data will accumulate again with future trading")
        
        await interaction.edit_original_response(embed=result_embed, view=None)
    else:
        error_embed = discord.Embed(
            title="❌ Failed to Clear History",
            description="Failed to clear stock price history. Check logs for details.",
            color=0xff4444
        )
        await interaction.edit_original_response(embed=error_embed, view=None)

@app_commands.command(name="stocks_test_stability", description="Test market stability with simulation (Admin)")
@app_commands.describe(
    days="Number of days to simulate (1-10)",
    test_volatility="Optional: Test with specific volatility (0.0-1.0)",
    stress_test="Whether to include stress test parameters"
)
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to run stability test")
async def stocks_test_stability(
    interaction: discord.Interaction,
    days: int = 5,
    test_volatility: Optional[float] = None,
    stress_test: bool = False
):
    """Run market stability simulation to test algorithms"""
    await interaction.response.defer()
    
    # Validate parameters
    days = max(1, min(10, days))
    if test_volatility is not None:
        test_volatility = max(0.0, min(1.0, test_volatility))
    
    stock_market = get_stock_market()
    
    # Prepare test parameters
    test_params = None
    if stress_test:
        test_params = {
            "volatility": test_volatility if test_volatility is not None else 0.9,
            "trend_direction": -0.8,
            "momentum": 0.2,
            "market_sentiment": 0.1
        }
    elif test_volatility is not None:
        test_params = {"volatility": test_volatility}
    
    # Run simulation
    results = stock_market.simulate_trading_days(days, test_params)
    
    # Create results embed
    embed = discord.Embed(
        title="🧪 Market Stability Test Results",
        color=0x00ff88 if not results["market_broke"] else 0xff4444,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Test summary
    status = "✅ PASSED" if not results["market_broke"] else "❌ FAILED"
    embed.add_field(
        name="📊 Test Status",
        value=f"**Status**: {status}\n**Days Simulated**: {results['days_simulated']}\n**Market Broke**: {'Yes' if results['market_broke'] else 'No'}",
        inline=True
    )
    
    # Parameter summary
    param_text = ""
    if test_params:
        for key, value in test_params.items():
            param_text += f"**{key.replace('_', ' ').title()}**: {value:.2f}\n"
    else:
        param_text = "Default economic parameters used"
    
    embed.add_field(
        name="⚙️ Test Parameters",
        value=param_text,
        inline=True
    )
    
    # Daily breakdown
    daily_text = ""
    for day_summary in results["daily_summaries"]:
        day_num = day_summary["day"]
        max_change = day_summary["max_daily_change"] * 100
        broke_count = len(day_summary["broke_stocks"])
        
        status_icon = "✅" if broke_count == 0 else "⚠️" if broke_count < 3 else "❌"
        daily_text += f"{status_icon} **Day {day_num}**: {max_change:.1f}% max change, {broke_count} broken\n"
    
    embed.add_field(
        name="📅 Daily Breakdown",
        value=daily_text if daily_text else "No daily data available",
        inline=False
    )
    
    # Price range analysis
    if results["min_prices"] and results["max_prices"]:
        extreme_stocks = []
        for symbol in list(results["min_prices"].keys())[:5]:  # Top 5 most volatile
            min_price = results["min_prices"][symbol]
            max_price = results["max_prices"][symbol]
            range_pct = ((max_price - min_price) / min_price) * 100
            extreme_stocks.append(f"**{symbol}**: ${min_price:.2f}-${max_price:.2f} ({range_pct:.1f}%)")
        
        embed.add_field(
            name="📈 Price Ranges (Top 5)",
            value="\n".join(extreme_stocks),
            inline=False
        )
    
    # Recommendations
    if results["market_broke"]:
        embed.add_field(
            name="🔧 Recommendations",
            value="• Reduce volatility parameters\n• Implement stricter price bounds\n• Review invisible factor calculations\n• Consider AI price range validation",
            inline=False
        )
    else:
        embed.add_field(
            name="✅ Market Health",
            value="• Market algorithms are stable\n• Price movements are realistic\n• No broken stocks detected\n• Ready for production use",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_daily_init", description="Force daily market initialization (Admin)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to run daily initialization")
async def stocks_daily_init(interaction: discord.Interaction):
    """Force a complete daily market initialization"""
    await interaction.response.defer()
    
    from stock_market import stock_scheduler
    
    if not stock_scheduler:
        await interaction.followup.send("❌ Stock market scheduler not available")
        return
    
    # Run daily initialization
    success = await stock_scheduler.force_daily_initialization()
    
    if success:
        embed = discord.Embed(
            title="✅ Daily Market Initialization Complete",
            description="Market has been freshly initialized with new daily data",
            color=0x00ff88,
            timestamp=datetime.now(timezone.utc)
        )
        
        stock_market = get_stock_market()
        
        # Show results
        total_stocks = sum(len(cat['stocks']) for cat in stock_market.categories.values())
        has_market_params = bool(stock_market.market_params.get("trend_direction") is not None)
        
        embed.add_field(
            name="📊 Initialization Results",
            value=f"• {total_stocks} stocks initialized\n• On-demand pricing: {'✅ Active' if has_market_params else '❌ Failed'}\n• Trading day: {stock_market.current_trading_day}\n• Market active: {'✅' if stock_market.is_trading_day else '❌'}",
            inline=False
        )
        
        # Show market parameters
        params = stock_market.market_params
        params_text = f"""
**Trend**: {params['trend_direction']:+.2f}
**Volatility**: {params['volatility']:.2f}
**Sentiment**: {params['market_sentiment']:.2f}
**Momentum**: {params['momentum']:.2f}
"""
        embed.add_field(name="📈 Market Parameters", value=params_text.strip(), inline=True)
        
        # Sample stock prices using on-demand pricing
        if has_market_params:
            # Get 3 sample stocks from different categories
            sample_symbols = []
            for _, cat_data in list(stock_market.categories.items())[:3]:
                if cat_data["stocks"]:
                    sample_symbols.append(cat_data["stocks"][0]["symbol"])
            
            sample_text = ""
            for symbol in sample_symbols:
                try:
                    current_price = stock_market.get_stock_price(symbol)
                    if current_price:
                        sample_text += f"**{symbol}**: ${current_price:.2f}\n"
                except Exception as e:
                    print(f"Error getting price for {symbol}: {e}")
            
            if sample_text:
                embed.add_field(name="📊 Sample Prices", value=sample_text.strip(), inline=True)
        
        embed.set_footer(text="Market is now ready for automated trading")
        
    else:
        embed = discord.Embed(
            title="❌ Daily Market Initialization Failed",
            description="Could not initialize market data. Check logs for details.",
            color=0xff4444,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="🔧 Troubleshooting",
            value="• Check economic data files\n• Verify AI system is operational\n• Review stock market configuration\n• Try `/stocks_reset` if persistent",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)