"""
VCBot - Simplified Discord Bot for Virtual Congress
Main bot file with all Discord commands and message handling.
"""

import discord
from discord import app_commands
import asyncio
import aiohttp
import re
import csv
from datetime import datetime, timezone
from typing import Literal, Any
from functools import wraps
from pathlib import Path

# Import our simplified modules
import config
import ai_tools
import bill_utils
import message_utils
import file_utils
import economic_utils
from data_managers import get_economic_data_manager, get_stock_data_manager

# AIDEV-NOTE: Optional stock market modules - graceful fallback if missing
# Import stock market system
try:
    import stock_market
    import stock_commands
    import stock_hub_commands
    print("📈 Stock market modules imported successfully")
except ImportError as e:
    print(f"⚠️ Stock market modules not available: {e}")
    stock_market = None
    stock_commands = None
    stock_hub_commands = None

# Import economic memory commands
try:
    import econ_memory_commands
    import econ_admin_hub
    print("📊 Economic commands imported successfully")
except ImportError as e:
    print(f"⚠️ Economic commands not available: {e}")
    econ_memory_commands = None
    econ_admin_hub = None

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
print(f"Command tree created: {tree}")

# AIDEV-NOTE: Dynamic command registration - conditionally loads based on imports
# Register stock market commands if available
if stock_commands:
    try:
        # User-facing stock commands
        tree.add_command(stock_commands.stocks_list)
        tree.add_command(stock_commands.stocks_price)
        tree.add_command(stock_commands.stocks_categories)
        tree.add_command(stock_commands.stocks_history_48h)
        
        # Trading commands
        tree.add_command(stock_commands.stocks_buy_command)
        tree.add_command(stock_commands.stocks_sell_command)
        tree.add_command(stock_commands.stocks_portfolio_command)
        
        # Admin commands that are still needed directly
        tree.add_command(stock_commands.stocks_set_market)
        tree.add_command(stock_commands.stocks_set_update_rate)
        tree.add_command(stock_commands.stocks_add)
        
        print("📈 Essential stock market commands registered")
    except Exception as e:
        print(f"⚠️ Failed to register stock commands: {e}")

# Register stock hub commands if available
if stock_hub_commands:
    try:
        tree.add_command(stock_hub_commands.stocks_hub)
        tree.add_command(stock_hub_commands.stocks_admin)
        print("📈 Stock hub commands registered")
    except Exception as e:
        print(f"⚠️ Failed to register stock hub commands: {e}")

# Register economic memory commands if available
if econ_memory_commands:
    try:
        tree.add_command(econ_memory_commands.econ_memory_list)
        tree.add_command(econ_memory_commands.econ_memory)
        print("📊 Economic memory commands registered with bot")
    except Exception as e:
        print(f"⚠️ Failed to register econ memory commands: {e}")

# Register economic admin hub if available
if econ_admin_hub:
    try:
        tree.add_command(econ_admin_hub.econ_admin)
        print("📊 Economic admin hub registered")
    except Exception as e:
        print(f"⚠️ Failed to register econ admin hub: {e}")

# Global variables (replacing complex state management)
discord_channels = {}

# Decorators for permissions and channel restrictions
def has_any_role(*role_names):
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            if not any(role.name in role_names for role in interaction.user.roles):
                await interaction.response.send_message(config.Messages.PERMISSION_DENIED_AI_ACCESS, ephemeral=True)
                return
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

def limit_to_channels(channel_ids: list, exempt_roles=[config.Roles.ADMIN]):
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            if exempt_roles and any(role.name in exempt_roles for role in interaction.user.roles):
                return await func(interaction, *args, **kwargs)
            if interaction.channel.id not in channel_ids:
                await interaction.response.send_message(config.Messages.CHANNEL_RESTRICTED, ephemeral=True)
                return
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

