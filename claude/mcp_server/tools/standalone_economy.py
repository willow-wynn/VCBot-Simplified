"""
Standalone Economic Data Manager for MCP Server
Full read/write economic system that works exactly like the agentic economic bot
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import time

class StandaloneEconomyManager:
    """Complete economic data management system for MCP server"""
    
    def __init__(self, base_path: str = "/Users/wynndiaz/VCBot"):
        self.base_path = Path(base_path)
        self.economic_data_dir = self.base_path / "economic_data"
        self.stock_data_dir = self.base_path / "stock_data"
        
        # Channel restrictions (same as agentic bot)
        self.ALLOWED_CHANNELS = {
            "NEWS": [
                "news-information", "official-rp-news", "parody", "pbn", 
                "liberty-ledger", "wall-street-journal", "4e-news-from-the-hill", 
                "202news", "msnbc"
            ],
            "CONGRESS": [
                "speaker-announcements", "house-docket", "house-floor", 
                "house-vote-results", "senate-announcements", "senate-docket", 
                "senate-floor", "senate-vote-results", "committee-announcements"
            ],
            "EXECUTIVE": [
                "bills-signed-into-law", "bills-vetoed", "presidential-congressional-desk",
                "president-announcements", "press-briefing-room", "cabinet-announcements",
                "executive-orders", "presidential-memoranda"
            ],
            "STATES": [
                "olympia-governor", "pacifica-governor", "lincoln-governor", 
                "jackson-governor", "frontier-governor"
            ],
            "COURTS": ["district-court-announcements", "supreme-court-announcements"],
            "PUBLIC_SQUARE": [
                "rp-chat", "twitter-rp", "press-releases", "press-room", 
                "election-announcements"
            ]
        }
        
        # Flatten authorized channels
        self.all_allowed_channels = []
        for channels in self.ALLOWED_CHANNELS.values():
            self.all_allowed_channels.extend(channels)
        
        # Memory storage (in-memory for MCP session)
        self.memory_entries = {}
        self.next_memory_id = 1
        
        # Ensure directories exist
        self.economic_data_dir.mkdir(exist_ok=True)
        self.stock_data_dir.mkdir(exist_ok=True)
    
    # ==================== FILE I/O OPERATIONS ====================
    
    def read_json_file(self, directory: Path, filename: str) -> Optional[Dict[str, Any]]:
        """Read a JSON file from specified directory"""
        try:
            file_path = directory / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            return None
    
    def write_json_file(self, directory: Path, filename: str, data: Dict[str, Any]) -> bool:
        """Write data to a JSON file"""
        try:
            file_path = directory / filename
            directory.mkdir(exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error writing {filename}: {e}")
            return False
    
    def append_economic_data(self, filename: str, data: Dict[str, Any]) -> bool:
        """Append timestamped data to economic data file"""
        try:
            file_path = self.economic_data_dir / filename
            
            # Read existing data or create new list
            if file_path.exists():
                with open(file_path, 'r') as f:
                    existing_data = json.load(f)
            else:
                existing_data = []
            
            # Append new entry with timestamp
            new_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data
            }
            existing_data.append(new_entry)
            
            # Write back to file
            with open(file_path, 'w') as f:
                json.dump(existing_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error appending to {filename}: {e}")
            return False
    
    # ==================== ECONOMIC DATA OPERATIONS ====================
    
    def get_fresh_economic_report(self) -> Dict[str, Any]:
        """Generate economic report from individual data files"""
        
        # Read individual data files
        gdp_data = self.read_json_file(self.economic_data_dir, "gdp.json")
        inflation_data = self.read_json_file(self.economic_data_dir, "inflation.json") 
        unemployment_data = self.read_json_file(self.economic_data_dir, "unemployment.json")
        sentiment_data = self.read_json_file(self.economic_data_dir, "sentiment.json")
        parameters = self.read_json_file(self.economic_data_dir, "parameters.json")
        
        # Extract latest data from each file (they're arrays of timestamped entries)
        latest_gdp = gdp_data[-1]["data"] if gdp_data and len(gdp_data) > 0 else None
        latest_inflation = inflation_data[-1]["data"] if inflation_data and len(inflation_data) > 0 else None
        latest_unemployment = unemployment_data[-1]["data"] if unemployment_data and len(unemployment_data) > 0 else None
        latest_sentiment = sentiment_data[-1]["data"] if sentiment_data and len(sentiment_data) > 0 else None
        
        # Create comprehensive report
        report = {
            "metadata": {
                "analysis_type": "standalone_file_manager",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "source": "standalone_economy.py"
            },
            "gdp": {
                "current_gdp": latest_gdp.get("value", 26.8) if latest_gdp else 26.8,
                "quarterly_growth_percent": latest_gdp.get("change_percent", -1.2) if latest_gdp else -1.2,
                "annual_growth_percent": latest_gdp.get("quarterly_growth", -0.3) * 4 if latest_gdp else -2.8,
                "projected_growth": -1.8,
                "confidence_interval": 0.75,
                "outlook": latest_gdp.get("outlook", "Recessionary") if latest_gdp else "Recessionary"
            },
            "inflation": {
                "yoy_percent": latest_inflation.get("rate", 8.51) if latest_inflation else 8.51,
                "monthly_percent": 0.7,
                "core_inflation": 7.2,
                "federal_funds_rate": latest_inflation.get("federal_funds_rate", 4.0) if latest_inflation else 4.0,
                "target_rate": 2.0,
                "trend": latest_inflation.get("trend", "High") if latest_inflation else "High",
                "policy_impact": latest_inflation.get("policy_impact", "Restrictive monetary policy") if latest_inflation else "Restrictive monetary policy"
            },
            "unemployment": {
                "rate_percent": latest_unemployment.get("rate", 3.2) if latest_unemployment else 3.2,
                "jobless_claims": 240000,  # Not in data file, use default
                "participation_rate": 63.1,
                "underemployment": 7.8,
                "trend": latest_unemployment.get("trend", "Stable") if latest_unemployment else "Stable",
                "labor_market_state": latest_unemployment.get("labor_market_state", "Tight") if latest_unemployment else "Tight"
            },
            "sentiment": {
                "confidence_percent": latest_sentiment.get("market_confidence", 35) if latest_sentiment else 35,
                "anxiety_index_percent": latest_sentiment.get("inflation_anxiety", 78) if latest_sentiment else 78,
                "consumer_sentiment": latest_sentiment.get("consumer_confidence", 30) if latest_sentiment else 30,
                "business_confidence": latest_sentiment.get("business_sentiment", 40) if latest_sentiment else 40,
                "market_volatility": 31.2,
                "outlook": latest_sentiment.get("outlook", "Pessimistic") if latest_sentiment else "Pessimistic"
            },
            "parameters": parameters
        }
        
        return report
    
    def submit_economic_report(self, report_data: Dict[str, Any]) -> bool:
        """Submit new economic data to individual files"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Extract and save GDP data
            if "gdp" in report_data:
                gdp_entry = {
                    "value": report_data["gdp"].get("current_gdp", 26.8),
                    "change_percent": report_data["gdp"].get("quarterly_growth_percent", -1.2),
                    "quarterly_growth": report_data["gdp"].get("quarterly_growth_percent", -1.2) / 4,
                    "outlook": report_data["gdp"].get("outlook", "Recessionary")
                }
                self.append_economic_data("gdp.json", gdp_entry)
            
            # Extract and save inflation data
            if "inflation" in report_data:
                inflation_entry = {
                    "rate": report_data["inflation"].get("yoy_percent", 8.51),
                    "federal_funds_rate": report_data["inflation"].get("federal_funds_rate", 4.0),
                    "trend": report_data["inflation"].get("trend", "High"),
                    "policy_impact": report_data["inflation"].get("policy_impact", "Restrictive monetary policy")
                }
                self.append_economic_data("inflation.json", inflation_entry)
            
            # Extract and save unemployment data
            if "unemployment" in report_data:
                unemployment_entry = {
                    "rate": report_data["unemployment"].get("rate_percent", 3.2),
                    "trend": report_data["unemployment"].get("trend", "Stable"),
                    "labor_market_state": report_data["unemployment"].get("labor_market_state", "Tight")
                }
                self.append_economic_data("unemployment.json", unemployment_entry)
            
            # Extract and save sentiment data
            if "sentiment" in report_data:
                sentiment_entry = {
                    "market_confidence": report_data["sentiment"].get("confidence_percent", 35),
                    "inflation_anxiety": report_data["sentiment"].get("anxiety_index_percent", 78),
                    "consumer_confidence": report_data["sentiment"].get("consumer_sentiment", 30),
                    "business_sentiment": report_data["sentiment"].get("business_confidence", 40),
                    "outlook": report_data["sentiment"].get("outlook", "Pessimistic")
                }
                self.append_economic_data("sentiment.json", sentiment_entry)
            
            # Log the submission to reports.json
            report_entry = {
                "timestamp": timestamp,
                "report_id": f"econ_report_{int(time.time())}",
                "submitted_by": "mcp_claude_user",
                "data_summary": {
                    "gdp_growth": report_data.get("gdp", {}).get("quarterly_growth_percent", "N/A"),
                    "inflation_rate": report_data.get("inflation", {}).get("yoy_percent", "N/A"),
                    "unemployment_rate": report_data.get("unemployment", {}).get("rate_percent", "N/A"),
                    "market_confidence": report_data.get("sentiment", {}).get("confidence_percent", "N/A")
                }
            }
            
            reports_file = self.economic_data_dir / "reports.json"
            if reports_file.exists():
                with open(reports_file, 'r') as f:
                    reports = json.load(f)
            else:
                reports = []
            
            reports.append(report_entry)
            with open(reports_file, 'w') as f:
                json.dump(reports, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error submitting economic report: {e}")
            return False
    
    # ==================== STOCK MARKET OPERATIONS ====================
    
    def get_stock_market_data(self) -> Optional[Dict[str, Any]]:
        """Get complete stock market data"""
        return self.read_json_file(self.stock_data_dir, "market_data.json")
    
    def get_stock_history(self) -> Optional[Dict[str, Any]]:
        """Get stock price history"""
        return self.read_json_file(self.stock_data_dir, "stock_history.json")
    
    def update_stock_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Update stock market data file"""
        market_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        return self.write_json_file(self.stock_data_dir, "market_data.json", market_data)
    
    def get_stock_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current price for a specific stock"""
        market_data = self.get_stock_market_data()
        if not market_data:
            return None
        
        # Search through all categories for the stock
        for category_name, category_data in market_data.get("categories", {}).items():
            for stock in category_data.get("stocks", []):
                if stock.get("symbol") == symbol:
                    return {
                        "symbol": symbol,
                        "current": stock.get("price", 0),
                        "company_name": stock.get("name", "Unknown"),
                        "sector": category_name,
                        "industry": stock.get("sector", "Unknown"),
                        "daily_range_low": stock.get("daily_range_low", 0),
                        "daily_range_high": stock.get("daily_range_high", 0),
                        "sector_factor": stock.get("sector_factor", 1.0),
                        "last_updated": market_data.get("last_updated", "Unknown")
                    }
        
        return {"error": f"Stock {symbol} not found"}
    
    def get_all_stocks(self) -> List[Dict[str, Any]]:
        """Get all stocks with current prices"""
        market_data = self.get_stock_market_data()
        if not market_data:
            return []
        
        all_stocks = []
        for category_name, category_data in market_data.get("categories", {}).items():
            for stock in category_data.get("stocks", []):
                stock_info = {
                    "symbol": stock.get("symbol"),
                    "name": stock.get("name"),
                    "price": stock.get("price", 0),
                    "sector": category_name,
                    "industry": stock.get("sector", "Unknown"),
                    "daily_range_low": stock.get("daily_range_low", 0),
                    "daily_range_high": stock.get("daily_range_high", 0)
                }
                all_stocks.append(stock_info)
        
        return all_stocks
    
    def get_market_parameters(self) -> Dict[str, Any]:
        """Get current market parameters"""
        market_data = self.get_stock_market_data()
        if market_data and "market_params" in market_data:
            return market_data["market_params"]
        
        # Default parameters if no market data
        return {
            "trend_direction": -0.35,
            "volatility": 0.8,
            "momentum": 0.25,
            "market_sentiment": 0.35,
            "long_term_outlook": 0.4
        }
    
    def update_market_parameters(self, new_params: Dict[str, Any]) -> bool:
        """Update market parameters"""
        market_data = self.get_stock_market_data()
        if not market_data:
            return False
        
        market_data["market_params"].update(new_params)
        return self.update_stock_market_data(market_data)
    
    # ==================== CHANNEL & ACCESS CONTROL ====================
    
    def is_channel_allowed(self, channel_name: str) -> bool:
        """Check if channel is authorized for economic analysis"""
        return channel_name in self.all_allowed_channels
    
    def get_channel_category(self, channel_name: str) -> str:
        """Get the category of an authorized channel"""
        for category, channels in self.ALLOWED_CHANNELS.items():
            if channel_name in channels:
                return category
        return "UNKNOWN"
    
    def get_authorized_channels(self, category: Optional[str] = None) -> List[str]:
        """Get list of authorized channels, optionally filtered by category"""
        if category and category.upper() in self.ALLOWED_CHANNELS:
            return self.ALLOWED_CHANNELS[category.upper()]
        return self.all_allowed_channels
    
    # ==================== MEMORY MANAGEMENT ====================
    
    def add_memory_entry(self, content: str, admin_id: int = 0) -> str:
        """Add memory entry for AI context continuity"""
        entry_id = str(self.next_memory_id)
        self.memory_entries[entry_id] = {
            "id": entry_id,
            "content": content,
            "admin_id": admin_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.next_memory_id += 1
        return entry_id
    
    def remove_memory_entry(self, entry_id: str) -> bool:
        """Remove memory entry by ID"""
        if entry_id in self.memory_entries:
            del self.memory_entries[entry_id]
            return True
        return False
    
    def get_memory_context(self) -> str:
        """Get formatted memory context for AI analysis"""
        if not self.memory_entries:
            return ""
        
        context_lines = []
        for entry in self.memory_entries.values():
            timestamp = entry["timestamp"][:19]  # Remove timezone info for readability
            context_lines.append(f"[{timestamp}] {entry['content']}")
        
        return "\n".join(context_lines)
    
    # ==================== ADMIN & LOGGING ====================
    
    def log_admin_action(self, admin_id: int, action: str, details: Dict[str, Any]) -> None:
        """Log administrative action for audit trail"""
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "admin_id": admin_id,
                "action": action,
                "details": details
            }
            
            admin_log_file = self.economic_data_dir / "admin_log.json"
            if admin_log_file.exists():
                with open(admin_log_file, 'r') as f:
                    admin_log = json.load(f)
            else:
                admin_log = []
            
            admin_log.append(log_entry)
            with open(admin_log_file, 'w') as f:
                json.dump(admin_log, f, indent=2)
                
        except Exception as e:
            print(f"Error logging admin action: {e}")
    
    def get_economic_status(self) -> Dict[str, Any]:
        """Get comprehensive economic system status"""
        files_to_check = ["gdp.json", "inflation.json", "unemployment.json", "sentiment.json", "parameters.json"]
        file_status = {}
        
        for filename in files_to_check:
            file_path = self.economic_data_dir / filename
            if file_path.exists():
                stat = file_path.stat()
                file_status[filename] = {
                    "exists": True,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            else:
                file_status[filename] = {"exists": False}
        
        # Check stock data
        stock_files = ["market_data.json", "stock_history.json"]
        stock_status = {}
        for filename in stock_files:
            file_path = self.stock_data_dir / filename
            if file_path.exists():
                stat = file_path.stat()
                stock_status[filename] = {
                    "exists": True,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            else:
                stock_status[filename] = {"exists": False}
        
        return {
            "data_directory": str(self.economic_data_dir),
            "stock_directory": str(self.stock_data_dir),
            "economic_files": file_status,
            "stock_files": stock_status,
            "total_economic_files": len([f for f in file_status.values() if f.get("exists")]),
            "total_stock_files": len([f for f in stock_status.values() if f.get("exists")]),
            "authorized_channels": len(self.all_allowed_channels),
            "memory_entries": len(self.memory_entries),
            "last_check": datetime.now(timezone.utc).isoformat()
        }
    
    def set_economic_parameter(self, parameter: str, value: float) -> bool:
        """Set economic parameter with validation"""
        valid_parameters = [
            "inflation_base", "unemployment_base", "gdp_base", 
            "stock_volatility", "analysis_interval", "lookback_days"
        ]
        
        if parameter not in valid_parameters:
            return False
        
        try:
            # Read current parameters
            parameters = self.read_json_file(self.economic_data_dir, "parameters.json")
            if not parameters:
                parameters = {}
            
            # Update parameter
            parameters[parameter] = value
            parameters["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            # Save updated parameters
            return self.write_json_file(self.economic_data_dir, "parameters.json", parameters)
            
        except Exception as e:
            print(f"Error setting parameter {parameter}: {e}")
            return False

# Global instance for MCP server
standalone_economy = StandaloneEconomyManager()