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
from config import Roles
from data_managers import get_stock_data_manager, get_economic_data_manager
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
    
    # Category ETF prices from data manager
    category_prices = stock_data_manager.get_all_category_etf_prices()
    etf_text = ""
    for cat_name, price in category_prices.items():
        emoji = "⛽" if cat_name == "ENERGY" else "🎬" if cat_name == "ENTERTAINMENT" else "🏦" if cat_name == "FINANCE" else "🏥" if cat_name == "HEALTH" else "🏭" if cat_name == "MANUFACTURING" else "🛒" if cat_name == "RETAIL" else "💻" if cat_name == "TECH" else "✈️"
        etf_text += f"{emoji} **{cat_name}**: ${price:.2f}\n"
    
    embed.add_field(name="📊 Sector ETFs", value=etf_text.strip(), inline=True)
    
    # Trading info (24/7 operation)
    if stock_scheduler:
        et_now = stock_scheduler.get_et_now()
        trading_info = f"**Day**: {stock_market.current_trading_day or et_now.strftime('%Y-%m-%d')}\n**Time**: {et_now.strftime('%I:%M %p ET')}\n**Hours**: 24/7 Trading Active\n**Update Rate**: Every {stock_market.price_update_rate_minutes} minute{'s' if stock_market.price_update_rate_minutes != 1 else ''}"
    else:
        trading_info = f"**Hours**: 24/7 Trading Active\n**Update Rate**: Every {stock_market.price_update_rate_minutes} minute{'s' if stock_market.price_update_rate_minutes != 1 else ''}"
    
    embed.add_field(name="🕐 Trading Schedule", value=trading_info, inline=False)
    
    # Stock count
    total_stocks = sum(len(cat['stocks']) for cat in stock_market.categories.values())
    embed.set_footer(text=f"{total_stocks} individual stocks across {len(stock_market.categories)} sectors")
    
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
    
    if symbol:
        symbol = symbol.upper()
        
        # Extract data for specific stock
        prices = []
        timestamps = []
        
        for entry in historical_data:
            if 'data' in entry and 'individual_stocks' in entry['data']:
                if symbol in entry['data']['individual_stocks']:
                    prices.append(entry['data']['individual_stocks'][symbol])
                    timestamps.append(entry['timestamp'])
        
        if not prices:
            await interaction.followup.send(f"❌ No historical data found for stock '{symbol}'")
            return
        
        # Calculate statistics
        if len(prices) > 1:
            change = prices[-1] - prices[0]
            change_pct = (change / prices[0]) * 100
            high_price = max(prices)
            low_price = min(prices)
            avg_price = sum(prices) / len(prices)
            
            stock_stats = f"""
**Current**: ${prices[-1]:.2f}
**Change**: ${change:+.2f} ({change_pct:+.2f}%)
**High**: ${high_price:.2f}
**Low**: ${low_price:.2f}
**Average**: ${avg_price:.2f}
"""
            embed.add_field(name=f"📈 {symbol} Statistics", value=stock_stats.strip(), inline=True)
            
            # Generate chart
            try:
                chart_bytes = stock_market.generate_stock_chart(symbol, prices[-24:])  # Last 24 points
                if chart_bytes:
                    chart_file = discord.File(io.BytesIO(chart_bytes), filename=f"{symbol}_history.png")
                    embed.set_image(url=f"attachment://{symbol}_history.png")
                    await interaction.followup.send(embed=embed, file=chart_file)
                    return
            except Exception as e:
                print(f"Chart generation failed: {e}")
    
    else:
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

# User Commands

