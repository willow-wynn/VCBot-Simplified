# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

VCBot is a Discord bot for Virtual Congress that has been **dramatically simplified** from an over-engineered hobby project into clean, maintainable code. The bot provides AI assistance, bill search, and reference management using a straightforward functional architecture.

## Development Commands

### Testing
```bash
# Note: Test suite was removed during The Great Simplification
# The old over-engineered architecture had 131 tests
# New simplified code is straightforward enough to not need extensive testing
```

### Running the Bot
```bash
# Development
python bot.py

# With debug logging
LOG_LEVEL=DEBUG python bot.py
```

### Dependencies
```bash
# Install/update dependencies
pip install -r requirements.txt
```

## Simplified Architecture

The codebase now uses a **simple functional architecture** instead of complex service/repository patterns:

### Core Files
- **`bot.py`** - Main Discord bot with all commands and message handling
- **`config.py`** - Simple environment variable configuration
- **`ai_tools.py`** - Gemini AI integration and tool functions
- **`bill_utils.py`** - Bill search and management functions
- **`message_utils.py`** - Discord response formatting and messaging
- **`file_utils.py`** - File I/O operations
- **`economic_utils.py`** - Economic analysis system with AI-powered insights

### Key Principles
1. **Functions over classes** - Simple functions instead of complex class hierarchies
2. **Direct calls** - Functions call other functions directly, no dependency injection
3. **Single responsibility** - Each file has a clear, focused purpose
4. **No abstractions** - Code does what it looks like it does
5. **Global state** - Simple global variables instead of complex state management

## Configuration System

### Environment Variables (.env file)
Required:
- `BOT_ID`: Discord bot user ID
- `DISCORD_TOKEN`: Discord bot token
- `GEMINI_API_KEY`: Google Gemini API key

Channel IDs:
- `RECORDS_CHANNEL`, `NEWS_CHANNEL`, `SIGN_CHANNEL`, `CLERK_CHANNEL`

Optional:
- `GUILD`: Server ID for faster command sync
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR

### Configuration Access
All configuration is accessed via direct imports from `config.py`:
```python
from config import BOT_ID, DISCORD_TOKEN, GEMINI_API_KEY
from config import BILL_TEXT_DIR, BILL_PDF_DIR, KNOWLEDGE_FILES
```

## Discord Integration

### Commands (All in `bot.py`)
- `/helper [query]`: AI assistance with context awareness
- `/bill_keyword_search [query]`: Bill search with PDF attachments
- `/reference [link] [type]`: Bill reference assignment
- `/modifyrefs [number] [type]`: Reference number modification
- `/add_bill [link]`: Add bills to corpus
- `/econ_impact_report [bill_link]`: Generate economic analysis
- `/role [users] [role]`: Role management

#### Economic Analysis Commands
- `/fetch_econ_data`: Trigger comprehensive economic data collection
- `/econ_report`: Generate current economic overview
- `/econ_status`: View economic system status (Admin only)
- `/econ_set_inflation [rate]`: Set inflation rate (Admin only)
- `/econ_set_interval [minutes]`: Set analysis frequency (Admin only)

### Message Handling (Simple if/elif in `bot.py`)
```python
async def handle_message(message):
    if message.author.bot:
        return
    
    if message.channel.id == CLERK_CHANNEL:
        await handle_clerk_message(message)
    elif message.channel.id == NEWS_CHANNEL:
        await handle_news_message(message)
    elif message.channel.id == SIGN_CHANNEL and "docs.google.com" in message.content:
        await handle_sign_message(message)
```

### Permissions
Role-based access control using simple decorators:
```python
@has_any_role(Roles.ADMIN, Roles.AI_ACCESS)
@limit_to_channels([BOT_HELPER_CHANNEL])
```

## AI Integration

### Tool System (Simple JSON + Functions)
Tools are defined as simple JSON objects in `ai_tools.py`:
```python
GEMINI_TOOLS = [
    {
        "name": "call_knowledge",
        "description": "calls knowledge base files",
        "parameters": {...}
    }
]
```

Tool execution uses simple if/elif dispatch:
```python
async def execute_tool(function_call, discord_client=None):
    if function_call.name == "call_knowledge":
        return call_knowledge(args.get("file_to_call"))
    elif function_call.name == "call_bill_search":
        return call_bill_search(args.get("query"), args.get("top_k"))
```

### Available Tools
- `call_knowledge`: Access knowledge base files
- `call_other_channel_context`: Fetch Discord channel history
- `call_bill_search`: Search bills with keyword matching

## File Management

### Simple File Operations (file_utils.py)
```python
# Global variables for simple state
_bill_refs = None

def load_bill_references():
    global _bill_refs
    if _bill_refs is None:
        with open(BILL_REFS_FILE, 'r') as f:
            _bill_refs = json.load(f)
    return _bill_refs

def save_bill_references():
    global _bill_refs
    with open(BILL_REFS_FILE, 'w') as f:
        json.dump(_bill_refs, f, indent=2)
```

### Data Files
- `bill_refs.json`: Bill reference numbers (simple JSON)
- `queries.csv`: Query logging for analytics
- `news.txt`: Recent news for context

### Bill Storage
- Text files in `every-vc-bill/txts/`
- PDF files in `every-vc-bill/pdfs/`
- Metadata in `every-vc-bill/json_outputs/`

## Bill Search System