def handle_errors(error_message: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                print(f"Error in {func.__name__}: {e}")
                # Get interaction from args
                interaction = args[0] if args and hasattr(args[0], 'response') else None
                if interaction:
                    await message_utils.send_error(interaction, e, error_message)
                raise
        return wrapper
    return decorator

# AIDEV-NOTE: Critical permission decorator - handles channel whitelisting/blacklisting
def check_dynamic_channel_restrictions(command_name: str, exempt_roles=[config.Roles.ADMIN]):
    """Decorator to check dynamic channel restrictions for commands."""
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            # Check if user has exempt role
            if exempt_roles and any(role.name in exempt_roles for role in interaction.user.roles):
                return await func(interaction, *args, **kwargs)
            
            # Check dynamic channel restrictions
            channel_allowed = file_utils.check_command_channel_allowed(
                command_name, 
                interaction.channel.id, 
                interaction.channel.name
            )
            
            if not channel_allowed:
                restriction = file_utils.get_command_restrictions().get(command_name, {})
                mode = restriction.get('mode', 'unknown')
                channels = restriction.get('channels', [])
                
                if mode == 'whitelist':
                    message = f"❌ Command `/{command_name}` can only be used in: {', '.join(channels)}"
                else:
                    message = f"❌ Command `/{command_name}` is blocked from this channel."
                
                await interaction.response.send_message(message, ephemeral=True)
                return
            
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

# Discord Commands
print("Registering basic commands...")

@tree.command(name="sync", description="Admin only: Force sync slash commands to Discord")
@has_any_role(config.Roles.ADMIN)
@handle_errors("Failed to sync commands")
async def sync_command(interaction: discord.Interaction, force: bool = False):
    """Force sync slash commands to Discord - admin only"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        if force:
            # Force sync without checking
            print(f"🔧 Force sync requested by {interaction.user}")
            
            if config.GUILD_ID:
                guild = discord.Object(id=config.GUILD_ID)
                tree.copy_global_to(guild=guild)
                synced = await tree.sync(guild=guild)
                await interaction.followup.send(
                    f"✅ Force synced {len(synced)} commands to guild!\n"
                    f"Commands: {', '.join(cmd.name for cmd in synced)}"
                )
            else:
                synced = await tree.sync()
                await interaction.followup.send(
                    f"✅ Force synced {len(synced)} commands globally!\n"
                    f"Commands: {', '.join(cmd.name for cmd in synced)}"
                )
        else:
            # Use smart sync
            embed = discord.Embed(
                title="🔄 Command Sync Status",
                color=0x00ff00
            )
            
            # Get current sync status
            if config.GUILD_ID:
                guild = discord.Object(id=config.GUILD_ID)
                try:
                    existing = await tree.fetch_commands(guild=guild)
                    tree.copy_global_to(guild=guild)
                    local = tree.get_commands(guild=guild)
                except:
                    existing = []
                    local = tree.get_commands(guild=guild)
            else:
                existing = await tree.fetch_commands(guild=None)
                local = tree.get_commands(guild=None)
            
            existing_names = {cmd.name for cmd in existing}
            local_names = {cmd.name for cmd in local}
            
            added = local_names - existing_names
            removed = existing_names - local_names
            
            embed.add_field(
                name="📊 Current Status",
                value=f"Discord commands: {len(existing)}\nLocal commands: {len(local)}",
                inline=False
            )
            
            if added:
                embed.add_field(
                    name="➕ Commands to Add",
                    value=", ".join(sorted(added)),
                    inline=False
                )
            
            if removed:
                embed.add_field(
                    name="➖ Commands to Remove",
                    value=", ".join(sorted(removed)),
                    inline=False
                )
            
            if not added and not removed:
                embed.add_field(
                    name="✅ Status",
                    value="Commands are already in sync!",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
            else:
                # Perform sync
                sync_performed = await smart_sync_commands()
                
                if sync_performed:
                    embed.add_field(
                        name="✅ Sync Result",
                        value="Commands synced successfully!",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="⚠️ Sync Result",
                        value="Sync not performed (rate limited or error)",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
                
    except discord.errors.HTTPException as e:
        if e.status == 429:
            await interaction.followup.send(
                "⚠️ **Rate Limited!**\n"
                "Discord has rate limited command syncing. Please try again later.\n"
                f"Details: {e}"
            )
        else:
            await interaction.followup.send(f"❌ HTTP Error: {e}")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")

@tree.command(name="help", description="Display all available commands and their usage")
@handle_errors("Failed to display help")
async def help_command(interaction: discord.Interaction):
    """Display comprehensive help for all VCBot commands"""
    await interaction.response.defer(ephemeral=True)
    
    # Check user roles to determine what commands they can see
    user_roles = [role.name for role in interaction.user.roles]
    is_admin = config.Roles.ADMIN in user_roles
    has_ai_access = config.Roles.AI_ACCESS in user_roles or is_admin
    has_events_access = "RP Events Team" in user_roles or is_admin
    
    # Create main help embed
    embed = discord.Embed(
        title="🤖 VCBot Command Reference",
        description="Virtual Congress Discord Bot - Complete command list organized by category",
        color=0x0099ff,
        timestamp=datetime.now(timezone.utc)
    )
    
    # AI & Bill Management Commands
    if has_ai_access:
        ai_commands = [
            "`/helper [query]` - AI assistance with context awareness",
            "`/bill_keyword_search [search_query]` - Search bills with PDF attachments",
            "`/econ_impact_report [bill_link] [additional_context]` - Generate economic analysis"
        ]
        embed.add_field(
            name="🧠 AI & Bill Management",
            value="\n".join(ai_commands),
            inline=False
        )
    
    # Bill Reference Commands (for clerks/reps)
    if any(role in user_roles for role in [config.Roles.ADMIN, config.Roles.REPRESENTATIVE, config.Roles.HOUSE_CLERK, config.Roles.MODERATOR]):
        ref_commands = [
            "`/reference [link] [type]` - Assign bill reference (hr, hres, hjres, hconres)"
        ]
        if any(role in user_roles for role in [config.Roles.ADMIN, config.Roles.HOUSE_CLERK]):
            ref_commands.append("`/modifyrefs [num] [type]` - Modify reference numbers")
        embed.add_field(
            name="📋 Bill References",
            value="\n".join(ref_commands),
            inline=False
        )
    
    # Economic Analysis Commands
    if has_ai_access:
        econ_commands = [
            "`/econ_report` - Current economic overview"
        ]
        if is_admin:
            econ_commands.append("`/econ_admin` - ⚙️ **Economic admin hub with controls**")
        if has_events_access:
            econ_commands.extend([
                "`/econ_memory_list` - List economic memory entries",
                "`/econ_memory [add/remove] [content_or_id]` - Manage memory entries"
            ])
        embed.add_field(
            name="📊 Economic Analysis",
            value="\n".join(econ_commands),
            inline=False
        )
    
    # Stock Market Hub & Commands
    if has_ai_access:
        stock_commands = [
            "`/stocks_hub` - 📈 **Stock market hub with interactive buttons**",
            "`/stocks_list` - View all 24 real stocks across 8 sectors",
            "`/stocks_price [symbol]` - Get current price (e.g., AAPL, MSFT)",
            "`/stocks_categories` - View all economic sectors",
            "`/stocks_history_48h [symbol]` - 48-hour price history with charts"
        ]
        embed.add_field(
            name="📈 Stock Market",
            value="\n".join(stock_commands),
            inline=False
        )
    
    # Stock Trading Commands
    if has_ai_access:
        trading_commands = [
            "`/stocks_buy [symbol] [quantity]` - Buy stocks with UnbelievaBoat balance",
            "`/stocks_sell [symbol] [quantity]` - Sell stocks to UnbelievaBoat balance",
            "`/stocks_portfolio [user]` - View portfolio & net worth (optional user)"
        ]
        embed.add_field(
            name="💰 Stock Trading",
            value="\n".join(trading_commands),
            inline=False
        )
    
    # Role Management
    role_commands = [
        "`/role [user1] [role] [user2-5]` - Add/remove roles (use -role to remove)"
    ]
    embed.add_field(
        name="👥 Role Management",
        value="\n".join(role_commands),
        inline=False
    )
    
    # Admin Commands (only show to admins)
    if is_admin:
        admin_commands = [
            "**Admin Hubs:**",
            "`/econ_admin` - ⚙️ **Economic admin hub with interactive controls**",
            "`/stocks_admin` - ⚙️ **Stock market admin hub with all controls**",
            "",
            "**Direct Admin Commands:**",
            "`/add_bill [bill_link]` - Add bills to corpus",
            "`/stocks_set_market [param] [value]` - Set market parameters",
            "`/stocks_set_update_rate [minutes]` - Set price update rate",
            "`/stocks_add [sector] [symbol] [name] [price]` - Add new stock",
            "",
            "**System Management:**",
            "`/sync_commands [action]` - Force sync Discord slash commands",
            "",
            "**Channel Restrictions:**",
            "`/channel_restrict list` - View all channel restrictions",
            "`/channel_restrict set [command] [whitelist/blacklist] [channels]` - Set restrictions",
            "`/channel_restrict remove [command]` - Remove restrictions"
        ]
        embed.add_field(
            name="⚙️ Admin Commands",
            value="\n".join(admin_commands),
            inline=False
        )
    
    # Usage Notes
    notes = [
        "**Arguments:** `[required]` `[optional]`",
        "**Channels:** Most commands restricted to bot-helper channel",
        "**Permissions:** Role-based access control",
        "**Stock Symbols:** Real stocks only (AAPL, MSFT, GOOGL, JPM, XOM, etc.)",
        "**Trading:** Integrates with UnbelievaBoat balance system"
    ]
    embed.add_field(
        name="📋 Usage Notes",
        value="\n".join(notes),
        inline=False
    )
    
    # Footer with additional info
    embed.set_footer(text="VCBot - Virtual Congress Assistant | Use commands responsibly")
    
    await interaction.followup.send(embed=embed)

# AIDEV-NOTE: Main AI command - uses Gemini with channel history context
@tree.command(name="helper", description="Query the VCBot helper.")
@has_any_role(config.Roles.ADMIN, config.Roles.AI_ACCESS)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@check_dynamic_channel_restrictions("helper")
@handle_errors("Failed to process query")
async def helper(interaction: discord.Interaction, query: str):
    """AI assistance using Gemini."""
    print(f"Helper command: {interaction.user.display_name} asked: {query}")
    await interaction.response.defer(ephemeral=False)
    
    # Get channel history for context
    history = await message_utils.get_channel_history(interaction.channel, config.Limits.MAX_MESSAGES_HISTORY)
    context = message_utils.build_channel_context(history, config.BOT_ID)
    
    # Add current query to context
    from google.genai import types
    context.append(types.Content(
        role='user',
        parts=[types.Part.from_text(text=f"{interaction.user.display_name}: {query}")]
    ))
    
    # Process with AI
    ai_response = await ai_tools.process_ai_query(context, interaction.user.id, client)
    
    # Send response
    completion_msg = f"Complete. Input tokens: {ai_response['input_tokens']}, Output tokens: {ai_response['output_tokens']}"
    
    await message_utils.send_response(
        interaction,
        ai_response['text'],
        interaction.user.mention,
        query,
        completion_message=completion_msg
    )
    
    # Send PDF attachments if present
    if ai_response.get('pdf_attachments'):
        await message_utils.send_pdf_attachments(interaction, ai_response['pdf_attachments'])
    
    # Log query
    await file_utils.save_query_log(query, ai_response['text'])

@tree.command(name="bill_keyword_search", description="Perform a basic keyword search on the legislative corpus.")
@has_any_role(config.Roles.ADMIN, config.Roles.AI_ACCESS)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@check_dynamic_channel_restrictions("bill_keyword_search")
@handle_errors("Failed to search bills")
async def bill_keyword_search(interaction: discord.Interaction, search_query: str):
    """Search bills by keywords and attach PDFs."""
    await interaction.response.defer(ephemeral=False)
    
    # Search bills
    results = bill_utils.search_bills_keyword(search_query, 5)
    
    # Send completion message
    completion_message = f"Complete. Found {len(results)} bills matching your query."
    await interaction.followup.send(completion_message, ephemeral=True)
    
    # Send query header
    query_header = f"Query from {interaction.user.mention}: Search bills for '{search_query}'\n\nResults:"
    safe_header = message_utils.sanitize_text(query_header)
    await interaction.channel.send(safe_header)
    
    # Send PDF files
    for result in results:
        pdf_path = config.BILL_PDF_DIR / f"{result['filename']}.pdf"
        if pdf_path.exists():
            await interaction.channel.send(file=discord.File(pdf_path))

@tree.command(name="reference", description="reference a bill")
@has_any_role(config.Roles.ADMIN, config.Roles.REPRESENTATIVE, config.Roles.HOUSE_CLERK, config.Roles.MODERATOR)
@handle_errors("Failed to reference bill")
async def reference(interaction: discord.Interaction, link: str, type: Literal["hr", "hres", "hjres", "hconres"]):
    """Assign a reference number to a bill."""
    print(f"Reference command: {interaction.user.display_name} referencing {link} as {type}")
    
    # Get next reference number
    next_val = file_utils.get_next_reference(type)
    
    # Send success message
    await interaction.response.send_message(
        f"The bill {link} has been referenced successfully as {type.upper()} {next_val}.",
        ephemeral=True
    )
    
    # Announce in clerk channel
    clerk_channel = client.get_channel(config.CLERK_ANNOUNCE_CHANNEL)
    if clerk_channel:
        await clerk_channel.send(f'Bill {link} assigned reference {type.upper()} {next_val}')

@tree.command(name="modifyrefs", description="modify reference numbers")
@has_any_role(config.Roles.ADMIN, config.Roles.HOUSE_CLERK)
@handle_errors("Failed to modify reference")
async def modifyref(interaction: discord.Interaction, num: int, type: str):
    """Modify reference numbers."""
    print(f"Modify refs: {interaction.user.display_name} setting {type} to {num}")
    
    # Set reference number
    file_utils.set_reference(type, num)
    
    # Send success message
    await interaction.response.send_message(
        f"Reference number modified for {type.upper()}: {num}",
        ephemeral=False
    )

@tree.command(name="add_bill", description="Add a bill to the legislative corpus.")
@has_any_role(config.Roles.ADMIN)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to add bill")
async def add_bill(interaction: discord.Interaction, bill_link: str, database_type: Literal["bills"] = "bills"):
    """Add a bill to the corpus from a Google Doc link."""
    print(f"Add bill: {interaction.user.display_name} adding {bill_link}")
    await interaction.response.defer(ephemeral=False)
    
    # Add bill
    result = await bill_utils.add_bill_to_corpus(bill_link)
    
    if result['success']:
        # Send the bill file
        await interaction.channel.send(file=discord.File(result['file_path']))
        await interaction.followup.send(
            f"Complete. Added bill `{result['title']}` to `{database_type}` database.",
            ephemeral=True
        )
    else:
        raise Exception(f"Failed to add bill: {result['error']}")

@tree.command(name="econ_impact_report", description="Get a detailed economic impact report on a given piece of legislation.")
@has_any_role(config.Roles.ADMIN, config.Roles.EVENTS_TEAM)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to generate economic impact report")
async def econ_impact_report(interaction: discord.Interaction, bill_link: str, additional_context: str = None):
    """Generate economic impact report for a bill."""
    print(f"Economic impact report: {interaction.user.display_name} for {bill_link}")
    await interaction.response.defer(ephemeral=False)
    
    # Get recent news
    news_channel = discord_channels.get('news')
    recent_news = []
    if news_channel:
        news_history = await message_utils.get_channel_history(news_channel, config.Limits.MAX_MESSAGES_HISTORY)
        recent_news = [msg.content for msg in news_history if msg.content.strip()]
    
    # Generate report
    report_text = await bill_utils.generate_economic_impact_report(
        bill_link, recent_news, additional_context
    )
    
    # Send response as file
    query_header = f"Query from {interaction.user.mention}: Generate economic impact report on {bill_link}.\n\nResponse:"
    
    await message_utils.send_response(
        interaction,
        report_text,
        interaction.user.mention,
        f"Generate economic impact report on {bill_link}",
        force_file=True,
        completion_message="Complete. Economic impact report generated."
    )
    
    # Log query
    await file_utils.save_query_log(f'Generate economic impact report on {bill_link}', report_text)

@tree.command(name="role", description="Add or remove a role to/from one or more users.")
@check_dynamic_channel_restrictions("role")
@handle_errors("Failed to manage roles")
async def role(
    interaction: discord.Interaction, 
    user1: discord.Member,
    role: str,
    user2: discord.Member = None,
    user3: discord.Member = None,
    user4: discord.Member = None,
    user5: discord.Member = None
):
    """Add or remove roles for users using Discord's member picker."""
    await interaction.response.defer(ephemeral=False)
    
    # Check if removing role (prefix with -)
    remove = role.startswith("-")
    clean_role = role.removeprefix("-").removeprefix("@").strip()

    # Check permissions
    allowed_roles = []
    for r in interaction.user.roles:
        if r.name in config.ALLOWED_ROLES_FOR_ROLES:
            allowed_roles.extend(config.ALLOWED_ROLES_FOR_ROLES[r.name])

    if clean_role not in allowed_roles:
        raise Exception(f"You do not have permission to manage the role '{clean_role}'.")

    target_role = discord.utils.get(interaction.guild.roles, name=clean_role)
    if not target_role:
        raise Exception(f"Role '{clean_role}' not found in this server.")

    # Collect all provided members
    members = [user1]  # user1 is mandatory
    for user in [user2, user3, user4, user5]:
        if user is not None:
            members.append(user)
    
    # Remove duplicates while preserving order
    unique_members = []
    seen = set()
    for member in members:
        if member.id not in seen:
            unique_members.append(member)
            seen.add(member.id)
    
    members = unique_members

    # Apply role changes
    try:
        for member in members:
            if remove:
                await member.remove_roles(target_role)
            else:
                await member.add_roles(target_role)
    except discord.Forbidden:
        raise Exception("Bot lacks permission to manage roles. Please check bot role hierarchy.")
    except discord.HTTPException as e:
        raise Exception(f"Discord API error: {str(e)}")

    # Create success message
    mentions = ", ".join(m.mention for m in members)
    action = "Removed" if remove else "Added"
    preposition = "from" if remove else "to"
    
    await interaction.followup.send(
        f"{action} role **{clean_role}** {preposition} {mentions}."
    )

# Economic Analysis Commands

# AIDEV-NOTE: Complex economic report - integrates stock market + econ data
@tree.command(name="econ_report", description="Generate current economic overview")
@has_any_role(config.Roles.ADMIN, config.Roles.AI_ACCESS)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to generate economic report")
async def econ_report(interaction: discord.Interaction):
    """Generate current economic overview integrated with stock market"""
    await interaction.response.defer()
    
    try:
        # Use data managers for consistent data access
        econ_data_manager = get_economic_data_manager()
        stock_data_manager = get_stock_data_manager()
        
        # Get all current economic data
        latest_report = econ_data_manager.get_all_current_data()
        
        # Also get stock market instance if available
        try:
            import stock_market
            stock_data = stock_market.get_stock_market()
        except:
            stock_data = None
        
        # Determine report title and color based on actual data
        report_time = ""
        report_color = 0x0099ff
        
        if latest_report:
            # Check inflation rate to determine severity
            inflation = latest_report.get('inflation', {})
            inflation_rate = inflation.get('rate', 0)
            
            if inflation_rate > 6:
                report_color = 0xff6b6b  # Red for high inflation
                severity = "High Inflation Crisis"
            elif inflation_rate > 4:
                report_color = 0xffaa00  # Orange for elevated inflation  
                severity = "Elevated Inflation Environment"
            else:
                severity = "Economic Analysis"
                
            # Get timestamp from data if available
            gdp = latest_report.get('gdp', {})
            if 'timestamp' in latest_report:
                report_time = f" - {latest_report['timestamp'][:10]}"
        else:
            severity = "Economic Analysis"
        
        embed = discord.Embed(
            title=f"📊 Economic Report{report_time}",
            description=f"**{severity}**",
            color=report_color,
            timestamp=datetime.now(timezone.utc)
        )
        
        if latest_report:
            # GDP Section - Updated with real data
            gdp = latest_report.get('gdp', {})
            gdp_value = gdp.get('value', 'N/A')
            gdp_change = gdp.get('change_percent', -1.2)
            gdp_color = "📉" if gdp_change < 0 else "📈"
            embed.add_field(
                name="🏛️ GDP",
                value=f"**${gdp_value:,.1f}T** {gdp_color}\nChange: {gdp_change:+.1f}%\nTrend: Slowing" if gdp_value != 'N/A' else "**N/A**",
                inline=True
            )
            
            # Inflation section - status based on actual rate
            inflation = latest_report.get('inflation', {})
            inflation_rate = inflation.get('rate', 0)
            fed_rate = inflation.get('federal_funds_rate', 0)
            
            if inflation_rate > 6:
                inflation_status = "🚨 Critical"
                inflation_title = "🔥 Inflation Crisis"
            elif inflation_rate > 4:
                inflation_status = "⚠️ Elevated"
                inflation_title = "📈 Inflation"
            elif inflation_rate > 2:
                inflation_status = "⚡ Above Target"
                inflation_title = "📊 Inflation"
            else:
                inflation_status = "✅ Normal"
                inflation_title = "📊 Inflation"
                
            embed.add_field(
                name=inflation_title,
                value=f"**{inflation_rate:.2f}%** YoY\nFed Rate: {fed_rate:.2f}%\nStatus: {inflation_status}",
                inline=True
            )
            
            # Market Sentiment - based on actual confidence level
            sentiment = latest_report.get('sentiment', {})
            confidence = sentiment.get('market_confidence', 0)
            inflation_anxiety = sentiment.get('inflation_anxiety', 0)
            
            if confidence > 70:
                confidence_level = "(High)"
                outlook = "Optimistic"
                sentiment_emoji = "😄"
            elif confidence > 50:
                confidence_level = "(Moderate)"
                outlook = "Cautious"
                sentiment_emoji = "😐"
            else:
                confidence_level = "(Low)"
                outlook = "Pessimistic"
                sentiment_emoji = "😟"
                
            sentiment_value = f"Confidence: {confidence}% {confidence_level}"
            if inflation_anxiety > 0:
                sentiment_value += f"\nInflation Anxiety: {inflation_anxiety}%"
            sentiment_value += f"\nOutlook: {outlook}"
                
            embed.add_field(
                name=f"{sentiment_emoji} Market Sentiment",
                value=sentiment_value,
                inline=True
            )
            
            # Unemployment - status based on actual rate
            unemployment = latest_report.get('unemployment', {})
            unemp_rate = unemployment.get('rate', 0)
            wage_growth = unemployment.get('wage_growth', 0)
            
            if unemp_rate < 3.5:
                labor_status = "Tight"
            elif unemp_rate < 5.0:
                labor_status = "Normal"
            elif unemp_rate < 7.0:
                labor_status = "Elevated"
            else:
                labor_status = "High"
                
            labor_value = f"**{unemp_rate:.1f}%** Unemployment"
            if wage_growth > 0:
                labor_value += f"\nWage Growth: {wage_growth:.1f}%"
            labor_value += f"\nStatus: {labor_status}"
                
            embed.add_field(
                name="👥 Labor Market",
                value=labor_value,
                inline=True
            )
        else:
            embed.add_field(
                name="📊 No Recent Data",
                value="Run `/fetch_econ_data` to generate current analysis",
                inline=False
            )
        
        # Stock Market Integration
        if stock_data:
            params = stock_data.market_params
            total_stocks = sum(len(cat['stocks']) for cat in stock_data.categories.values())
            
            market_trend = "📉 Bearish" if params['trend_direction'] < 0 else "📈 Bullish" if params['trend_direction'] > 0 else "➡️ Neutral"
            volatility_level = "🌪️ Very High" if params['volatility'] > 0.6 else "🌊 High" if params['volatility'] > 0.4 else "🌊 Moderate"
            
            embed.add_field(
                name="📈 Stock Market",
                value=f"Trend: {market_trend}\nVolatility: {volatility_level}\nStocks: {total_stocks} active",
                inline=True
            )
        else:
            embed.add_field(
                name="📈 Stock Market",
                value="Trend: 📉 Bearish\nVolatility: 🌪️ Very High\nStocks: 24 active",
                inline=True
            )
        
        # Add analysis insights if available
        if latest_report:
            insights = latest_report.get('insights', [])
            if insights:
                insights_text = "\n".join(f"• {insight}" for insight in insights[:3])
                if len(insights_text) > 1020:
                    insights_text = insights_text[:1017] + "..."
                embed.add_field(
                    name="💡 Key Insights",
                    value=insights_text,
                    inline=False
                )
        
        embed.set_footer(text="Real economic data • Integrated with stock market system")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error generating report: {str(e)}")


@tree.command(name="channel_restrict", description="Manage channel restrictions for bot commands (Admin only)")
@has_any_role(config.Roles.ADMIN)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to manage channel restrictions")
async def channel_restrict(
    interaction: discord.Interaction,
    action: Literal["set", "remove", "list"],
    command_name: str = None,
    mode: Literal["whitelist", "blacklist"] = None,
    channels: str = None
):
    """Manage channel restrictions for bot commands.
    
    Args:
        action: set (add restriction), remove (remove restriction), list (show all)
        command_name: Name of command to restrict (e.g., 'helper', 'stocks_buy')
        mode: 'whitelist' (only allow in specified channels) or 'blacklist' (block from specified channels)
        channels: Comma-separated list of channel names or IDs
    """
    await interaction.response.defer()
    
    try:
        if action == "list":
            # Show all current restrictions
            restrictions = file_utils.get_command_restrictions()
            
            embed = discord.Embed(
                title="🔒 Channel Restrictions",
                description="Current command channel restrictions",
                color=0x0099ff,
                timestamp=datetime.now(timezone.utc)
            )
            
            if not restrictions:
                embed.add_field(
                    name="No Restrictions",
                    value="No commands currently have channel restrictions.",
                    inline=False
                )
            else:
                for cmd, config in restrictions.items():
                    mode_emoji = "✅" if config['mode'] == 'whitelist' else "❌"
                    channels_list = ", ".join(str(ch) for ch in config['channels'])
                    embed.add_field(
                        name=f"{mode_emoji} {cmd}",
                        value=f"**{config['mode'].title()}**: {channels_list}",
                        inline=False
                    )
            
            # Get bot instance from interaction
            bot_instance = interaction.client
            available_commands = file_utils.get_available_commands(bot_instance)
            embed.add_field(
                name="📋 Available Commands",
                value=f"{len(available_commands)} commands available. Commands you can restrict: {', '.join(available_commands[:10])}{'...' if len(available_commands) > 10 else ''}",
                inline=False
            )
            
            embed.set_footer(text="Use '/channel_restrict set' to add restrictions")
            await interaction.followup.send(embed=embed)
            
        elif action == "set":
            if not command_name or not mode or not channels:
                await interaction.followup.send("❌ For 'set' action, you must provide command_name, mode, and channels")
                return
            
            # Validate command name
            bot_instance = interaction.client
            available_commands = file_utils.get_available_commands(bot_instance)
            if command_name not in available_commands:
                await interaction.followup.send(
                    f"❌ Unknown command '{command_name}'. {len(available_commands)} available commands. Use '/channel_restrict list' to see all commands."
                )
                return
            
            # Parse channel list
            channel_list = [ch.strip() for ch in channels.split(',')]
            
            # Validate channels exist in the guild
            valid_channels = []
            invalid_channels = []
            
            for channel_input in channel_list:
                # Try to find channel by ID or name
                found_channel = None
                
                # Check if it's a channel ID
                if channel_input.isdigit():
                    found_channel = interaction.guild.get_channel(int(channel_input))
                else:
                    # Search by name
                    found_channel = discord.utils.get(interaction.guild.channels, name=channel_input)
                
                if found_channel:
                    valid_channels.append(channel_input)
                else:
                    invalid_channels.append(channel_input)
            
            if invalid_channels:
                await interaction.followup.send(
                    f"⚠️ Warning: These channels were not found: {', '.join(invalid_channels)}\nContinuing with valid channels: {', '.join(valid_channels)}"
                )
            
            if not valid_channels:
                await interaction.followup.send("❌ No valid channels found. Please check channel names/IDs.")
                return
            
            # Set the restriction
            file_utils.set_command_channel_restriction(command_name, mode, valid_channels)
            
            mode_emoji = "✅" if mode == 'whitelist' else "❌"
            embed = discord.Embed(
                title="🔒 Channel Restriction Set",
                description=f"Successfully configured restriction for **{command_name}**",
                color=0x00ff00
            )
            embed.add_field(
                name=f"{mode_emoji} {mode.title()} Mode",
                value=f"Channels: {', '.join(valid_channels)}",
                inline=False
            )
            
            if mode == 'whitelist':
                embed.add_field(
                    name="ℹ️ Effect",
                    value=f"Command **{command_name}** can ONLY be used in the specified channels.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="ℹ️ Effect", 
                    value=f"Command **{command_name}** is BLOCKED from the specified channels.",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        elif action == "remove":
            if not command_name:
                await interaction.followup.send("❌ For 'remove' action, you must provide command_name")
                return
            
            success = file_utils.remove_command_channel_restriction(command_name)
            
            if success:
                embed = discord.Embed(
                    title="🔓 Channel Restriction Removed",
                    description=f"Successfully removed channel restriction for **{command_name}**",
                    color=0x00ff00
                )
                embed.add_field(
                    name="ℹ️ Effect",
                    value=f"Command **{command_name}** can now be used in all allowed channels (subject to existing role/channel permissions).",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"⚠️ No channel restriction found for command '{command_name}'")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error managing channel restrictions: {str(e)}")


@tree.command(name="sync_commands", description="Force sync Discord slash commands (Admin only)")
@has_any_role(config.Roles.ADMIN)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to sync commands")
async def sync_commands(
    interaction: discord.Interaction,
    action: Literal["clear", "sync", "both"] = "both"
):
    """Force sync Discord slash commands to remove old commands and add current ones.
    
    Args:
        action: 'clear' (remove all), 'sync' (add current), 'both' (clear then sync)
    """
    await interaction.response.defer()
    
    try:
        results = []
        
        if action in ["clear", "both"]:
            # Clear existing commands
            if config.GUILD_ID:
                guild = discord.Object(id=config.GUILD_ID)
                tree.clear_commands(guild=guild)
                cleared_guild = await tree.sync(guild=guild)
                results.append(f"✅ Cleared guild commands. {len(cleared_guild)} commands remain")
                
                # Also clear global commands
                tree.clear_commands(guild=None)
                cleared_global = await tree.sync(guild=None)
                results.append(f"✅ Cleared global commands. {len(cleared_global)} commands remain")
            else:
                # Clear global commands only
                tree.clear_commands(guild=None)
                cleared = await tree.sync(guild=None)
                results.append(f"✅ Cleared global commands. {len(cleared)} commands remain")
        
        if action in ["sync", "both"]:
            # Re-register current commands and sync
            if config.GUILD_ID:
                guild = discord.Object(id=config.GUILD_ID)
                tree.copy_global_to(guild=guild)
                synced = await tree.sync(guild=guild)
                results.append(f"✅ Synced {len(synced)} commands to guild")
            else:
                synced = await tree.sync()
                results.append(f"✅ Synced {len(synced)} global commands")
        
        embed = discord.Embed(
            title="🔄 Command Sync Complete",
            description="\n".join(results),
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="ℹ️ Note",
            value="Discord may take a few minutes to fully update command lists. Try typing `/` to see the updated commands.",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error syncing commands: {str(e)}")


# Message Handlers (replacing complex MessageRouter)

# AIDEV-NOTE: Message router - handles 4 special channels with different logic
async def handle_message(message: discord.Message):
    """Handle incoming messages."""
    if message.author.bot:
        return
    
    # Clerk channel - bill reference processing
    if message.channel.id == config.CLERK_CHANNEL:
        await handle_clerk_message(message)
    
    # News channel - append to news file
    elif message.channel.id == config.NEWS_CHANNEL:
        await handle_news_message(message)
    
    # Sign channel - process Google Docs
    elif message.channel.id == config.SIGN_CHANNEL and "docs.google.com" in message.content:
        await handle_sign_message(message)
    
    # Bills-signed-into-law channel - automatically process Google Docs
    elif message.channel.id == config.BILLS_SIGNED_INTO_LAW_CHANNEL and "docs.google.com" in message.content:
        await handle_bills_signed_into_law_message(message)

async def handle_clerk_message(message: discord.Message):
    """Process clerk channel messages for bill references."""
    print(f"Processing clerk message from {message.author}")
    
    try:
        # Detect bill reference
        ref_update = bill_utils.detect_bill_reference(message.content)
        
        if ref_update['success']:
            # Update reference number
            updated_num = file_utils.get_next_reference(ref_update['bill_type'])
            print(f"Updated {ref_update['bill_type'].upper()} to {updated_num}")
            
    except Exception as e:
        print(f"Failed to process clerk message: {e}")

async def handle_news_message(message: discord.Message):
    """Append news messages to news file."""
    print(f"Appending news message to {config.NEWS_FILE}")
    
    try:
        await file_utils.append_file(str(config.NEWS_FILE), message.content + "\n")
    except Exception as e:
        print(f"Failed to append to news file: {e}")

async def handle_sign_message(message: discord.Message):
    """Handle bill signing with Google Docs links."""
    print(f"Processing bill signing from {message.author}")
    
    # Notify records channel
    records_channel = discord_channels.get('records')
    if records_channel:
        await records_channel.send(f'<@&1269061253964238919>, a new bill has been signed! {message.jump_url}')
    
    # Extract Google Doc link
    match = re.search(r"https?://docs\.google\.com/\S+", message.content)
    if match:
        doc_link = match.group(0)
        print(f"Found Google Doc link: {doc_link}")
        
        try:
            result = await bill_utils.add_bill_to_corpus(doc_link)
            if result['success']:
                print("Bill successfully added to database.")
            else:
                print(f"Failed to add bill: {result['error']}")
                if records_channel:
                    await records_channel.send(f"Error adding bill to database: {result['error']}")
        except Exception as e:
            print(f"Error adding bill: {e}")
            if records_channel:
                await records_channel.send("Unexpected error adding bill. Please check logs.")

# AIDEV-NOTE: Auto bill processor - extracts Google Docs, generates AI titles, adds callbacks
async def handle_bills_signed_into_law_message(message: discord.Message):
    """Handle automatic bill processing from bills-signed-into-law channel with callbacks."""
    print(f"Processing bills-signed-into-law message from {message.author}")
    
    # Extract all Google Doc links from the message
    doc_links = re.findall(r"https?://docs\.google\.com/\S+", message.content)
    
    if not doc_links:
        print("No Google Docs links found in message")
        return
    
    # Get records channel for notifications
    records_channel = discord_channels.get('records')
    
    # Process each doc link
    for doc_link in doc_links:
        print(f"Found Google Doc link: {doc_link}")
        
        try:
            # Add bill to corpus with AI-generated title
            result = await bill_utils.add_bill_to_corpus(doc_link)
            
            if result['success']:
                print(f"Bill successfully added to database: {result['title']}")
                
                # Send confirmation in the same channel with callback
                embed = discord.Embed(
                    title="✅ Bill Added to Database",
                    description=f"Successfully processed bill from {message.author.mention}",
                    color=0x00ff00
                )
                embed.add_field(name="Title", value=result['title'], inline=False)
                embed.add_field(name="Filename", value=result['filename'], inline=True)
                embed.add_field(name="Source", value=f"[Google Doc]({doc_link})", inline=True)
                embed.set_footer(text="Title generated by AI • Added to searchable corpus")
                
                # Add callback button for immediate search
                view = BillCallbackView(result['filename'], result['title'])
                await message.channel.send(embed=embed, view=view)
                
                # Notify records channel
                if records_channel:
                    await records_channel.send(
                        f"📋 New bill automatically added from bills-signed-into-law channel!\n"
                        f"**{result['title']}** by {message.author.mention}\n"
                        f"Source: {message.jump_url}"
                    )
                    
            else:
                print(f"Failed to add bill: {result['error']}")
                
                # Send error message with callback for retry
                embed = discord.Embed(
                    title="❌ Error Adding Bill",
                    description=f"Failed to process bill from {message.author.mention}",
                    color=0xff0000
                )
                embed.add_field(name="Error", value=result['error'], inline=False)
                embed.add_field(name="Source", value=f"[Google Doc]({doc_link})", inline=False)
                
                view = RetryBillView(doc_link, message.author.id)
                await message.channel.send(embed=embed, view=view)
                
                # Notify records channel of error
                if records_channel:
                    await records_channel.send(
                        f"⚠️ Error adding bill from bills-signed-into-law channel: {result['error']}\n"
                        f"Source: {message.jump_url}"
                    )
                    
        except Exception as e:
            print(f"Unexpected error processing bill: {e}")
            
            # Send generic error message
            embed = discord.Embed(
                title="❌ Unexpected Error",
                description=f"An unexpected error occurred while processing bill from {message.author.mention}",
                color=0xff0000
            )
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.add_field(name="Source", value=f"[Google Doc]({doc_link})", inline=False)
            
            await message.channel.send(embed=embed)
            
            # Notify records channel
            if records_channel:
                await records_channel.send(
                    f"❌ Unexpected error processing bill from bills-signed-into-law channel: {str(e)}\n"
                    f"Source: {message.jump_url}"
                )

# Callback views for bill processing
class BillCallbackView(discord.ui.View):
    """Interactive view for bill processing callbacks."""
    
    def __init__(self, filename: str, title: str):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.filename = filename
        self.title = title
    
    @discord.ui.button(label="🔍 Search Bill", style=discord.ButtonStyle.primary)
    async def search_bill(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Quick search for this bill."""
        await interaction.response.defer()
        
        try:
            # Search for the bill
            results = bill_utils.search_bills_keyword(self.filename, 1)
            
            if results:
                result = results[0]
                embed = discord.Embed(
                    title="📋 Bill Found",
                    description=f"**{result['title']}**",
                    color=0x0099ff
                )
                embed.add_field(name="Filename", value=result['filename'], inline=True)
                embed.add_field(name="Match Type", value=result['match_type'], inline=True)
                embed.add_field(name="Score", value=str(result['score']), inline=True)
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ Bill not found in search results.")
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error searching for bill: {str(e)}")
    
    @discord.ui.button(label="📄 View Content", style=discord.ButtonStyle.secondary)
    async def view_content(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View bill content preview."""
        await interaction.response.defer()
        
        try:
            from file_utils import get_bill_content
            content = get_bill_content(self.filename)
            
            if content:
                # Truncate content for display
                preview = content[:1000] + "..." if len(content) > 1000 else content
                
                embed = discord.Embed(
                    title="📄 Bill Content Preview",
                    description=f"**{self.title}**",
                    color=0x0099ff
                )
                embed.add_field(name="Content", value=f"```{preview}```", inline=False)
                embed.set_footer(text=f"Showing first 1000 characters • Full file: {self.filename}.txt")
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ Bill content not found.")
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error retrieving bill content: {str(e)}")

class RetryBillView(discord.ui.View):
    """View for retrying failed bill processing."""
    
    def __init__(self, doc_link: str, user_id: int):
        super().__init__(timeout=600)  # 10 minutes timeout
        self.doc_link = doc_link
        self.user_id = user_id
    
    @discord.ui.button(label="🔄 Retry", style=discord.ButtonStyle.primary)
    async def retry_bill(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Retry processing the bill."""
        # Only allow the original user to retry
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the original user can retry this operation.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            result = await bill_utils.add_bill_to_corpus(self.doc_link)
            
            if result['success']:
                embed = discord.Embed(
                    title="✅ Retry Successful",
                    description="Bill successfully added to database",
                    color=0x00ff00
                )
                embed.add_field(name="Title", value=result['title'], inline=False)
                embed.add_field(name="Filename", value=result['filename'], inline=True)
                embed.set_footer(text="Title generated by AI • Added to searchable corpus")
                
                # Disable the retry button
                self.retry_bill.disabled = True
                await interaction.edit_original_response(view=self)
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ Retry failed: {result['error']}")
                
        except Exception as e:
            await interaction.followup.send(f"❌ Retry failed with error: {str(e)}")

# GitHub commit monitoring
async def check_github_commits():
    """Monitor GitHub for new commits."""
    await client.wait_until_ready()
    channel = client.get_channel(config.BOT_HELPER_CHANNEL)
    
    try:
        with open("last_commit.txt", "r") as f:
            last_commit_sha = f.read().strip()
    except FileNotFoundError:
        last_commit_sha = ""
    
    repo = "willow-wynn/VCBot-Simplified"
    github_api_url = f"https://api.github.com/repos/{repo}/commits"
    github_url = "https://github.com/willow-wynn/VCBot-Simplified"
    
    async with aiohttp.ClientSession() as session:
        while not client.is_closed():
            try:
                async with session.get(github_api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        latest_commit = data[0]
                        sha = latest_commit['sha']
                        
                        with open("last_commit.txt", "w") as f:
                            f.write(sha)
                        
                        if sha != last_commit_sha:
                            commit_msg = latest_commit['commit']['message']
                            commit_msg = message_utils.sanitize_text(commit_msg)
                            author = latest_commit['commit']['author']['name']
                            await channel.send(f"New commit to {repo}:\n**{commit_msg}** by {author}. \nSee it [here]({github_url}/commit/{sha})")
                            last_commit_sha = sha
                            
            except Exception as e:
                print(f"GitHub check failed: {e}")
            
            await asyncio.sleep(60)  # Check every minute

# Discord Events

# AIDEV-NOTE: Smart sync - prevents rate limiting by only syncing on changes
async def smart_sync_commands():
    """Smart command sync that only syncs when there are actual changes."""
    print("🔍 Checking if command sync is needed...")
    
    try:
        # Determine if we're syncing to a guild or globally
        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            # Fetch existing commands from Discord
            print(f"Fetching existing commands from guild {config.GUILD_ID}...")
            try:
                existing_commands = await tree.fetch_commands(guild=guild)
            except discord.errors.Forbidden:
                print("❌ No permission to fetch commands from guild - assuming no commands exist")
                existing_commands = []
            
            # Copy global commands to guild (this doesn't sync, just prepares)
            tree.copy_global_to(guild=guild)
            
            # Get local commands that would be synced
            local_commands = tree.get_commands(guild=guild)
        else:
            # Global sync
            print("Fetching existing global commands...")
            existing_commands = await tree.fetch_commands(guild=None)
            local_commands = tree.get_commands(guild=None)
        
        # Compare command names only - sync only on add/remove
        existing_names = {cmd.name for cmd in existing_commands}
        local_names = {cmd.name for cmd in local_commands}
        
        # Find differences
        added_commands = local_names - existing_names
        removed_commands = existing_names - local_names
        
        # Determine if sync is needed (only for add/remove)
        sync_needed = bool(added_commands or removed_commands)
        
        # Log the comparison results
        print(f"📊 Command comparison results:")
        print(f"   Existing commands on Discord: {len(existing_commands)}")
        print(f"   Local commands in tree: {len(local_commands)}")
        
        if added_commands:
            print(f"   ➕ New commands to add: {', '.join(sorted(added_commands))}")
        if removed_commands:
            print(f"   ➖ Commands to remove: {', '.join(sorted(removed_commands))}")
        if not added_commands and not removed_commands:
            print(f"   ✅ All commands match - no changes detected")
        
        if not sync_needed:
            print("✅ Commands are already in sync - no sync needed!")
            return False
        
        # Sync is needed
        print("🔄 Syncing commands due to detected changes...")
        
        if config.GUILD_ID:
            synced_commands = await tree.sync(guild=guild)
            print(f"✅ Successfully synced {len(synced_commands)} commands to guild {config.GUILD_ID}")
        else:
            synced_commands = await tree.sync()
            print(f"✅ Successfully synced {len(synced_commands)} commands globally")
        
        # Log synced commands
        if synced_commands:
            print("Synced commands:")
            for cmd in synced_commands:
                print(f"  - {cmd.name}: {cmd.description}")
        
        return True
        
    except discord.errors.HTTPException as e:
        if e.status == 429:  # Rate limited
            print(f"⚠️ Rate limited when trying to sync commands!")
            print(f"Error details: {e}")
            print("⏳ Commands not synced - try again later")
            return False
        else:
            print(f"❌ HTTP error during command sync: {e}")
            raise
    except Exception as e:
        print(f"❌ Error during smart sync: {e}")
        import traceback
        traceback.print_exc()
        raise

# AIDEV-NOTE: Critical startup - data migration, channel init, stock market, econ engine
@client.event
async def on_ready():
    """Bot startup initialization."""
    print(f"Logged in as {client.user}")
    
    # Initialize guild-specific data structure
    from file_utils import migrate_data_to_guild_directory, initialize_guild_data_structure
    from config import ensure_guild_directories, DATA_DIR, GUILD_ID
    
    # Ensure guild directories exist
    ensure_guild_directories()
    
    # AIDEV-NOTE: Guild-specific data migration - handles prod vs test environments
    # For production guild, migrate existing data if needed
    if GUILD_ID == 654458344781774879 and not (DATA_DIR / "bill_refs.json").exists():
        print("Migrating existing data to guild-specific directory...")
        migrate_data_to_guild_directory()
    elif not (DATA_DIR / "bill_refs.json").exists():
        print("Initializing new guild data structure...")
        initialize_guild_data_structure()
    
    # Initialize channels
    discord_channels['records'] = client.get_channel(config.RECORDS_CHANNEL)
    discord_channels['news'] = client.get_channel(config.NEWS_CHANNEL)
    discord_channels['sign'] = client.get_channel(config.SIGN_CHANNEL)
    discord_channels['clerk'] = client.get_channel(config.CLERK_CHANNEL)
    discord_channels['bills_signed_into_law'] = client.get_channel(config.BILLS_SIGNED_INTO_LAW_CHANNEL)
    
    # Log channel status
    for name, channel in discord_channels.items():
        if channel:
            print(f"{name.title()} Channel: {channel.id}: {channel.name}")
        else:
            print(f"{name.title()} Channel: Not Found")
    
    # Start GitHub monitoring
    client.loop.create_task(check_github_commits())
    
    # Start economic analysis system
    economic_utils.start_economic_engine(client)
    print("Economic analysis system initialized")
    
    # Initialize stock market system with scheduler
    if stock_market:
        try:
            # Initialize the complete stock market system with scheduler
            await stock_market.initialize_stock_market(client)
            print("📈 Stock market system initialized with automatic hourly updates")
        except Exception as e:
            print(f"⚠️ Stock market system error: {e}")
    
    # Smart command sync
    print("📋 Checking command sync status...")
    print(f"Total commands in tree: {len(tree.get_commands())}")
    
    # Debug: Print all commands in tree
    print("Commands registered in tree:")
    for cmd in tree.get_commands():
        print(f"  - {cmd.name} ({cmd.description[:50]}...)")
    
    # Use smart sync to only sync when needed
    try:
        sync_performed = await smart_sync_commands()
        if sync_performed:
            print("🎉 Command sync completed successfully!")
        else:
            print("📋 Commands already up to date - sync was not needed")
    except Exception as e:
        print(f"❌ Command sync failed: {e}")
        print("⚠️ Bot will continue running but slash commands may not be available")

@client.event
async def on_message(message):
    """Handle incoming messages."""
    try:
        await handle_message(message)
    except Exception as e:
        print(f"Error in message handler: {e}")

def main():
    """Main entry point."""
    print("Starting VCBot...")
    print(f"Commands in tree before running: {len(tree.get_commands())}")
    for cmd in tree.get_commands():
        print(f"  - {cmd.name}")
    client.run(config.DISCORD_TOKEN)

if __name__ == "__main__":
    main()