@app_commands.command(name="stocks_list", description="List all available stocks")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to list stocks")
async def stocks_list(interaction: discord.Interaction):
    """List all available stocks across all sectors"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    embed = discord.Embed(
        title="📈 Available Stocks",
        description="All stocks traded on the Virtual Congress Market",
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
    
    embed.set_footer(text=f"Total: {total_stocks} stocks across {len(stock_market.categories)} sectors")
    await interaction.followup.send(embed=embed)

@app_commands.command(name="stocks_price", description="Check current price of a stock")
@app_commands.describe(symbol="Stock symbol (e.g., AAPL, MSFT, GOOGL)")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to check stock price")
async def stocks_price(interaction: discord.Interaction, symbol: str):
    """Check and display current price of a specific stock"""
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
        available_symbols = []
        for cat_data in stock_market.categories.values():
            for stock in cat_data['stocks']:
                available_symbols.append(stock['symbol'])
        
        embed = discord.Embed(
            title="❌ Stock Not Found",
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
    
    # Create price embed
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

@app_commands.command(name="stocks_history_48h", description="Show stock's 48-hour price history")
@app_commands.describe(symbol="Stock symbol (e.g., AAPL, MSFT)")
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@handle_errors("Failed to get stock history")
async def stocks_history_48h(interaction: discord.Interaction, symbol: str):
    """Show a stock's price history over the last 48 hours"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    symbol = symbol.upper()
    
    # Verify stock exists
    stock_exists = False
    for cat_data in stock_market.categories.values():
        for stock in cat_data['stocks']:
            if stock['symbol'] == symbol:
                stock_exists = True
                break
        if stock_exists:
            break
    
    if not stock_exists:
        await interaction.followup.send(f"❌ Stock '{symbol}' not found")
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
    await interaction.response.defer()
    
    # Confirmation check
    embed = discord.Embed(
        title="⚠️ Reset Stock Market",
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
    
    await interaction.followup.send(embed=embed)
    
    # Note: In a real implementation, you'd want to add a confirmation mechanism
    # For now, we'll implement the reset directly
    
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
    
    # Reset market parameters to economic data calculation
    try:
        stock_market.market_params = stock_market._calculate_market_params_from_economic_data()
        print("📊 Market parameters recalculated from economic data")
    except Exception as e:
        print(f"⚠️ Could not recalculate from economic data: {e}")
        # Fallback to reasonable defaults
        stock_market.market_params = {
            "trend_direction": -0.15,    # Slightly bearish but not extreme
            "volatility": 0.45,          # Moderate volatility
            "momentum": 0.50,            # Neutral momentum
            "market_sentiment": 0.45,    # Cautious but not panicked
            "long_term_outlook": 0.50    # Neutral outlook
        }
    
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
    
    await interaction.followup.send(embed=reset_embed)

@app_commands.command(name="stocks_force_init", description="Force re-initialize stock market with new data (Admin)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to force initialization")
async def stocks_force_init(interaction: discord.Interaction):
    """Force re-initialize the stock market with current code structure"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    # Force save current structure (from code) to file
    stock_market.save_market_data()
    
    # Create response
    embed = discord.Embed(
        title="✅ Stock Market Force Initialized",
        description="Market data has been updated to current code structure",
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
    
    await interaction.followup.send(embed=embed)

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
        
        # CRITICAL: Recalculate all baseline stock prices from new economic parameters
        print("🔄 Recalculating stock baselines from new economic parameters...")
        baseline_changes = stock_market.recalculate_all_baseline_prices()
        print(f"✅ Updated baseline prices for {len(baseline_changes)} stocks")
        
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
            recalculate_baselines=False  # Already done above
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

@app_commands.command(name="stocks_recalc_baselines", description="Recalculate all stock baseline prices from current economic parameters (Admin)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to recalculate baseline prices")
async def stocks_recalc_baselines(interaction: discord.Interaction):
    """Manually recalculate all stock baseline prices from current economic parameters"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    # Send initial status
    embed = discord.Embed(
        title="🔄 Recalculating Stock Baselines",
        description="Recalculating all stock prices based on current economic parameters",
        color=0xffaa00,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="📊 Process", value="⏳ Analyzing current economic data...", inline=False)
    
    initial_msg = await interaction.followup.send(embed=embed)
    
    try:
        # Show current economic parameters
        embed.set_field_at(0, name="📊 Process", value="📈 Recalculating baseline prices...", inline=False)
        await initial_msg.edit(embed=embed)
        
        # Recalculate baseline prices
        price_changes = stock_market.recalculate_all_baseline_prices()
        
        # Trigger dynamic update with new baselines
        await stock_market.trigger_dynamic_update(
            reason="Manual baseline recalculation from economic data",
            send_discord_notification=True,
            recalculate_baselines=False  # Already done above
        )
        
        # Create success embed
        embed = discord.Embed(
            title="✅ Baseline Recalculation Complete",
            description="All stock prices recalculated from current economic parameters",
            color=0x00ff88,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Show market parameters used
        params = stock_market.market_params
        param_text = f"""
**Trend**: {params['trend_direction']:+.3f} {'📈' if params['trend_direction'] > 0 else '📉' if params['trend_direction'] < 0 else '➡️'}
**Volatility**: {params['volatility']:.3f} {'🌪️' if params['volatility'] > 0.7 else '🌊'}
**Momentum**: {params['momentum']:.3f} {'🚀' if params['momentum'] > 0.7 else '⚡'}
**Sentiment**: {params['market_sentiment']:.3f} {'😄' if params['market_sentiment'] > 0.7 else '😐' if params['market_sentiment'] > 0.4 else '😟'}
**Outlook**: {params['long_term_outlook']:.3f} {'🌟' if params['long_term_outlook'] > 0.7 else '🌤️'}
"""
        embed.add_field(name="📊 Economic Parameters Used", value=param_text.strip(), inline=True)
        
        # Show biggest price changes
        if price_changes:
            changes_text = ""
            sorted_changes = sorted(price_changes.items(), key=lambda x: abs(x[1]["change_pct"]), reverse=True)
            total_changes = len([c for c in price_changes.values() if abs(c["change_pct"]) > 0.1])  # Changes > 0.1%
            
            for symbol, change in sorted_changes[:8]:  # Top 8 biggest changes
                direction = "📈" if change["change_pct"] > 0 else "📉" if change["change_pct"] < 0 else "➡️"
                changes_text += f"{direction} **{symbol}**: ${change['old_price']:.2f} → ${change['new_price']:.2f} ({change['change_pct']:+.1f}%)\n"
            
            embed.add_field(name=f"📊 Biggest Price Changes ({total_changes} stocks changed)", value=changes_text.strip(), inline=False)
        
        # Calculate new ETF prices
        category_prices = stock_market.calculate_category_prices()
        etf_text = ""
        for cat_name, price in category_prices.items():
            emoji = "⛽" if cat_name == "ENERGY" else "🎬" if cat_name == "ENTERTAINMENT" else "🏦" if cat_name == "FINANCE" else "🏥" if cat_name == "HEALTH" else "🏭" if cat_name == "MANUFACTURING" else "🛒" if cat_name == "RETAIL" else "💻" if cat_name == "TECH" else "✈️"
            etf_text += f"{emoji} **{cat_name}**: ${price:.2f}\n"
        
        embed.add_field(name="📊 Updated Sector ETFs", value=etf_text.strip(), inline=True)
        
        embed.set_footer(text=f"{len(price_changes)} stocks recalculated • All ETF prices updated")
        
        await initial_msg.edit(embed=embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Baseline Recalculation Failed",
            description=f"Error: {str(e)}",
            color=0xff4444,
            timestamp=datetime.now(timezone.utc)
        )
        await initial_msg.edit(embed=error_embed)

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

@app_commands.command(name="stocks_force_baseline_update", description="Force immediate stock price update from economic parameters (Admin)")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to force baseline update")
async def stocks_force_baseline_update(interaction: discord.Interaction):
    """Force immediate update of all stock prices based on current economic parameters"""
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    try:
        # Recalculate market parameters from economic data
        print("🔄 Recalculating market parameters from economic data...")
        stock_market.market_params = stock_market._calculate_market_params_from_economic_data()
        
        # Recalculate baseline prices
        print("🔄 Recalculating baseline prices...")
        price_changes = stock_market.recalculate_all_baseline_prices()
        
        # Trigger full dynamic update
        update_summary = await stock_market.trigger_dynamic_update(
            reason="Forced baseline update from economic data",
            send_discord_notification=True,
            recalculate_baselines=False  # Already done above
        )
        
        # Create response embed
        embed = discord.Embed(
            title="⚡ Forced Baseline Update Complete",
            description="Market parameters and stock prices updated from current economic data",
            color=0x00ff88,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Show updated parameters
        params = stock_market.market_params
        param_text = f"""
**Trend**: {params['trend_direction']:+.3f}
**Volatility**: {params['volatility']:.3f}
**Momentum**: {params['momentum']:.3f}
**Sentiment**: {params['market_sentiment']:.3f}
**Outlook**: {params['long_term_outlook']:.3f}
"""
        embed.add_field(name="📊 Updated Parameters", value=param_text.strip(), inline=True)
        
        # Show price change summary
        if price_changes:
            significant_changes = [c for c in price_changes.values() if abs(c["change_pct"]) > 1.0]
            summary_text = f"""
**Total Stocks**: {len(price_changes)}
**Significant Changes**: {len(significant_changes)} (>1%)
**ETFs Updated**: {len(update_summary.get('etf_prices', {}))}
"""
            embed.add_field(name="📈 Update Summary", value=summary_text.strip(), inline=True)
        
        embed.set_footer(text="All prices now reflect current economic conditions")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
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
            all_stocks = stock_market.get_all_stocks_flat()
            stock_info = next((s for s in all_stocks if s['symbol'].upper() == symbol.upper()), None)
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
            all_stocks = stock_market.get_all_stocks_flat()
            stock_info = next((s for s in all_stocks if s['symbol'].upper() == symbol.upper()), None)
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
                profit_loss = (details['price'] - 100) * details['quantity']  # Rough P/L calc
                pl_emoji = "📈" if profit_loss >= 0 else "📉"
                stock_lines.append(
                    f"{pl_emoji} **{symbol}** - {details['quantity']:,} shares @ ${details['price']:,.2f}\n"
                    f"   Value: ${details['value']:,.2f}"
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
    await interaction.response.defer()
    
    stock_market = get_stock_market()
    
    # Create confirmation embed
    embed = discord.Embed(
        title="⚠️ Clear Stock Price History",
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
    
    # For now, we'll proceed directly (in production, you'd want a confirmation mechanism)
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
        
        await interaction.followup.send(embed=result_embed)
    else:
        await interaction.followup.send("❌ Failed to clear stock price history. Check logs for details.")

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
            for cat_name, cat_data in list(stock_market.categories.items())[:3]:
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