"""
Economic System Integration for bot.py
This file contains the commands and integration code to add to bot.py
"""

import discord
from discord import app_commands
from typing import Literal
import economic_utils
import message_utils
import config

# Add these imports to the top of bot.py:
# import economic_utils

# Add this command to bot.py after the existing commands:

@tree.command(name="fetch_econ_data", description="Trigger comprehensive economic data collection and analysis")
@has_any_role(config.Roles.ADMIN, config.Roles.AI_ACCESS)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to fetch economic data")
async def fetch_econ_data(interaction: discord.Interaction):
    """Manually trigger economic data collection"""
    await interaction.response.defer()
    
    try:
        # Get existing data status
        latest_report = economic_utils.econ_data.get_latest_economic_report()
        
        if latest_report is None:
            await interaction.followup.send("🔍 No existing economic data found. Analyzing last 30 days of server activity...")
        else:
            await interaction.followup.send("📊 Found existing economic data. Analyzing recent activity for updated report...")
        
        # Trigger analysis
        analysis = await economic_utils.fetch_econ_data_manually(client)
        
        if analysis:
            # Create response embed
            embed = discord.Embed(
                title="📈 Economic Analysis Complete",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(
                name="GDP",
                value=f"${analysis['gdp']['value']:,.2f} ({analysis['gdp']['change_percent']:+.2f}%)",
                inline=True
            )
            
            embed.add_field(
                name="Inflation",
                value=f"{analysis['inflation']['rate']:.2f}% ({analysis['inflation']['trend']})",
                inline=True
            )
            
            embed.add_field(
                name="Market Sentiment",
                value=f"{analysis['sentiment']['market_confidence']}/100",
                inline=True
            )
            
            if analysis.get('insights'):
                embed.add_field(
                    name="Key Insights",
                    value="\n".join(f"• {insight}" for insight in analysis['insights'][:3]),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Economic analysis failed. Check logs for details.")
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error during economic analysis: {str(e)}")

@tree.command(name="econ_report", description="Generate current economic overview")
@has_any_role(config.Roles.ADMIN, config.Roles.AI_ACCESS)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to generate economic report")
async def econ_report(interaction: discord.Interaction):
    """Generate current economic overview"""
    await interaction.response.defer()
    
    try:
        latest_report = economic_utils.econ_data.get_latest_economic_report()
        
        if not latest_report:
            await interaction.followup.send("❌ No economic data available. Run `/fetch_econ_data` first.")
            return
        
        embed = discord.Embed(
            title="📊 Virtual Congress Economic Report",
            color=0x0099ff,
            timestamp=discord.utils.utcnow()
        )
        
        # GDP Section
        gdp = latest_report.get('gdp', {})
        embed.add_field(
            name="🏛️ GDP",
            value=f"**${gdp.get('value', 0):,.2f}**\nChange: {gdp.get('change_percent', 0):+.2f}%",
            inline=True
        )
        
        # Stocks Section
        stocks = latest_report.get('stocks', [])
        if stocks:
            stock_text = "\n".join([
                f"**{stock['symbol']}**: ${stock['price']:.2f} ({stock.get('change_percent', 0):+.2f}%)"
                for stock in stocks[:3]
            ])
            embed.add_field(name="📈 Stock Market", value=stock_text, inline=True)
        
        # Inflation
        inflation = latest_report.get('inflation', {})
        embed.add_field(
            name="💰 Inflation",
            value=f"**{inflation.get('rate', 0):.2f}%**\nTrend: {inflation.get('trend', 'stable').title()}",
            inline=True
        )
        
        # Sentiment
        sentiment = latest_report.get('sentiment', {})
        embed.add_field(
            name="🎭 Market Sentiment",
            value=f"Confidence: {sentiment.get('market_confidence', 0)}/100\nApproval: {sentiment.get('public_approval', 0)}/100",
            inline=True
        )
        
        # Unemployment
        unemployment = latest_report.get('unemployment', {})
        embed.add_field(
            name="👥 Unemployment",
            value=f"**{unemployment.get('rate', 0):.1f}%**",
            inline=True
        )
        
        # Activity Summary
        gdp_components = gdp.get('components', {})
        embed.add_field(
            name="📋 Government Activity",
            value=f"Legislative: {gdp_components.get('legislative', 0)}\nCommittee: {gdp_components.get('committee', 0)}\nPublic: {gdp_components.get('public', 0)}",
            inline=True
        )
        
        # Insights
        insights = latest_report.get('insights', [])
        if insights:
            embed.add_field(
                name="💡 Key Insights",
                value="\n".join(f"• {insight}" for insight in insights[:3]),
                inline=False
            )
        
        embed.set_footer(text=f"Data from: {latest_report.get('timestamp', 'Unknown')[:10]}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error generating report: {str(e)}")

@tree.command(name="econ_status", description="View economic system status and parameters")
@has_any_role(config.Roles.ADMIN)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to get economic status")
async def econ_status(interaction: discord.Interaction):
    """Show economic system status"""
    await interaction.response.defer()
    
    try:
        status = economic_utils.get_economic_status()
        
        if "error" in status:
            await interaction.followup.send(f"❌ Error: {status['error']}")
            return
        
        embed = discord.Embed(
            title="⚙️ Economic System Status",
            color=0x0099ff,
            timestamp=discord.utils.utcnow()
        )
        
        params = status.get("parameters", {})
        
        # GDP Settings
        gdp_weights = params.get("gdp_weights", {})
        embed.add_field(
            name="📊 GDP Weights",
            value=f"Legislative: {gdp_weights.get('legislative', 0.4):.2f}\nCommittee: {gdp_weights.get('committee', 0.3):.2f}\nPublic: {gdp_weights.get('public', 0.3):.2f}",
            inline=True
        )
        
        # Market Settings  
        embed.add_field(
            name="📈 Market Settings",
            value=f"Inflation: {params.get('inflation_base', 2.5):.2f}%\nInterval: {params.get('analysis_interval', 3600)//60} min",
            inline=True
        )
        
        # System Status
        embed.add_field(
            name="🔧 System Status",
            value=f"Data Files: {status.get('data_files_count', 0)}/{status.get('total_files', 5)}\nStocks: {len(params.get('tracked_stocks', []))} tracked",
            inline=True
        )
        
        # Latest Report
        latest = status.get("latest_report")
        if latest:
            embed.add_field(
                name="📅 Latest Report",
                value=f"Timestamp: {latest.get('timestamp', 'Unknown')[:16]}\nGDP: ${latest.get('gdp', {}).get('value', 0):,.0f}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error getting status: {str(e)}")

@tree.command(name="econ_set_inflation", description="Set base inflation rate (Admin only)")
@has_any_role(config.Roles.ADMIN)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to set inflation rate")
async def econ_set_inflation(interaction: discord.Interaction, rate: float):
    """Set inflation rate"""
    await interaction.response.defer()
    
    try:
        # Clamp to reasonable bounds
        rate = max(-10.0, min(50.0, rate))
        
        success = economic_utils.set_economic_parameter("inflation_base", rate)
        
        if success:
            economic_utils.log_admin_action(interaction.user.id, "set_inflation", {"rate": rate})
            
            embed = discord.Embed(
                title="✅ Inflation Rate Updated",
                description=f"Base inflation rate set to {rate:.2f}%",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Failed to update inflation rate")
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error setting inflation: {str(e)}")

@tree.command(name="econ_set_interval", description="Set analysis interval in minutes (Admin only)")
@has_any_role(config.Roles.ADMIN)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to set analysis interval")
async def econ_set_interval(interaction: discord.Interaction, minutes: int):
    """Set analysis interval"""
    await interaction.response.defer()
    
    try:
        # Convert to seconds and clamp (5 minutes to 24 hours)
        seconds = max(300, min(86400, minutes * 60))
        
        success = economic_utils.set_economic_parameter("analysis_interval", seconds)
        
        if success:
            economic_utils.log_admin_action(interaction.user.id, "set_analysis_interval", {"minutes": minutes})
            
            embed = discord.Embed(
                title="⏰ Analysis Interval Updated",
                description=f"Economic analysis will now run every {seconds//60} minutes",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Failed to update analysis interval")
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error setting interval: {str(e)}")

# Add this to the on_ready() function in bot.py:
def start_economic_system():
    """Start the economic analysis system"""
    economic_utils.start_economic_engine(client)
    print("Economic analysis system initialized")

# Modify the on_ready() function to include:
# start_economic_system()

"""
INTEGRATION INSTRUCTIONS:

1. Add this import to the top of bot.py:
   import economic_utils

2. Add all the command functions above to bot.py (after the existing commands)

3. In the on_ready() function, add this line before the final print statement:
   economic_utils.start_economic_engine(client)

4. The economic system will then be fully integrated and ready to use.

Example integration in bot.py on_ready():

@client.event
async def on_ready():
    # ... existing code ...
    
    # Start economic analysis system
    economic_utils.start_economic_engine(client)
    
    # ... rest of existing code ...
"""