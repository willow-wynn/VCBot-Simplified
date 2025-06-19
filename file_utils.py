"""
Simple file utilities for VCBot.
Replaces the complex FileManager and Repository classes with direct functions.
"""

import json
import csv
import asyncio
import aiofiles
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from config import (
    BILL_REFS_FILE, QUERIES_FILE, DATA_DIR, ECONOMIC_DATA_DIR, 
    STOCK_DATA_DIR, BASE_DIR, GUILD_ID, ensure_guild_directories
)

# File paths for channel restrictions (guild-specific)
CHANNEL_RESTRICTIONS_FILE = DATA_DIR / "channel_restrictions.json"

# Global variables for data
_bill_refs = None
_channel_restrictions = None

def load_bill_references() -> Dict[str, int]:
    """Load bill reference numbers from JSON file."""
    global _bill_refs
    if _bill_refs is None:
        try:
            with open(BILL_REFS_FILE, 'r') as f:
                _bill_refs = json.load(f)
        except FileNotFoundError:
            _bill_refs = {"hr": 1, "hres": 1, "hjres": 1, "hconres": 1}
            save_bill_references()
    return _bill_refs

def save_bill_references():
    """Save bill reference numbers to JSON file."""
    global _bill_refs
    if _bill_refs is not None:
        with open(BILL_REFS_FILE, 'w') as f:
            json.dump(_bill_refs, f, indent=2)

def get_next_reference(bill_type: str) -> int:
    """Get next reference number for a bill type."""
    refs = load_bill_references()
    next_num = refs.get(bill_type, 1)
    refs[bill_type] = next_num + 1
    save_bill_references()
    return next_num

def set_reference(bill_type: str, number: int):
    """Set reference number for a bill type."""
    refs = load_bill_references()
    refs[bill_type] = number
    save_bill_references()

async def append_file(file_path: str, content: str):
    """Append content to a file asynchronously."""
    async with aiofiles.open(file_path, 'a', encoding='utf-8') as f:
        await f.write(content)

async def save_query_log(query: str, response: str):
    """Save query and response to CSV log."""
    import io
    
    # Create CSV row
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f'query: {query}', f'response: {response}'])
    csv_line = output.getvalue()
    
    # Append to file
    await append_file(str(QUERIES_FILE), csv_line)

def read_knowledge_file(file_key: str) -> str:
    """Read content from a knowledge file."""
    from config import KNOWLEDGE_FILES
    file_path = KNOWLEDGE_FILES.get(file_key)
    if not file_path:
        raise ValueError(f"Unknown knowledge file: {file_key}")
    
    return Path(file_path).read_text(encoding='utf-8')

def get_bill_content(filename: str) -> Optional[str]:
    """Get bill content from text file."""
    from config import BILL_TEXT_DIR
    
    # Ensure .txt extension
    if not filename.endswith('.txt'):
        filename += '.txt'
    
    bill_path = BILL_TEXT_DIR / filename
    if bill_path.exists():
        return bill_path.read_text(encoding='utf-8')
    return None

def get_bill_metadata(filename: str) -> Optional[Dict[str, Any]]:
    """Get bill metadata from JSON file."""
    from config import BILL_JSON_DIR
    
    # Remove .txt extension if present and add .json
    if filename.endswith('.txt'):
        filename = filename[:-4]
    
    json_path = BILL_JSON_DIR / f"{filename}.json"
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_bill_content(filename: str, content: str):
    """Save bill content to text file."""
    from config import BILL_TEXT_DIR
    
    # Ensure .txt extension
    if not filename.endswith('.txt'):
        filename += '.txt'
    
    bill_path = BILL_TEXT_DIR / filename
    bill_path.write_text(content, encoding='utf-8')

def save_bill_metadata(filename: str, metadata: Dict[str, Any]):
    """Save bill metadata to JSON file."""
    from config import BILL_JSON_DIR
    
    # Remove .txt extension if present and add .json
    if filename.endswith('.txt'):
        filename = filename[:-4]
    
    json_path = BILL_JSON_DIR / f"{filename}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

def ensure_directories():
    """Ensure all required directories exist."""
    ensure_guild_directories()