### Keyword Search (Simple and Reliable)
```python
def search_bills_keyword(query: str, top_k: int = 5):
    results = []
    
    # Search JSON metadata first
    for json_file in BILL_JSON_DIR.glob("*.json"):
        metadata = json.load(open(json_file))
        if query.lower() in metadata.get('title', '').lower():
            results.append({'title': metadata['title'], 'score': 10})
    
    # Search text content if needed
    for txt_file in BILL_TEXT_DIR.glob("*.txt"):
        content = txt_file.read_text()
        if query.lower() in content.lower():
            results.append({'title': txt_file.stem, 'score': 1})
    
    return sorted(results, key=lambda x: x['score'], reverse=True)[:top_k]
```

## Common Development Patterns

### Adding New Commands
1. Add command handler in `bot.py` with proper decorators
2. Add business logic function to appropriate utility module
3. Use existing error handling decorators
4. Keep it simple - avoid creating new abstractions

### Adding New Functions
1. Add function to the appropriate utility module
2. Import directly where needed
3. Use simple parameters, avoid complex data structures
4. Return simple data types (dicts, lists, strings)

### Error Handling
Use the simple `@handle_errors` decorator:
```python
@handle_errors("Failed to process command")
async def my_command(interaction, ...):
    # Command logic here
```

## What Was Removed (The Great Simplification)

### Eliminated Complex Patterns
- ❌ Service layer pattern with dependency injection
- ❌ Repository pattern for simple file operations
- ❌ Complex BotState dataclass with initialization
- ❌ MessageRouter with handlers and conditions
- ❌ Tool registry with decorators and validation
- ❌ Pydantic configuration models
- ❌ Custom exception hierarchy
- ❌ Abstract base classes and interfaces

### Replaced With Simple Alternatives
- ✅ Direct function calls
- ✅ Simple if/elif conditionals
- ✅ Global variables for state
- ✅ Environment variable configuration
- ✅ Plain Python exceptions
- ✅ Concrete functions with clear names

## Backward Compatibility

The refactor maintains compatibility through wrapper files:
- `response_formatter.py` - Wraps `message_utils` functions
- `message_router.py` - Delegates to `bot.py` handlers
- `services/` and `repositories/` - Maintain old interfaces for tests

This allows existing tests to continue working while new code uses the simplified architecture.

## Performance Benefits

The simplified architecture provides:
- **Faster startup** - No complex initialization
- **Lower memory usage** - No service layer overhead  
- **Simpler debugging** - Linear code flow
- **Easier maintenance** - Fewer files, less abstraction

## Code Style Guidelines

1. **Keep functions simple** - One clear purpose per function
2. **Use descriptive names** - Function names should describe what they do
3. **Avoid abstractions** - Don't create classes unless absolutely necessary
4. **Direct imports** - Import what you need from specific modules
5. **Simple data structures** - Use dicts, lists, and basic types
6. **Error handling** - Use existing decorators, don't create new exception types

## Testing Strategy

The codebase maintains 131 unit tests (8 skipped due to Discord.py limitations):
- Tests use compatibility layers to continue working
- Focus on testing actual functionality, not architecture
- Production tests simulate real Discord interactions
- Keep tests simple and focused

## Deployment Notes

- Main entry point is now `bot.py` (not `main.py`)
- Uses simple environment variable configuration
- Logging with rotation in `logs/` directory
- No complex dependency injection or service initialization

## Economic Analysis System

VCBot includes a sophisticated economic analysis system that transforms Discord server activity into economic indicators:

### Core Features
- **AI-Powered Analysis**: Uses Gemini 2.5 for intelligent economic insights
- **Multi-Channel Monitoring**: Analyzes all server channels for governmental activity
- **Document Integration**: Processes Google Docs links for policy analysis
- **Virtual Stock Market**: Tracks 5 government sector stocks (GOV, DEF, EDU, HLT, BIP)
- **Economic Indicators**: GDP, inflation, unemployment, market sentiment

### Data Storage
```
economic_data/
├── parameters.json      # Economic simulation parameters
├── reports.json         # Comprehensive analysis reports
├── gdp.json            # GDP historical data
├── stocks.json         # Stock market data
├── inflation.json      # Inflation metrics
├── unemployment.json   # Unemployment indicators
├── sentiment.json      # Market sentiment data
└── admin_log.json      # Administrative action log
```

### Key Functions (in `economic_utils.py`)
- `start_economic_engine(client)` - Initialize the analysis system
- `fetch_econ_data_manually(client)` - Trigger manual analysis
- `get_economic_data(type, days_back)` - Retrieve historical data
- `set_economic_parameter(param, value)` - Admin parameter control

### Integration Notes
- Economic system starts automatically when bot initializes
- Runs continuous background analysis every hour (configurable)
- Provides new AI tools for economic data access
- Admin commands allow real-time economic parameter steering

### Testing
- Core functionality tested with `test_economic_core.py`
- Google Docs integration verified with test document
- All economic calculations validated

## Important Principles

### 1. Resist Over-Engineering
This refactor proves that **simple is better**. When adding new features:
- Start with the simplest solution that works
- Avoid creating abstractions until you actually need them
- Functions are often better than classes for hobby projects

### 2. Prefer Explicitness
- Direct function calls over dynamic dispatch
- Simple if/elif over complex routing systems
- Environment variables over configuration objects
- Global variables over complex state management

### 3. Keep It Maintainable
- All Discord logic in one file (`bot.py`)
- Clear module boundaries with focused responsibilities
- Minimal dependencies between modules
- Self-contained functions that are easy to understand

---

**Remember**: This codebase demonstrates that you can have full functionality without complex architectures. The goal is to keep it **simple, maintainable, and functional** - not to showcase software engineering patterns.

When in doubt, choose the simpler solution. Functions are your friend!