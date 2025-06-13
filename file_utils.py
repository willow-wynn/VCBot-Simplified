"""
Simple file utilities for VCBot.
Replaces the complex FileManager and Repository classes with direct functions.
"""

import json
import csv
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional
from config import BILL_REFS_FILE, QUERIES_FILE

# File paths for channel restrictions
CHANNEL_RESTRICTIONS_FILE = Path(__file__).parent / "channel_restrictions.json"

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
    from config import BILL_TEXT_DIR, BILL_PDF_DIR, BILL_JSON_DIR, KNOWLEDGE_DIR
    
    for directory in [BILL_TEXT_DIR, BILL_PDF_DIR, BILL_JSON_DIR, KNOWLEDGE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

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

def get_available_commands() -> list:
    """Get list of available command names for restriction management."""
    # This list includes all major bot commands
    return [
        'helper', 'bill_keyword_search', 'reference', 'modifyrefs', 'add_bill',
        'econ_impact_report', 'role', 'fetch_econ_data', 'econ_report', 
        'econ_status', 'econ_set_inflation', 'econ_set_interval',
        'stocks_list', 'stocks_price', 'stocks_categories', 'stocks_history_48h',
        'stocks_buy', 'stocks_sell', 'stocks_portfolio', 'stocks_set_market',
        'stocks_force_update', 'stocks_reset', 'stocks_sync_econ', 'stocks_force_init',
        'econ_memory_list', 'econ_memory'
    ]

# Initialize directories on import
ensure_directories()