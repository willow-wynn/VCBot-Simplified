"""
Simple configuration for VCBot.
Replaces the complex Pydantic configuration system with direct environment variable reading.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Required environment variables
BOT_ID = int(os.getenv("BOT_ID"))
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Optional environment variables
GUILD_ID = int(os.getenv("GUILD", 0)) if os.getenv("GUILD") else None

# Channel IDs
RECORDS_CHANNEL = int(os.getenv("RECORDS_CHANNEL", 0))
NEWS_CHANNEL = int(os.getenv("NEWS_CHANNEL", 0))
SIGN_CHANNEL = int(os.getenv("SIGN_CHANNEL", 0))
CLERK_CHANNEL = int(os.getenv("CLERK_CHANNEL", 0))
MAIN_CHAT_CHANNEL = 654467992272371712
BOT_HELPER_CHANNEL = 1327483297202176080
CLERK_ANNOUNCE_CHANNEL = 1037456401708105780

# File paths
BASE_DIR = Path(__file__).parent
KNOWLEDGE_DIR = BASE_DIR / "Knowledge"
BILL_TEXT_DIR = BASE_DIR / "every-vc-bill" / "txts"
BILL_PDF_DIR = BASE_DIR / "every-vc-bill" / "pdfs"
BILL_JSON_DIR = BASE_DIR / "every-vc-bill" / "json_outputs"
BILL_REFS_FILE = BASE_DIR / "bill_refs.json"
NEWS_FILE = BASE_DIR / "news.txt"
QUERIES_FILE = BASE_DIR / "queries.csv"

# Knowledge files
KNOWLEDGE_FILES = {
    "rules": KNOWLEDGE_DIR / "rules.txt",
    "constitution": KNOWLEDGE_DIR / "constitution.txt", 
    "server_information": KNOWLEDGE_DIR / "rules.txt",
    "house_rules": KNOWLEDGE_DIR / "houserules.txt",
    "senate_rules": KNOWLEDGE_DIR / "senaterules.txt"
}

# Role permissions for /role command
ALLOWED_ROLES_FOR_ROLES = {
    "Speaker of the House": [
        "House Presiding Officer", "House Clerk", "Speaker Pro Tempore",
        "House Majority Leader", "House Minority Leader", "House Hearing Attendee",
        "House Ethics and Oversight Committee", "House Rules Committee",
        "House Judiciary Committee", "House Education and Youth Welfare Committee",
        "House General Legislation Committee"
    ],
    "President": [
        "Attorney General", "Cabinet Member", "US Attorney", "Sub-Cabinet",
        "UN Ambassador", "IPTO Sec. Gen.", "White House Staff",
        "Chief of Staff", "Deputy Chief of Staff", "National Security Council"
    ],
    "Attorney General": ["US Attorney"],
    "Senate President Pro Tempore": [
        "Senate General Welfare Committee", "Senate Judiciary Committee",
        "Senate Relations Committee", "Senate Secretary",
        "Senate Presiding Officer", "Senate Hearing Attendee"
    ],
    "Vice President": [
        "Senate General Welfare Committee", "Senate Judiciary Committee",
        "Senate Relations Committee", "Senate Secretary",
        "Senate Presiding Officer", "Senate Hearing Attendee", "Senate Minority Leader"
    ],
    "Speaker Pro Tempore": [
        "House Ethics and Oversight Committee", "House Rules Committee",
        "House Judiciary Committee", "House Education and Youth Welfare Committee",
        "House General Legislation Committee", "House Presiding Officer", "House Hearing Attendee"
    ],
    "House Majority Leader": [
        "House Ethics and Oversight Committee", "House Rules Committee",
        "House Judiciary Committee", "House Education and Youth Welfare Committee",
        "House General Legislation Committee"
    ],
    "House Minority Leader": [
        "House Ethics and Oversight Committee", "House Rules Committee",
        "House Judiciary Committee", "House Education and Youth Welfare Committee",
        "House General Legislation Committee"
    ],
    "Committee Chair": ["House Hearing Attendee", "Senate Hearing Attendee"],
    "Committee Ranking Member": ["House Hearing Attendee", "Senate Hearing Attendee"]
}

# Role names
class Roles:
    ADMIN = "Admin"
    AI_ACCESS = "AI Access"
    REPRESENTATIVE = "Representative"
    HOUSE_CLERK = "House Clerk"
    MODERATOR = "Moderator"
    EVENTS_TEAM = "Events Team"

# Constants
class Limits:
    MAX_MESSAGES_HISTORY = 50
    MAX_MESSAGE_LENGTH = 1900
    MAX_BILL_SEARCH_RESULTS = 10

class Messages:
    PERMISSION_DENIED_AI_ACCESS = "You do not have permission to use AI commands."
    CHANNEL_RESTRICTED = "This command can only be used in specific channels."