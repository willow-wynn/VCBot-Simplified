"""
Economic Admin Hub Commands
Provides consolidated economic management interface with interactive buttons
"""

import discord
from discord import app_commands
from datetime import datetime, timezone
from functools import wraps
import economic_utils
from config import Roles, BOT_HELPER_CHANNEL

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

class EconAdminView(discord.ui.View):
    """Interactive view for economic admin hub"""
    
    def __init__(self, user: discord.User, client: discord.Client):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user = user
        self.client = client
        
    @discord.ui.button(label="📊 View Status", style=discord.ButtonStyle.primary, row=0)
    async def view_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            status = economic_utils.get_economic_status()
            
            if "error" in status:
                await interaction.followup.send(f"❌ Error: {status['error']}")
                return
            
            embed = discord.Embed(
                title="⚙️ Economic System Status",
                color=0x0099ff,
                timestamp=datetime.now(timezone.utc)
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
                value=f"Inflation: {params.get('inflation_base', 8.51):.2f}%\nInterval: {params.get('analysis_interval', 3600)//60} min",
                inline=True
            )
            
            # System Status
            embed.add_field(
                name="🔧 System Status",
                value=f"Data Files: {status.get('data_files_count', 0)}/{status.get('total_files', 5)}\nStock Market: Integrated",
                inline=True
            )
            
            # Latest Report
            latest = status.get("latest_report")
            if latest:
                embed.add_field(
                    name="📅 Latest Report",
                    value=f"Time: {latest.get('timestamp', 'Unknown')[:16]}\nGDP: ${latest.get('gdp', {}).get('value', 0):,.0f}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error getting status: {str(e)}")
            
    @discord.ui.button(label="📈 Set Inflation", style=discord.ButtonStyle.secondary, row=0)
    async def set_inflation(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        modal = InflationModal()
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="⏰ Set Interval", style=discord.ButtonStyle.secondary, row=0)
    async def set_interval(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        modal = IntervalModal()
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🔄 Fetch Data Now", style=discord.ButtonStyle.success, row=1)
    async def fetch_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            # Get existing data status
            latest_report = economic_utils.econ_data.get_latest_economic_report()
            
            if latest_report is None:
                status_msg = "🔍 No existing economic data found. Starting comprehensive AI analysis..."
            else:
                status_msg = "📊 Updating economic data with comprehensive AI analysis..."
            
            await interaction.followup.send(status_msg)
            
            # Trigger analysis
            analysis = await economic_utils.fetch_econ_data_manually(self.client, None, interaction.channel)
            
            # Create response embed
            embed = discord.Embed(
                title="📈 Economic Analysis Complete",
                color=0x00ff00,
                timestamp=datetime.now(timezone.utc)
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
            
            await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Analysis failed: {str(e)}")
            
    @discord.ui.button(label="🧠 Manage Memory", style=discord.ButtonStyle.primary, row=1)
    async def manage_memory(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="🧠 Economic Memory Management",
            description="Use these commands to manage memory entries:",
            color=0x0099ff
        )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "`/econ_memory_list` - View all memory entries\n"
                "`/econ_memory add [content]` - Add new entry\n"
                "`/econ_memory remove [id]` - Remove entry by ID\n"
                "\nMemory entries help guide economic analysis with persistent context."
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @discord.ui.button(label="📊 Generate Report", style=discord.ButtonStyle.success, row=1)
    async def generate_report(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            # Get fresh economic data
            latest_report = economic_utils.econ_data.get_fresh_economic_report()
            
            if not latest_report:
                await interaction.followup.send("❌ No economic data available. Run 'Fetch Data Now' first.")
                return
            
            # Also get stock market data
            try:
                import stock_market
                stock_data = stock_market.get_stock_market()
            except:
                stock_data = None
            
            # Determine report color based on inflation
            inflation_rate = latest_report.get('inflation', {}).get('rate', 0)
            if inflation_rate > 6:
                report_color = 0xff6b6b  # Red
                severity = "High Inflation Crisis"
            elif inflation_rate > 4:
                report_color = 0xffaa00  # Orange
                severity = "Elevated Inflation Environment"
            else:
                report_color = 0x0099ff  # Blue
                severity = "Economic Analysis"
            
            embed = discord.Embed(
                title="📊 Economic Report",
                description=f"**{severity}**",
                color=report_color,
                timestamp=datetime.now(timezone.utc)
            )
            
            # GDP Section
            gdp = latest_report.get('gdp', {})
            gdp_value = gdp.get('value', 26.8)
            gdp_change = gdp.get('change_percent', -1.2)
            gdp_color = "📉" if gdp_change < 0 else "📈"
            embed.add_field(
                name="🏛️ GDP",
                value=f"**${gdp_value:,.1f}T** {gdp_color}\nChange: {gdp_change:+.1f}%",
                inline=True
            )
            
            # Inflation section
            inflation = latest_report.get('inflation', {})
            embed.add_field(
                name="🔥 Inflation",
                value=f"**{inflation_rate:.2f}%** YoY\nFed Rate: {inflation.get('federal_funds_rate', 0):.2f}%",
                inline=True
            )
            
            # Market Sentiment
            sentiment = latest_report.get('sentiment', {})
            confidence = sentiment.get('market_confidence', 0)
            embed.add_field(
                name="😟 Market Sentiment",
                value=f"Confidence: {confidence}%\nInflation Anxiety: {sentiment.get('inflation_anxiety', 0)}%",
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating report: {str(e)}")

class InflationModal(discord.ui.Modal, title="Set Inflation Rate"):
    rate = discord.ui.TextInput(
        label="Inflation Rate (%)",
        placeholder="Enter inflation rate (e.g., 8.51)",
        required=True,
        max_length=10
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            rate_value = float(self.rate.value)
            rate_value = max(-10.0, min(50.0, rate_value))  # Clamp to bounds
            
            success = economic_utils.set_economic_parameter("inflation_base", rate_value)
            
            if success:
                economic_utils.log_admin_action(interaction.user.id, "set_inflation", {"rate": rate_value})
                
                embed = discord.Embed(
                    title="✅ Inflation Rate Updated",
                    description=f"Base inflation rate set to {rate_value:.2f}%",
                    color=0x00ff00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to update inflation rate", ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message("❌ Invalid rate. Please enter a number.", ephemeral=True)

class IntervalModal(discord.ui.Modal, title="Set Analysis Interval"):
    minutes = discord.ui.TextInput(
        label="Interval (minutes)",
        placeholder="Enter interval in minutes (e.g., 60)",
        required=True,
        max_length=10
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            minutes_value = int(self.minutes.value)
            seconds = max(300, min(86400, minutes_value * 60))  # Clamp 5 min to 24 hours
            
            success = economic_utils.set_economic_parameter("analysis_interval", seconds)
            
            if success:
                economic_utils.log_admin_action(interaction.user.id, "set_analysis_interval", {"minutes": minutes_value})
                
                embed = discord.Embed(
                    title="⏰ Analysis Interval Updated",
                    description=f"Economic analysis will now run every {seconds//60} minutes",
                    color=0x00ff00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to update interval", ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message("❌ Invalid interval. Please enter a number.", ephemeral=True)

# Hub Command

@app_commands.command(name="econ_admin", description="Economic admin hub - management controls")
@has_any_role(Roles.ADMIN)
@handle_errors("Failed to display economic admin hub")
async def econ_admin(interaction: discord.Interaction):
    """Economic admin hub with management controls"""
    embed = discord.Embed(
        title="⚙️ Economic Admin Hub",
        description="Administrative controls for economic system management",
        color=0xff6b6b,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Get current status
    try:
        status = economic_utils.get_economic_status()
        params = status.get("parameters", {})
        
        status_text = f"**Current Settings:**\n"
        status_text += f"Inflation Base: {params.get('inflation_base', 8.51):.2f}%\n"
        status_text += f"Analysis Interval: {params.get('analysis_interval', 3600)//60} minutes\n"
        
        latest = status.get("latest_report")
        if latest:
            status_text += f"\n**Latest Report:** {latest.get('timestamp', 'Unknown')[:16]}"
        else:
            status_text += f"\n**Latest Report:** No data available"
            
        embed.add_field(name="📊 System Status", value=status_text, inline=False)
    except:
        embed.add_field(name="📊 System Status", value="Unable to fetch status", inline=False)
    
    # Control descriptions
    controls = (
        "• **View Status** - Detailed system parameters\n"
        "• **Set Inflation** - Adjust base inflation rate\n"
        "• **Set Interval** - Change analysis frequency\n"
        "• **Fetch Data Now** - Trigger immediate analysis\n"
        "• **Manage Memory** - Add/remove memory entries\n"
        "• **Generate Report** - Create current economic report"
    )
    embed.add_field(name="🛠️ Admin Controls", value=controls, inline=False)
    
    embed.set_footer(text="⚠️ Admin controls affect economic analysis")
    
    # Pass the client instance to the view
    view = EconAdminView(interaction.user, interaction.client)
    await interaction.response.send_message(embed=embed, view=view)