"""
Economic Analysis Engine for Virtual Congress Discord Bot
Provides comprehensive economic data collection and analysis with agentic loops
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import discord
from discord.ext import commands, tasks
import google.generativeai as genai
from config import GEMINI_API_KEY, Roles
import aiohttp
import re
from pathlib import Path

# Configure Gemini 2.5
genai.configure(api_key=GEMINI_API_KEY)

class EconomicEngine(commands.Cog):
    """Advanced Economic Analysis System for Virtual Congress"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = Path("economic_data")
        self.data_dir.mkdir(exist_ok=True)
        self.analysis_running = False
        
        # Initialize Gemini 2.5 model
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Economic parameters (admin configurable)
        self.parameters = self.load_parameters()
        
        # Start background analysis loop
        self.economic_analysis_loop.start()
    
    def load_parameters(self) -> Dict[str, Any]:
        """Load economic parameters or create defaults"""
        params_file = self.data_dir / "parameters.json"
        
        default_params = {
            "gdp_weights": {
                "legislative": 0.4,
                "committee": 0.3,
                "public": 0.3
            },
            "inflation_base": 2.5,
            "stock_volatility": 0.05,
            "analysis_interval": 3600,  # 1 hour
            "lookback_days": 30,
            # Note: Stock tracking moved to stock_market.py for real stock integration
        }
        
        if params_file.exists():
            with open(params_file, 'r') as f:
                return json.load(f)
        else:
            self.save_parameters(default_params)
            return default_params
    
    def save_parameters(self, params: Dict[str, Any]) -> None:
        """Save economic parameters to file"""
        with open(self.data_dir / "parameters.json", 'w') as f:
            json.dump(params, f, indent=2)
    
    async def get_document_content(self, doc_url: str) -> Optional[str]:
        """Extract content from Google Docs link"""
        try:
            # Convert Google Docs URL to export format
            if "docs.google.com" in doc_url:
                doc_id = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc_url)
                if doc_id:
                    export_url = f"https://docs.google.com/document/d/{doc_id.group(1)}/export?format=txt"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(export_url) as response:
                            if response.status == 200:
                                content = await response.text()
                                return content[:10000]  # Limit content size
            return None
        except Exception as e:
            print(f"Error fetching document: {e}")
            return None
    
    async def collect_channel_activity(self, days_back: int = 1) -> Dict[str, Any]:
        """Collect and analyze activity from all server channels"""
        activity_data = {
            "legislative": [],
            "committee": [],
            "public": [],
            "documents": []
        }
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Define channel categories for economic analysis
        legislative_keywords = ["bill", "vote", "legislation", "amendment", "resolution"]
        committee_keywords = ["committee", "hearing", "subcommittee", "markup"]
        
        print(f"🔒 Economic analysis restricted to authorized channels only")
        
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                try:
                    # Skip if bot doesn't have read permissions
                    if not channel.permissions_for(guild.me).read_message_history:
                        continue
                    
                    # Skip if channel is not in allowed list for economic analysis
                    from economic_utils import is_channel_allowed
                    if not is_channel_allowed(channel.name):
                        continue
                    
                    messages = []
                    async for message in channel.history(limit=1000, after=cutoff_date):
                        if message.author.bot:
                            continue
                            
                        message_data = {
                            "content": message.content[:500],  # Limit message length
                            "timestamp": message.created_at.isoformat(),
                            "channel": channel.name,
                            "author_roles": [role.name for role in getattr(message.author, 'roles', [])],
                            "reactions": len(message.reactions),
                            "replies": len(getattr(message, 'replies', []))
                        }
                        
                        # Extract document links
                        urls = re.findall(r'https://docs\.google\.com/document/d/[^\s]+', message.content)
                        for url in urls:
                            doc_content = await self.get_document_content(url)
                            if doc_content:
                                activity_data["documents"].append({
                                    "url": url,
                                    "content": doc_content,
                                    "channel": channel.name,
                                    "timestamp": message.created_at.isoformat()
                                })
                        
                        messages.append(message_data)
                    
                    # Categorize channel activity using economic analysis categories
                    from economic_utils import get_channel_category
                    econ_category = get_channel_category(channel.name)
                    
                    # Map economic categories to activity data structure
                    if econ_category in ["CONGRESS", "EXECUTIVE"]:
                        activity_data["legislative"].extend(messages)
                    elif econ_category in ["COURTS"]:
                        activity_data["committee"].extend(messages)  # Courts handled as specialized committee work
                    elif econ_category in ["NEWS", "PUBLIC_SQUARE"]:
                        activity_data["public"].extend(messages)
                    elif econ_category in ["STATES"]:
                        activity_data["committee"].extend(messages)  # State government handled as committee work
                    else:
                        # Fallback to old logic for any edge cases
                        channel_lower = channel.name.lower()
                        if any(keyword in channel_lower for keyword in legislative_keywords):
                            activity_data["legislative"].extend(messages)
                        elif any(keyword in channel_lower for keyword in committee_keywords):
                            activity_data["committee"].extend(messages)
                        else:
                            activity_data["public"].extend(messages)
                        
                except Exception as e:
                    print(f"Error collecting from channel {channel.name}: {e}")
                    continue
        
        return activity_data
    
    def get_latest_economic_report(self) -> Optional[Dict[str, Any]]:
        """Get the most recent economic report or None if no data exists"""
        reports_file = self.data_dir / "reports.json"
        
        if not reports_file.exists():
            return None
        
        try:
            with open(reports_file, 'r') as f:
                reports = json.load(f)
                if reports:
                    return reports[-1]  # Return most recent report
        except (json.JSONDecodeError, IndexError):
            pass
        
        return None
    
    async def analyze_with_gemini(self, activity_data: Dict[str, Any], previous_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Use Gemini 2.5 to analyze economic data and generate insights"""
        
        context_prompt = """You are an advanced economic analyst for a Virtual Congress simulation. 
        Analyze the provided Discord server activity and generate comprehensive economic indicators.
        
        Your analysis should include:
        1. GDP calculation based on legislative productivity
        2. Stock market movements for government sectors
        3. Inflation indicators from policy discussions
        4. Unemployment metrics from committee activity
        5. Market sentiment from public discussions
        6. Budget efficiency analysis
        7. Trade and interstate relations
        
        Focus on governmental activity patterns, policy impacts, and public engagement levels.
        Provide specific numerical values and trend analysis."""
        
        if previous_report:
            context_prompt += f"\n\nPrevious Economic Report (for continuity):\n{json.dumps(previous_report, indent=2)}"
        else:
            context_prompt += "\n\nNote: This is initial economic analysis - no previous data available."
        
        data_prompt = f"""
        Discord Activity Data:
        
        Legislative Activity ({len(activity_data['legislative'])} messages):
        {json.dumps(activity_data['legislative'][:10], indent=2)}
        
        Committee Activity ({len(activity_data['committee'])} messages):
        {json.dumps(activity_data['committee'][:10], indent=2)}
        
        Public Discussion ({len(activity_data['public'])} messages):
        {json.dumps(activity_data['public'][:10], indent=2)}
        
        Documents Analyzed ({len(activity_data['documents'])} documents):
        {json.dumps([doc['content'][:200] for doc in activity_data['documents'][:5]], indent=2)}
        
        Economic Parameters:
        {json.dumps(self.parameters, indent=2)}
        
        Please provide a detailed economic analysis in JSON format with the following structure:
        {{
            "timestamp": "ISO datetime",
            "gdp": {{
                "value": number,
                "change_percent": number,
                "components": {{"legislative": number, "committee": number, "public": number}}
            }},
            "stocks": [
                {{"symbol": "string", "price": number, "change_percent": number, "volume": number}}
            ],
            "inflation": {{
                "rate": number,
                "trend": "string",
                "policy_impact": "string"
            }},
            "unemployment": {{
                "rate": number,
                "committee_activity_index": number
            }},
            "sentiment": {{
                "market_confidence": number,
                "public_approval": number,
                "bipartisan_cooperation": number
            }},
            "insights": [
                "string insights about economic trends"
            ]
        }}
        """
        
        try:
            response = await self.model.generate_content_async(
                f"{context_prompt}\n\n{data_prompt}",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=4000
                )
            )
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            print(f"❌ Gemini analysis failed: {e}")
            print("🚫 Economic analysis requires AI - no synthetic data generated")
            raise Exception(f"Economic analysis failed: {e}")
    
    async def save_economic_data(self, analysis: Dict[str, Any]) -> None:
        """Save economic analysis to data files"""
        
        # Save to comprehensive reports file
        reports_file = self.data_dir / "reports.json"
        reports = []
        if reports_file.exists():
            with open(reports_file, 'r') as f:
                reports = json.load(f)
        
        reports.append(analysis)
        # Keep only last 100 reports
        reports = reports[-100:]
        
        with open(reports_file, 'w') as f:
            json.dump(reports, f, indent=2)
        
        # Save individual data files for easy access
        for category in ["gdp", "stocks", "inflation", "unemployment", "sentiment"]:
            if category in analysis:
                category_file = self.data_dir / f"{category}.json"
                
                category_data = []
                if category_file.exists():
                    with open(category_file, 'r') as f:
                        category_data = json.load(f)
                
                category_data.append({
                    "timestamp": analysis["timestamp"],
                    "data": analysis[category]
                })
                
                # Keep only last 1000 entries per category
                category_data = category_data[-1000:]
                
                with open(category_file, 'w') as f:
                    json.dump(category_data, f, indent=2)
    
    @tasks.loop(seconds=3600)  # Run every hour by default
    async def economic_analysis_loop(self):
        """Main agentic loop for continuous economic analysis"""
        if self.analysis_running:
            return
        
        self.analysis_running = True
        
        try:
            print("Starting economic analysis cycle...")
            
            # Check if we have existing economic data
            latest_report = self.get_latest_economic_report()
            
            if latest_report is None:
                # No existing data - look back 30 days for initial analysis
                print("No existing economic data found. Analyzing last 30 days...")
                days_back = self.parameters["lookback_days"]
            else:
                # Use existing data - only analyze recent activity
                print("Found existing economic data. Analyzing recent activity...")
                days_back = 1
            
            # Collect Discord activity
            activity_data = await self.collect_channel_activity(days_back)
            
            # Analyze with Gemini
            analysis = await self.analyze_with_gemini(activity_data, latest_report)
            
            # Save the results
            await self.save_economic_data(analysis)
            
            print(f"Economic analysis completed. GDP: {analysis.get('gdp', {}).get('value', 'N/A')}")
            
        except Exception as e:
            print(f"Error in economic analysis loop: {e}")
        finally:
            self.analysis_running = False
    
    @economic_analysis_loop.before_loop
    async def before_analysis_loop(self):
        """Wait for bot to be ready before starting analysis"""
        await self.bot.wait_until_ready()
    
    # Commands
    @commands.slash_command(name="fetch_econ_data", description="Trigger comprehensive economic data collection and analysis")
    @commands.has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
    async def fetch_econ_data(self, interaction: discord.Interaction):
        """Manually trigger economic data collection"""
        await interaction.response.defer()
        
        try:
            # Check for existing data
            latest_report = self.get_latest_economic_report()
            
            if latest_report is None:
                await interaction.followup.send("🔍 No existing economic data found. Analyzing last 30 days of server activity...")
                days_back = self.parameters["lookback_days"]
            else:
                await interaction.followup.send("📊 Found existing economic data. Analyzing recent activity for updated report...")
                days_back = 1
            
            # Collect and analyze data
            activity_data = await self.collect_channel_activity(days_back)
            analysis = await self.analyze_with_gemini(activity_data, latest_report)
            await self.save_economic_data(analysis)
            
            # Create response embed
            embed = discord.Embed(
                title="📈 Economic Analysis Complete",
                color=0x00ff00,
                timestamp=datetime.utcnow()
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
            
            embed.add_field(
                name="Data Sources",
                value=f"Legislative: {len(activity_data['legislative'])}\nCommittee: {len(activity_data['committee'])}\nPublic: {len(activity_data['public'])}\nDocuments: {len(activity_data['documents'])}",
                inline=False
            )
            
            if analysis.get('insights'):
                embed.add_field(
                    name="Key Insights",
                    value="\n".join(f"• {insight}" for insight in analysis['insights'][:3]),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error during economic analysis: {str(e)}")

async def setup(bot):
    await bot.add_cog(EconomicEngine(bot))