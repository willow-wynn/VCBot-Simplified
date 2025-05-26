# VCBot - A Discord Bot for Virtual Congress

A simple Discord bot for the Virtual Congress server. Answers questions, searches bills, and tracks bill numbers.

## What It Does

- **AI Helper**: Uses Google Gemini to answer questions about Virtual Congress
- **Bill Search**: Finds bills using keyword search through titles and content
- **Reference Tracking**: Keeps track of bill numbers (HR 123, S 456, etc.)
- **Economic Impact Reports**: Generates detailed economic analysis for bills
- **Bill Management**: Adds new bills to the corpus with PDF handling

## The Great Simplification

This bot went through a major architectural refactor. What started as an over-engineered hobby project with service layers, repository patterns, and dependency injection has been simplified into clean, maintainable code.

**Before**: 2000+ lines across 15+ files with complex abstractions
**After**: ~800 lines across 6 core files with simple functions

**Lesson learned**: Keep it simple! Functions are often better than classes for hobby projects.

## Quick Start

### 1. Install Dependencies

```bash
git clone https://github.com/willow-wynn/VCBot.git
cd VCBot
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```env
# Required
BOT_ID=your_bot_user_id_here
DISCORD_TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here

# Channel IDs (get by right-clicking channels in Discord)
RECORDS_CHANNEL=1234567890123456789
NEWS_CHANNEL=1234567890123456789
SIGN_CHANNEL=1234567890123456789
CLERK_CHANNEL=1234567890123456789

# Optional
GUILD=1234567890123456789  # Your server ID for faster command sync
```

### 3. Run the Bot

```bash
python bot.py
```

If successful, you'll see:
```
Logged in as YourBotName#1234
Commands synced: X commands
```

## Commands

### User Commands
- `/helper [question]` - Ask the AI anything about Virtual Congress
- `/bill_keyword_search [query]` - Search for bills by keyword

### Admin Commands
- `/reference [link] [type]` - Reference a new bill (HR, HRES, HJRES, HCONRES)
- `/modifyrefs [number] [type]` - Modify reference numbers
- `/add_bill [link]` - Add a bill from Google Docs to the database
- `/econ_impact_report [bill_link]` - Generate economic impact analysis
- `/role [users] [role]` - Manage user roles (prefix with `-` to remove)

## Architecture

The bot now uses a simplified architecture:

```
bot.py          # Main Discord bot with all commands
├── config.py       # Simple environment configuration
├── ai_tools.py     # Gemini AI integration
├── bill_utils.py   # Bill search and management
├── message_utils.py # Response formatting and Discord messaging
└── file_utils.py   # File operations
```

### Key Features

- **Single Entry Point**: All Discord logic in `bot.py`
- **Simple Functions**: No complex classes or dependency injection
- **Direct Calls**: Functions call other functions directly
- **Environment Config**: Configuration via environment variables
- **Keyword Search**: Fast, reliable bill search through text content

### Example Data Flow

```
User runs /helper command
         ↓
bot.py command handler
         ↓  
ai_tools.process_ai_query()
         ↓
message_utils.send_response()
         ↓