def migrate_data_to_guild_directory():
    """
    One-time migration of existing data to guild-specific directory.
    Only runs if guild directory doesn't exist but root files do.
    Copies (not moves) to preserve original data.
    """
    # Production guild ID
    PROD_GUILD = 654458344781774879
    
    # Only migrate for production guild
    if GUILD_ID != PROD_GUILD:
        return
        
    # Check if migration is needed
    if (DATA_DIR / "bill_refs.json").exists():
        print(f"Guild data directory already exists for {GUILD_ID}, skipping migration")
        return
        
    # Check if source data exists
    old_bill_refs = BASE_DIR / "bill_refs.json"
    if not old_bill_refs.exists():
        print("No existing data to migrate")
        return
        
    print(f"Migrating data to guild-specific directory: {DATA_DIR}")
    
    # Ensure directories exist
    ensure_guild_directories()
    
    # Copy root level files
    files_to_copy = [
        ("bill_refs.json", DATA_DIR / "bill_refs.json"),
        ("news.txt", DATA_DIR / "news.txt"),
        ("queries.csv", DATA_DIR / "queries.csv"),
        ("channel_restrictions.json", DATA_DIR / "channel_restrictions.json"),
    ]
    
    for src_name, dst_path in files_to_copy:
        src_path = BASE_DIR / src_name
        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            print(f"Copied {src_name}")
    
    # Copy economic data
    old_econ_dir = BASE_DIR / "economic_data"
    if old_econ_dir.exists():
        for file in old_econ_dir.glob("*.json"):
            shutil.copy2(file, ECONOMIC_DATA_DIR / file.name)
        print("Copied economic data")
    
    # Copy stock data
    old_stock_dir = BASE_DIR / "stock_data"
    if old_stock_dir.exists():
        for file in old_stock_dir.glob("*.json"):
            shutil.copy2(file, STOCK_DATA_DIR / file.name)
        # Copy analysis logs subdirectory
        old_logs = old_stock_dir / "analysis_logs"
        if old_logs.exists():
            new_logs = STOCK_DATA_DIR / "analysis_logs"
            new_logs.mkdir(exist_ok=True)
            for file in old_logs.glob("*.json"):
                shutil.copy2(file, new_logs / file.name)
        print("Copied stock data")
    
    # Copy bill data
    old_bill_dir = BASE_DIR / "every-vc-bill"
    if old_bill_dir.exists():
        # Copy text files
        old_txts = old_bill_dir / "txts"
        if old_txts.exists():
            for file in old_txts.glob("*.txt"):
                shutil.copy2(file, DATA_DIR / "every-vc-bill" / "txts" / file.name)
        
        # Copy PDF files
        old_pdfs = old_bill_dir / "pdfs"
        if old_pdfs.exists():
            for file in old_pdfs.glob("*.pdf"):
                shutil.copy2(file, DATA_DIR / "every-vc-bill" / "pdfs" / file.name)
        
        # Copy JSON files
        old_jsons = old_bill_dir / "json_outputs"
        if old_jsons.exists():
            for file in old_jsons.glob("*.json"):
                shutil.copy2(file, DATA_DIR / "every-vc-bill" / "json_outputs" / file.name)
        
        print("Copied bill data")
    
    print("Migration complete!")

def initialize_guild_data_structure():
    """
    Initialize empty data structure for new guild.
    Creates all required JSON files with default values.
    """
    print(f"Initializing data structure for guild {GUILD_ID}")
    
    # Ensure directories exist
    ensure_guild_directories()
    
    # Initialize bill references
    if not BILL_REFS_FILE.exists():
        default_refs = {"hr": 1, "hres": 1, "hjres": 1, "hconres": 1, "h.res": 1}
        with open(BILL_REFS_FILE, 'w') as f:
            json.dump(default_refs, f, indent=2)
    
    # Initialize channel restrictions
    if not CHANNEL_RESTRICTIONS_FILE.exists():
        with open(CHANNEL_RESTRICTIONS_FILE, 'w') as f:
            json.dump({}, f, indent=2)
    
    # Initialize economic data files
    economic_files = {
        "parameters.json": {
            "econ_channel": 1275044113754095697,
            "interval": 15,
            "is_running": False,
            "inflation_rate": 0.02
        },
        "gdp.json": {"current": 21.5, "history": []},
        "inflation.json": {"current": 0.02, "history": []},
        "unemployment.json": {"current": 0.04, "history": []},
        "sentiment.json": {"current": {"positive": 0.5, "negative": 0.3, "neutral": 0.2}, "history": []},
        "admin_log.json": [],
        "memory.json": {"entries": []},
        "reports.json": []
    }
    
    for filename, default_data in economic_files.items():
        filepath = ECONOMIC_DATA_DIR / filename
        if not filepath.exists():
            with open(filepath, 'w') as f:
                json.dump(default_data, f, indent=2)
    
    # Initialize stock data files
    stock_files = {
        "market_data.json": {
            "market_open": True,
            "last_update": None,
            "stocks": {},
            "market_params": {
                "trend_direction": 0.0,
                "volatility": 0.3,
                "momentum": 0.5,
                "market_sentiment": 0.5,
                "long_term_outlook": 0.5
            }
        },
        "stock_history.json": {},
        "daily_analysis.json": {},
        "user_portfolios.json": {}
    }
    
    for filename, default_data in stock_files.items():
        filepath = STOCK_DATA_DIR / filename
        if not filepath.exists():
            with open(filepath, 'w') as f:
                json.dump(default_data, f, indent=2)
    
    # Create empty news and queries files
    if not (DATA_DIR / "news.txt").exists():
        (DATA_DIR / "news.txt").write_text("")
    
    if not (DATA_DIR / "queries.csv").exists():
        (DATA_DIR / "queries.csv").write_text("")
    
    print("Initialization complete!")

