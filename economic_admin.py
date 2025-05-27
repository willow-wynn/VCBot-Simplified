"""
Economic Administration Commands for VCBot
Provides admin-only commands to control and steer the economic simulation
"""

import json
import discord
from discord.ext import commands
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
from config import Roles

class EconomicAdmin(commands.Cog):
    """Admin commands for controlling the economic simulation"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = Path("economic_data")
        self.data_dir.mkdir(exist_ok=True)
    
    def load_parameters(self) -> Dict[str, Any]:
        """Load current economic parameters"""
        params_file = self.data_dir / "parameters.json"
        if params_file.exists():
            with open(params_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_parameters(self, params: Dict[str, Any]) -> None:
        """Save economic parameters"""
        with open(self.data_dir / "parameters.json", 'w') as f:
            json.dump(params, f, indent=2)
    
    def log_admin_action(self, admin_id: int, action: str, details: Dict[str, Any]) -> None:
        """Log administrative actions for audit trail"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "admin_id": admin_id,
            "action": action,
            "details": details
        }
        
        log_file = self.data_dir / "admin_log.json"
        logs = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
        
        logs.append(log_entry)
        logs = logs[-1000:]  # Keep last 1000 entries
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    # GDP Control Commands
    @commands.slash_command(name="econ_set_gdp_weights", description="Set GDP calculation weights for different activity types")
    @commands.has_role(Roles.ADMIN)
    async def set_gdp_weights(
        self, 
        interaction: discord.Interaction,
        legislative: float = None,
        committee: float = None,
        public: float = None
    ):
        """Set GDP calculation weights"""
        params = self.load_parameters()
        
        if "gdp_weights" not in params:
            params["gdp_weights"] = {"legislative": 0.4, "committee": 0.3, "public": 0.3}
        
        changes = {}
        if legislative is not None:
            params["gdp_weights"]["legislative"] = max(0.0, min(1.0, legislative))
            changes["legislative"] = legislative
        
        if committee is not None:
            params["gdp_weights"]["committee"] = max(0.0, min(1.0, committee))
            changes["committee"] = committee
        
        if public is not None:
            params["gdp_weights"]["public"] = max(0.0, min(1.0, public))
            changes["public"] = public
        
        if not changes:
            embed = discord.Embed(
                title="📊 Current GDP Weights",
                color=0x0099ff
            )
            for category, weight in params["gdp_weights"].items():
                embed.add_field(name=category.title(), value=f"{weight:.2f}", inline=True)
            await interaction.response.send_message(embed=embed)
            return
        
        self.save_parameters(params)
        self.log_admin_action(interaction.user.id, "set_gdp_weights", changes)
        
        embed = discord.Embed(
            title="✅ GDP Weights Updated",
            description="Economic simulation parameters have been updated",
            color=0x00ff00
        )
        
        for category, value in changes.items():
            embed.add_field(name=category.title(), value=f"{value:.2f}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    # Inflation Control Commands
    @commands.slash_command(name="econ_set_inflation", description="Set base inflation rate for the economic simulation")
    @commands.has_role(Roles.ADMIN)
    async def set_inflation(self, interaction: discord.Interaction, rate: float):
        """Set inflation rate"""
        # Clamp inflation rate to reasonable bounds
        rate = max(-10.0, min(50.0, rate))
        
        params = self.load_parameters()
        old_rate = params.get("inflation_base", 2.5)
        params["inflation_base"] = rate
        
        self.save_parameters(params)
        self.log_admin_action(interaction.user.id, "set_inflation", {"old_rate": old_rate, "new_rate": rate})
        
        embed = discord.Embed(
            title="📈 Inflation Rate Updated",
            description=f"Base inflation rate changed from {old_rate:.2f}% to {rate:.2f}%",
            color=0x00ff00
        )
        
        await interaction.response.send_message(embed=embed)
    
    # Stock Market Control Commands
    @commands.slash_command(name="econ_set_stock", description="Modify stock price and volatility")
    @commands.has_role(Roles.ADMIN)
    async def set_stock(
        self, 
        interaction: discord.Interaction,
        symbol: str,
        price: float = None,
        volatility: float = None
    ):
        """Set stock parameters"""
        params = self.load_parameters()
        
        if "tracked_stocks" not in params:
            await interaction.response.send_message("❌ No stocks found in economic system")
            return
        
        # Find the stock
        stock_found = False
        changes = {}
        
        for stock in params["tracked_stocks"]:
            if stock["symbol"].upper() == symbol.upper():
                stock_found = True
                
                if price is not None:
                    old_price = stock["price"]
                    stock["price"] = max(0.01, price)
                    changes["price"] = {"old": old_price, "new": stock["price"]}
                
                if volatility is not None:
                    old_vol = stock["volatility"]
                    stock["volatility"] = max(0.001, min(1.0, volatility))
                    changes["volatility"] = {"old": old_vol, "new": stock["volatility"]}
                
                break
        
        if not stock_found:
            available_stocks = [stock["symbol"] for stock in params["tracked_stocks"]]
            await interaction.response.send_message(
                f"❌ Stock '{symbol}' not found. Available: {', '.join(available_stocks)}"
            )
            return
        
        if not changes:
            # Show current stock info
            for stock in params["tracked_stocks"]:
                if stock["symbol"].upper() == symbol.upper():
                    embed = discord.Embed(
                        title=f"📊 {stock['symbol']} - {stock['name']}",
                        color=0x0099ff
                    )
                    embed.add_field(name="Price", value=f"${stock['price']:.2f}", inline=True)
                    embed.add_field(name="Volatility", value=f"{stock['volatility']:.3f}", inline=True)
                    await interaction.response.send_message(embed=embed)
                    return
        
        self.save_parameters(params)
        self.log_admin_action(interaction.user.id, "set_stock", {"symbol": symbol, "changes": changes})
        
        embed = discord.Embed(
            title=f"✅ Stock {symbol.upper()} Updated",
            color=0x00ff00
        )
        
        for param, change in changes.items():
            embed.add_field(
                name=param.title(),
                value=f"{change['old']:.3f} → {change['new']:.3f}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    
    # Analysis Control Commands
    @commands.slash_command(name="econ_set_interval", description="Set economic analysis interval in seconds")
    @commands.has_role(Roles.ADMIN)
    async def set_analysis_interval(self, interaction: discord.Interaction, seconds: int):
        """Set analysis interval"""
        # Clamp to reasonable bounds (5 minutes to 24 hours)
        seconds = max(300, min(86400, seconds))
        
        params = self.load_parameters()
        old_interval = params.get("analysis_interval", 3600)
        params["analysis_interval"] = seconds
        
        self.save_parameters(params)
        self.log_admin_action(interaction.user.id, "set_analysis_interval", {"old": old_interval, "new": seconds})
        
        # Update the actual analysis loop interval
        econ_cog = self.bot.get_cog("EconomicEngine")
        if econ_cog:
            econ_cog.economic_analysis_loop.change_interval(seconds=seconds)
        
        embed = discord.Embed(
            title="⏰ Analysis Interval Updated",
            description=f"Economic analysis will now run every {seconds//60} minutes",
            color=0x00ff00
        )
        
        await interaction.response.send_message(embed=embed)
    
    # Economic Scenario Commands
    @commands.slash_command(name="econ_simulate", description="Run economic scenario simulation")
    @commands.has_role(Roles.ADMIN)
    async def simulate_scenario(
        self, 
        interaction: discord.Interaction,
        scenario: str = commands.Param(choices=["recession", "boom", "crisis", "recovery", "stagnation"])
    ):
        """Simulate economic scenarios"""
        await interaction.response.defer()
        
        params = self.load_parameters()
        scenario_effects = {
            "recession": {
                "gdp_multiplier": 0.85,
                "inflation_modifier": -1.0,
                "stock_volatility_multiplier": 1.5,
                "unemployment_modifier": 2.0
            },
            "boom": {
                "gdp_multiplier": 1.25,
                "inflation_modifier": 1.5,
                "stock_volatility_multiplier": 0.8,
                "unemployment_modifier": -1.5
            },
            "crisis": {
                "gdp_multiplier": 0.7,
                "inflation_modifier": -2.0,
                "stock_volatility_multiplier": 2.0,
                "unemployment_modifier": 3.0
            },
            "recovery": {
                "gdp_multiplier": 1.15,
                "inflation_modifier": 0.5,
                "stock_volatility_multiplier": 1.2,
                "unemployment_modifier": -1.0
            },
            "stagnation": {
                "gdp_multiplier": 0.98,
                "inflation_modifier": 0.0,
                "stock_volatility_multiplier": 0.9,
                "unemployment_modifier": 0.5
            }
        }
        
        effects = scenario_effects[scenario]
        
        # Apply temporary scenario effects
        backup_params = params.copy()
        
        # Modify stocks
        for stock in params.get("tracked_stocks", []):
            stock["volatility"] *= effects["stock_volatility_multiplier"]
            stock["price"] *= effects["gdp_multiplier"]  # Stocks follow GDP trend
        
        # Modify inflation
        params["inflation_base"] += effects["inflation_modifier"]
        
        # Save temporary parameters
        params["scenario_active"] = {
            "name": scenario,
            "effects": effects,
            "backup": backup_params,
            "activated_by": interaction.user.id,
            "activated_at": datetime.utcnow().isoformat()
        }
        
        self.save_parameters(params)
        self.log_admin_action(interaction.user.id, "simulate_scenario", {"scenario": scenario, "effects": effects})
        
        embed = discord.Embed(
            title=f"🎭 Economic Scenario: {scenario.title()}",
            description="Scenario has been applied to the economic simulation",
            color=0xff9900
        )
        
        embed.add_field(name="GDP Effect", value=f"{effects['gdp_multiplier']:.0%}", inline=True)
        embed.add_field(name="Inflation Change", value=f"{effects['inflation_modifier']:+.1f}%", inline=True)
        embed.add_field(name="Stock Volatility", value=f"{effects['stock_volatility_multiplier']:.0%}", inline=True)
        
        embed.add_field(
            name="Duration",
            value="Scenario will remain active until manually reset with `/econ_reset_scenario`",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
    
    @commands.slash_command(name="econ_reset_scenario", description="Reset active economic scenario")
    @commands.has_role(Roles.ADMIN)
    async def reset_scenario(self, interaction: discord.Interaction):
        """Reset economic scenario"""
        params = self.load_parameters()
        
        if "scenario_active" not in params:
            await interaction.response.send_message("❌ No active scenario to reset")
            return
        
        scenario_name = params["scenario_active"]["name"]
        backup_params = params["scenario_active"]["backup"]
        
        # Restore backup parameters
        for key, value in backup_params.items():
            params[key] = value
        
        # Remove scenario data
        del params["scenario_active"]
        
        self.save_parameters(params)
        self.log_admin_action(interaction.user.id, "reset_scenario", {"scenario": scenario_name})
        
        embed = discord.Embed(
            title="✅ Economic Scenario Reset",
            description=f"'{scenario_name.title()}' scenario has been deactivated and parameters restored",
            color=0x00ff00
        )
        
        await interaction.response.send_message(embed=embed)
    
    # System Reset Commands
    @commands.slash_command(name="econ_reset_all", description="Reset all economic parameters to defaults")
    @commands.has_role(Roles.ADMIN)
    async def reset_all_parameters(self, interaction: discord.Interaction):
        """Reset all economic parameters"""
        
        # Create confirmation view
        view = discord.ui.View(timeout=30)
        
        async def confirm_callback(confirm_interaction):
            default_params = {
                "gdp_weights": {"legislative": 0.4, "committee": 0.3, "public": 0.3},
                "inflation_base": 2.5,
                "stock_volatility": 0.05,
                "analysis_interval": 3600,
                "lookback_days": 30,
                "tracked_stocks": [
                    {"symbol": "GOV", "name": "Government Efficiency", "price": 100.0, "volatility": 0.03},
                    {"symbol": "DEF", "name": "Defense Sector", "price": 95.0, "volatility": 0.04},
                    {"symbol": "EDU", "name": "Education Sector", "price": 110.0, "volatility": 0.02},
                    {"symbol": "HLT", "name": "Healthcare Sector", "price": 105.0, "volatility": 0.03},
                    {"symbol": "BIP", "name": "Bipartisan Index", "price": 80.0, "volatility": 0.06}
                ]
            }
            
            self.save_parameters(default_params)
            self.log_admin_action(confirm_interaction.user.id, "reset_all_parameters", {})
            
            embed = discord.Embed(
                title="✅ Economic Parameters Reset",
                description="All economic parameters have been reset to default values",
                color=0x00ff00
            )
            
            await confirm_interaction.response.edit_message(content=None, embed=embed, view=None)
        
        async def cancel_callback(cancel_interaction):
            embed = discord.Embed(
                title="❌ Reset Cancelled",
                description="Economic parameters remain unchanged",
                color=0xff0000
            )
            await cancel_interaction.response.edit_message(content=None, embed=embed, view=None)
        
        confirm_button = discord.ui.Button(label="Confirm Reset", style=discord.ButtonStyle.danger)
        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        
        view.add_item(confirm_button)
        view.add_item(cancel_button)
        
        embed = discord.Embed(
            title="⚠️ Confirm Parameter Reset",
            description="This will reset ALL economic parameters to default values. This action cannot be undone.",
            color=0xff9900
        )
        
        await interaction.response.send_message(embed=embed, view=view)
    
    # Status and Monitoring Commands
    @commands.slash_command(name="econ_status", description="View current economic system status and parameters")
    @commands.has_role(Roles.ADMIN)
    async def system_status(self, interaction: discord.Interaction):
        """Show economic system status"""
        params = self.load_parameters()
        
        embed = discord.Embed(
            title="📊 Economic System Status",
            color=0x0099ff,
            timestamp=datetime.utcnow()
        )
        
        # GDP Settings
        gdp_weights = params.get("gdp_weights", {})
        embed.add_field(
            name="GDP Weights",
            value=f"Legislative: {gdp_weights.get('legislative', 0.4):.2f}\nCommittee: {gdp_weights.get('committee', 0.3):.2f}\nPublic: {gdp_weights.get('public', 0.3):.2f}",
            inline=True
        )
        
        # Market Settings
        embed.add_field(
            name="Market Settings",
            value=f"Inflation: {params.get('inflation_base', 2.5):.2f}%\nAnalysis Interval: {params.get('analysis_interval', 3600)//60} min",
            inline=True
        )
        
        # Stock Count
        stock_count = len(params.get("tracked_stocks", []))
        embed.add_field(
            name="Tracked Stocks",
            value=f"{stock_count} symbols",
            inline=True
        )
        
        # Active Scenario
        if "scenario_active" in params:
            scenario = params["scenario_active"]
            embed.add_field(
                name="Active Scenario",
                value=f"**{scenario['name'].title()}**\nActivated: {scenario['activated_at'][:10]}",
                inline=False
            )
        
        # Data Files Status
        data_files = ["gdp.json", "stocks.json", "inflation.json", "unemployment.json", "sentiment.json"]
        existing_files = [f for f in data_files if (self.data_dir / f).exists()]
        
        embed.add_field(
            name="Data Files",
            value=f"{len(existing_files)}/{len(data_files)} files exist",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomicAdmin(bot))