User sees response
```

No service layers, no repositories, no complex routing. Just simple, direct function calls.

## Getting API Keys

### Discord Bot Token
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create application → Bot section → Reset Token
3. Enable "Message Content Intent" under Privileged Gateway Intents
4. Invite to server with Administrator permissions

### Google Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create new API key
3. Free tier has generous limits

### Channel IDs
1. Enable Developer Mode in Discord (User Settings → Advanced)
2. Right-click channels → "Copy ID"

## Bill Management

### Bill Search
The bot searches through:
- Bill titles and metadata (highest relevance)
- Bill text content (lower relevance)
- Author names and cosponsors
- Categories and tags

Results are ranked by relevance and automatically include PDF attachments.

### Adding Bills
Bills are added from Google Docs links:
1. Bot downloads the Google Doc as text
2. Extracts title from content
3. Saves to `every-vc-bill/txts/` directory
4. Creates metadata entry
5. Bill becomes searchable immediately

### Reference Numbers
The bot tracks bill reference numbers (HR 1, S 2, etc.) in a simple JSON file:
```json
{
  "hr": 125,
  "hres": 15,
  "hjres": 3,
  "hconres": 8
}
```

## Directory Structure

```
VCBot/
├── bot.py                    # Main bot file
├── config.py                 # Configuration
├── ai_tools.py               # AI integration
├── bill_utils.py             # Bill operations
├── message_utils.py          # Discord messaging
├── file_utils.py             # File operations
├── .env                      # Your secrets (don't commit!)
├── bill_refs.json            # Bill reference numbers
├── queries.csv               # Query logs
├── Knowledge/                # Knowledge base files
│   ├── constitution.txt
│   ├── rules.txt
│   ├── houserules.txt
│   └── senaterules.txt
├── every-vc-bill/           # Bill storage
│   ├── txts/               # Bill text files
│   ├── pdfs/               # Bill PDF files
│   └── json_outputs/       # Bill metadata
├── docs/                   # Documentation
├── tests/                  # Test suite (131 tests!)
└── logs/                   # Application logs
```

## AI Tools

The bot provides these tools to Gemini:

1. **call_knowledge** - Access knowledge base files (constitution, rules, etc.)
2. **call_other_channel_context** - Get recent messages from other Discord channels
3. **call_bill_search** - Search bills and return titles (PDFs auto-attached)

Tools are defined as simple JSON objects and executed via direct function calls.

## Deployment

### Production (systemd)
```bash
sudo systemctl enable vcbot
sudo systemctl start vcbot
```

### Development
```bash
LOG_LEVEL=DEBUG python bot.py
```

### Docker
```bash
docker build -t vcbot .
docker run -d --env-file .env vcbot
```

## Testing

Run the test suite:
```bash
python tests/run_all_tests.py
```

- **131 total tests** (8 skipped due to Discord.py testing limitations)
- **Unit tests** for individual components
- **Integration tests** for component interaction
- **Production tests** that mimic real usage scenarios

## Troubleshooting

### Bot Won't Start
- Check `.env` file has all required variables
- Verify Discord token hasn't expired
- Ensure bot has proper Discord permissions

### Commands Not Working
- Enable Message Content Intent in Discord Developer Portal
- Check bot role hierarchy in Discord server
- Set `GUILD` environment variable for faster command sync

### AI Responses Failing
- Verify Gemini API key is valid
- Check API quota usage
- Look for rate limiting in logs

## What Changed in the Refactor?

### Removed
- ❌ Service layer pattern with dependency injection
- ❌ Repository pattern for simple file operations  
- ❌ Complex BotState dataclass management
- ❌ Over-engineered MessageRouter system
- ❌ Tool registry with decorators and validation
- ❌ Nested Pydantic configuration models
- ❌ Custom exception hierarchy

### Added
- ✅ Single `bot.py` file with all Discord logic
- ✅ Simple utility modules with clear purposes
- ✅ Direct function calls instead of abstractions
- ✅ Environment variable configuration
- ✅ Global variables for simple state management
- ✅ Backward compatibility layers for existing tests

## Performance Benefits

The simplified architecture provides:
- **Faster startup** (no complex initialization)
- **Lower memory usage** (no service layer overhead)
- **Simpler debugging** (linear code flow)
- **Easier maintenance** (fewer files, less abstraction)

## Future Plans

Potential improvements:
- Enhanced fuzzy search for bills
- Better mobile response formatting
- PostgreSQL migration (when the JSON files get too big)
- Additional AI tools for congressional research

But the goal is to **keep it simple**. This bot proves that you don't need complex architectures for hobby projects.

## Credits

- **Original Creator**: Lucas Posting
- **Major Refactor**: Claude (Anthropic's AI assistant)
- **Inspiration**: The Virtual Congress Discord community

## License

MIT - Use it however you want.

---

*A hobby project that went from over-engineered to just right. Sometimes less really is more.*