# Channel Restrictions Management

def load_channel_restrictions() -> Dict[str, Dict[str, Any]]:
    """Load channel restrictions from JSON file."""
    global _channel_restrictions
    if _channel_restrictions is None:
        try:
            with open(CHANNEL_RESTRICTIONS_FILE, 'r') as f:
                _channel_restrictions = json.load(f)
        except FileNotFoundError:
            _channel_restrictions = {}
            save_channel_restrictions()
    return _channel_restrictions

def save_channel_restrictions():
    """Save channel restrictions to JSON file."""
    global _channel_restrictions
    if _channel_restrictions is not None:
        with open(CHANNEL_RESTRICTIONS_FILE, 'w') as f:
            json.dump(_channel_restrictions, f, indent=2)

def set_command_channel_restriction(command_name: str, mode: str, channels: list):
    """Set channel restriction for a command.
    
    Args:
        command_name: Name of the command (e.g., 'helper', 'stocks_buy')
        mode: 'whitelist' or 'blacklist'
        channels: List of channel names or IDs
    """
    restrictions = load_channel_restrictions()
    
    if mode not in ['whitelist', 'blacklist']:
        raise ValueError("Mode must be 'whitelist' or 'blacklist'")
    
    restrictions[command_name] = {
        'mode': mode,
        'channels': channels
    }
    
    save_channel_restrictions()

def remove_command_channel_restriction(command_name: str):
    """Remove channel restriction for a command."""
    restrictions = load_channel_restrictions()
    
    if command_name in restrictions:
        del restrictions[command_name]
        save_channel_restrictions()
        return True
    return False

def check_command_channel_allowed(command_name: str, channel_id: int, channel_name: str = None) -> bool:
    """Check if a command is allowed in a specific channel.
    
    Args:
        command_name: Name of the command
        channel_id: Discord channel ID
        channel_name: Discord channel name (optional)
        
    Returns:
        True if command is allowed, False otherwise
    """
    restrictions = load_channel_restrictions()
    
    # If no restrictions for this command, allow it
    if command_name not in restrictions:
        return True
    
    restriction = restrictions[command_name]
    mode = restriction['mode']
    restricted_channels = restriction['channels']
    
    # Check against both channel ID (as string) and channel name
    channel_id_str = str(channel_id)
    
    # Check if channel matches any in the restriction list
    is_in_list = False
    for channel in restricted_channels:
        if (str(channel) == channel_id_str or 
            (channel_name and str(channel).lower() == channel_name.lower())):
            is_in_list = True
            break
    
    # For whitelist: only allow if channel is in the list
    # For blacklist: allow unless channel is in the list
    if mode == 'whitelist':
        return is_in_list
    else:  # blacklist
        return not is_in_list

def get_command_restrictions() -> Dict[str, Dict[str, Any]]:
    """Get all current command channel restrictions."""
    return load_channel_restrictions()

def get_available_commands(bot_instance=None) -> list:
    """Get list of available command names for restriction management."""
    # If bot instance provided, dynamically get all registered commands
    if bot_instance and hasattr(bot_instance, 'tree'):
        command_names = []
        # Get all application commands from the command tree
        for command in bot_instance.tree.get_commands():
            command_names.append(command.name)
        # Sort alphabetically for better organization
        return sorted(command_names) if command_names else get_default_command_list()
    
    # Fallback to default list if no bot instance
    return get_default_command_list()

def get_default_command_list() -> list:
    """Get default list of command names as fallback."""
    return [
        'helper', 'bill_keyword_search', 'reference', 'modifyrefs', 'add_bill',
        'econ_impact_report', 'role', 'fetch_econ_data', 'econ_report', 
        'econ_status', 'econ_set_inflation', 'econ_set_interval',
        'stocks_list', 'stocks_price', 'stocks_categories', 'stocks_history_48h',
        'stocks_buy', 'stocks_sell', 'stocks_portfolio', 'stocks_set_market',
        'stocks_force_update', 'stocks_reset', 'stocks_sync_econ', 'stocks_force_init',
        'stocks_clear_history', 'stocks_hub', 'stocks_admin', 'stocks_admin_detail',
        'stocks_admin_peek', 'stocks_admin_debug', 'stocks_overview', 'stocks_etfs',
        'stocks_toggle_admin_trading', 'stocks_add', 'stocks_add_day', 'stocks_set_update_rate',
        'start', 'status', 'stop', 'econ_memory_list', 'econ_memory', 'econ_set_gdp_weights',
        'clear_stock_commands', 'clear_economic_commands', 'clear_bill_commands',
        'channel_restrict'
    ]

# Initialize directories on import
ensure_directories()