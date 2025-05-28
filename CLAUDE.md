# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

VCBot is a Discord bot for Virtual Congress that has been **dramatically simplified** from an over-engineered hobby project into clean, maintainable code. The bot provides AI assistance, bill search, reference management, and a comprehensive **real-world stock market simulation** using a straightforward functional architecture.

## Development Commands

### Testing
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest test_economic_core.py
python -m pytest test_economic_system.py

# Run tests with verbose output
python -m pytest -v

# Run tests with coverage (if needed)
python -m pytest --cov=.
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
- **`economic_utils.py`** - Economic analysis system with AI-powered insights from Discord activity
- **`economic_engine.py`** - Core economic data processing and analysis engine  
- **`economic_admin.py`** - Administrative controls for economic system management
- **`bot_economic_integration.py`** - Integration layer between Discord bot and economic systems

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

#### Stock Market Commands (Real-World Stocks)
- `/stocks_list`: View all 24 real stocks across 8 sectors (AAPL, MSFT, GOOGL, JPM, XOM, etc.)
- `/stocks_price [symbol]`: Get current price and detailed info for individual stock
- `/stocks_categories`: View all economic sectors and their stock composition
- `/stocks_history_48h [symbol]`: View 48-hour price history with charts
- `/stocks_set_market [param] [value]`: Set market parameters (Admin only)
- `/stocks_force_update`: Force immediate market analysis update (Admin only)
- `/stocks_reset`: Reset market to default state (Admin only)
- `/stocks_stop_updates`: Stop automatic market updates (Admin only)
- `/stocks_sync_econ`: Sync market parameters with economic data (Admin only)
- `/stocks_force_init`: Force re-initialization of stock market system (Admin only)
- `/stocks_add [sector] [symbol] [name] [price] [industry]`: Add new stock to market (Admin only)

#### UnbelievaBoat Trading Commands (Real Money Integration)
- `/stocks_buy [symbol] [quantity]`: Buy stocks using UnbelievaBoat balance
- `/stocks_sell [symbol] [quantity]`: Sell stocks to UnbelievaBoat balance  
- `/stocks_portfolio [user]`: View stock portfolio and total net worth with UnbelievaBoat balance

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
4. For economic/stock features: read from data files, never hardcode values
5. Keep it simple - avoid creating new abstractions

### Adding New Economic Features
1. Update appropriate data file in `economic_data/` or `stock_data/`
2. Add function to read and process the data dynamically
3. Ensure parameters are calculated from actual data
4. Test with different economic scenarios to verify dynamic calculation

### Adding New Functions
1. Add function to the appropriate utility module
2. Import directly where needed
3. Use simple parameters, avoid complex data structures
4. Return simple data types (dicts, lists, strings)
5. **Never hardcode economic values** - always read from files

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

The codebase maintains focused unit tests:
- `test_economic_core.py` - Core economic functionality and data validation
- `test_economic_system.py` - Economic system integration tests
- Tests focus on actual functionality, not architecture
- Economic tests verify dynamic parameter calculations
- Keep tests simple and focused on critical business logic

## Deployment Notes

- Main entry point is now `bot.py` (not `main.py`)
- Uses simple environment variable configuration
- Logging with rotation in `logs/` directory
- No complex dependency injection or service initialization

## Economic Analysis System

VCBot includes a sophisticated economic analysis system that transforms Discord server activity into economic indicators:

### Core Features
- **AI-Powered Analysis**: Uses Gemini 2.5 for intelligent economic insights
- **Restricted Channel Access**: Analyzes only authorized government and news channels (38 whitelisted channels)
- **Document Integration**: Processes Google Docs links for policy analysis
- **Virtual Stock Market**: Tracks 6 government sector stocks (GOV, DEF, EDU, HLT, INF, BIP)
- **Economic Indicators**: GDP, inflation, unemployment, market sentiment

### Channel Access Restrictions
The economic analysis system has **restricted access** to only authorized channels for security and relevance:

#### Allowed Channel Categories (38 total channels):
- **NEWS** (9 channels): news-information, official-rp-news, parody, pbn, liberty-ledger, wall-street-journal, 4e-news-from-the-hill, 202news, msnbc
- **CONGRESS** (9 channels): speaker-announcements, house-docket, house-floor, house-vote-results, senate-announcements, senate-docket, senate-floor, senate-vote-results, committee-announcements  
- **EXECUTIVE** (8 channels): bills-signed-into-law, bills-vetoed, presidential-congressional-desk, president-announcements, press-briefing-room, cabinet-announcements, executive-orders, presidential-memoranda
- **STATES** (5 channels): olympia-governor, pacifica-governor, lincoln-governor, jackson-governor, frontier-governor
- **COURTS** (2 channels): district-court-announcements, supreme-court-announcements
- **PUBLIC_SQUARE** (5 channels): rp-chat, twitter-rp, press-releases, press-room, election-announcements

#### Security Features:
- Channel whitelist enforced in `economic_utils.py` and `economic_engine.py`
- Unauthorized channels return access denied errors
- Channel restrictions logged for audit purposes
- Easy to modify whitelist by updating `ALLOWED_CHANNELS` configuration

### Data Storage
```
economic_data/
├── parameters.json      # Economic simulation parameters (8.51% inflation base)
├── reports.json         # Comprehensive analysis reports
├── gdp.json            # GDP data ($26.8T, -1.2% growth)
├── inflation.json      # Inflation data (8.51% YoY, 4.00% fed rate)
├── unemployment.json   # Unemployment data (3.2% rate, tight market)
├── sentiment.json      # Market sentiment (35% confidence, 78% anxiety)
└── admin_log.json      # Administrative action log

stock_data/
├── market_data.json        # Real stock prices and market state
├── stock_history.json      # Historical price movements
├── daily_analysis.json     # AI analysis results with reasoning
└── market_params.json      # Current calculated parameters
```

### Key Functions (in `economic_utils.py`)
- `start_economic_engine(client)` - Initialize the analysis system
- `fetch_econ_data_manually(client)` - Trigger manual analysis
- `get_fresh_economic_report()` - Retrieve current economic data from individual files
- `get_economic_data(type, days_back)` - Retrieve historical data
- `set_economic_parameter(param, value)` - Admin parameter control
- `is_channel_allowed(channel_name)` - Check if channel is authorized for analysis
- `get_channel_category(channel_name)` - Get economic category of allowed channel

### Key Functions (in `stock_market.py`)
- `StockMarket._calculate_market_params_from_economic_data()` - Calculate parameters from economic files
- `StockMarket.get_stock_price(symbol)` - Get current stock price
- `StockMarket.generate_stock_chart(symbol)` - Create price chart for Discord
- `get_stock_market()` - Get singleton stock market instance
- `initialize_stock_market(client)` - Initialize with Discord integration

### Integration Notes
- Economic system starts automatically when bot initializes
- Stock market system dynamically calculates parameters from economic data
- Real economic environment (8.51% inflation) drives bearish market conditions
- No hardcoded values - all parameters calculated from data files
- Admin commands allow real-time economic parameter steering
- Stock market reflects economic crisis with high volatility and negative sentiment

### Testing
- Core functionality tested with `test_economic_core.py`
- Channel restrictions verified with `test_channel_restrictions.py`
- Google Docs integration verified with test document
- All economic calculations validated
- Channel access controls ensure only authorized channels are processed

## Real-World Stock Market System

VCBot includes a sophisticated real-world stock market simulation that provides realistic trading with AI-driven analysis based on current economic conditions:

### Core Features
- **Real Stock Universe**: 24 major stocks from actual companies (AAPL, MSFT, GOOGL, JPM, XOM, etc.)
- **Dynamic Economic Integration**: Market parameters calculated from real economic data (8.51% inflation environment)
- **AI-Powered Analysis**: Uses Gemini 2.5 to analyze economic conditions and adjust market behavior
- **Realistic Price Movements**: Perlin noise generation with economic parameter influence
- **Crisis Environment Modeling**: Currently reflects high inflation (8.51% YoY) and bearish market conditions
- **Visual Chart Generation**: Matplotlib-powered price charts with Discord embeds

### Stock Universe
**24 Real Stocks** across 8 economic sectors:

#### Sector Structure:
- **ENERGY** (3 stocks): XOM (ExxonMobil), CVX (Chevron), SLB (Schlumberger)
- **TECH** (4 stocks): AAPL (Apple), MSFT (Microsoft), GOOGL (Alphabet), NVDA (NVIDIA)
- **FINANCE** (3 stocks): JPM (JPMorgan), BAC (Bank of America), WFC (Wells Fargo)
- **HEALTH** (3 stocks): JNJ (Johnson & Johnson), PFE (Pfizer), UNH (UnitedHealth)
- **RETAIL** (3 stocks): WMT (Walmart), TGT (Target), COST (Costco)
- **MANUFACTURING** (3 stocks): CAT (Caterpillar), GE (General Electric), MMM (3M)
- **ENTERTAINMENT** (3 stocks): DIS (Disney), NFLX (Netflix), CMCSA (Comcast)
- **TRANSPORT** (2 stocks): BA (Boeing), UPS (United Parcel Service)

### Market Parameters (Dynamically Calculated from Economic Data)
- **trend_direction** (-1 to 1): Currently -0.35 (bearish due to 8.51% inflation)
- **volatility** (0 to 1): Currently 0.80 (very high due to inflation crisis)
- **momentum** (0 to 1): Currently 0.25 (weak due to economic uncertainty)
- **market_sentiment** (0 to 1): Currently 0.35 (matches 35% market confidence)
- **long_term_outlook** (0 to 1): Currently 0.40 (pessimistic due to policy uncertainty)

### Economic Data Integration
Market parameters are **dynamically calculated** from real economic data files:
- **Inflation Rate**: 8.51% YoY (triggers high volatility, bearish trend)
- **Market Confidence**: 35% (drives low sentiment parameter)
- **GDP Growth**: -1.2% quarterly (influences negative trend direction)
- **Federal Funds Rate**: 4.00% (restrictive monetary policy impact)
- **Unemployment**: 3.2% (tight labor market contributing to inflation pressure)

### Market Operation
- **Continuous Operation**: Market runs 24/7 with hourly parameter updates
- **Economic Data Sync**: Parameters recalculated when economic data changes
- **Real-Time Analysis**: Instant parameter adjustment based on economic indicators
- **Crisis Mode**: Currently operating in high inflation crisis mode
  - Bearish trend direction (-0.35)
  - Very high volatility (0.80)
  - Low market confidence (0.35)
- **Manual Override**: Admin commands allow temporary parameter adjustment

### Data Storage
```
stock_data/
├── market_data.json        # Current market state and stock prices
├── stock_history.json      # Complete historical price data
├── daily_analysis.json     # AI analysis results with reasoning
└── (charts generated dynamically for Discord)
```

### Key Functions (in `stock_market.py`)
- `initialize_stock_market(client)` - Initialize system with Discord integration
- `StockMarket.get_daily_market_analysis()` - AI-powered market parameter setting
- `StockMarket.generate_hourly_prices()` - Perlin noise price generation
- `StockMarket.generate_stock_chart()` - Matplotlib chart creation
- `StockMarketScheduler` - Automated trading day management

### Integration with Economic System
- Stock market **dynamically calculates** parameters from real economic data
- Economic indicators directly influence market behavior:
  - 8.51% inflation → bearish trend direction (-0.35)
  - High inflation anxiety (78%) → very high volatility (0.80)
  - Low market confidence (35%) → low sentiment parameter (0.35)
  - Negative GDP growth (-1.2%) → reduced momentum (0.25)
- Real-time parameter recalculation when economic data updates

### Visual Features
- **Real-time Charts**: Matplotlib-generated price charts embedded in Discord
- **Market Overview Embeds**: Comprehensive market status with emojis and formatting
- **Sector Performance**: ETF-like category tracking with individual stock composition
- **Historical Analysis**: Multi-day performance tracking with statistical summaries

### Security & Administration
- Admin-only commands for stock management and parameter control
- Economic data drives market behavior (no hardcoded values)
- Parameter sync commands to ensure consistency with economic analysis
- Complete audit trail of all market actions and economic calculations
- Force initialization and reset commands for troubleshooting

## UnbelievaBoat Trading Integration

VCBot integrates with UnbelievaBoat to provide real money trading with Discord economy balances:

### Core Features
- **Real Balance Integration**: Uses UnbelievaBoat API to check and modify user balances
- **Portfolio Tracking**: JSON-based portfolio storage with detailed stock ownership
- **Transaction Processing**: Atomic buy/sell operations with rollback on failure
- **Comprehensive Portfolio View**: Shows cash balance, stock value, and total net worth

### Trading System Files
- **`stock_trading.py`** - Core trading system with UnbelievaBoat API integration
- **`stock_commands.py`** - Discord commands for buy/sell/portfolio operations
- **`stock_data/user_portfolios.json`** - Portfolio storage (auto-created)

### Key Functions (in `stock_trading.py`)
- `StockTradingSystem.buy_stock()` - Process stock purchases with balance validation
- `StockTradingSystem.sell_stock()` - Process stock sales with ownership validation
- `StockTradingSystem.get_portfolio_value()` - Calculate total portfolio value
- `get_stock_trading_system()` - Get singleton trading system instance

### Environment Variables Required
```bash
UNBELIEVABOAT_API_KEY=your_unbelievaboat_api_key
GUILD_ID=your_discord_server_id
```

### Trading Commands
- **`/stocks_buy [symbol] [quantity]`** - Buy stocks using UnbelievaBoat cash balance
- **`/stocks_sell [symbol] [quantity]`** - Sell stocks to UnbelievaBoat cash balance
- **`/stocks_portfolio [user]`** - View portfolio with cash and stock value breakdown

### Integration Benefits
- **Real Discord Economy**: Users trade with actual UnbelievaBoat balances
- **Cross-Bot Compatibility**: Works with existing UnbelievaBoat economy features
- **Risk Management**: Maximum 1000 shares per transaction, balance validation
- **Portfolio Analytics**: Real-time profit/loss calculations and sector breakdowns

## Important Principles

### 1. Resist Over-Engineering
This refactor proves that **simple is better**. The real-world stock market system demonstrates:
- Complex economic modeling with simple function-based architecture
- Dynamic parameter calculation without complex abstractions
- Real economic data integration through straightforward file reading
- Functions are often better than classes for hobby projects

### 2. Prefer Explicitness
- Direct function calls over dynamic dispatch
- Simple if/elif over complex routing systems
- Environment variables over configuration objects
- **Dynamic data reading over hardcoded values** (key principle)
- Real economic data files drive all market parameters

### 3. Keep It Maintainable
- All Discord logic in one file (`bot.py`)
- Economic integration through simple function calls
- Stock market parameters calculated from actual data
- Clear module boundaries with focused responsibilities
- No hardcoded economic values - everything reads from JSON files

---

**Remember**: This codebase demonstrates that you can have sophisticated economic modeling and real-world stock market simulation without complex architectures. The real-world stock market system with dynamic parameter calculation proves that **simple functions can handle complex requirements**.

### Key Success Factors:
1. **Dynamic Data Reading**: All economic parameters calculated from real data files
2. **Simple Integration**: Economic data drives stock market through straightforward function calls
3. **No Hardcoded Values**: Economic environment (8.51% inflation) reflected through data, not code
4. **Maintainable Complexity**: Complex economic modeling with simple, readable code

When in doubt, choose the simpler solution. Functions are your friend!

---

## CRITICAL: Stock Market & Economic System Integration

**⚠️ IMPORTANT INTEGRATION RULE: When modifying economic OR stock market code, you MUST consider both systems together. They are deeply integrated, NOT separate modules.**

### Integration Architecture

The economic system and stock market are interconnected:
- **Economic indicators** (inflation, GDP, unemployment) drive **stock market parameters**
- **Stock market behavior** reflects **economic conditions** in real-time
- **All changes** to either system require **coordination** across multiple files

### Files That Must Be Updated Together

When making ANY changes to economic or stock market functionality, check ALL of these files:

#### Core Integration Files:
1. **`stock_market.py`** - Real stock universe (24 stocks across 8 sectors)
2. **`economic_utils.py`** - Economic data processing and analysis
3. **`economic_engine.py`** - Economic data collection and processing engine
4. **`economic_admin.py`** - Admin controls for economic parameters
5. **`stock_commands.py`** - Discord commands for stock market management
6. **`stock_trading.py`** - UnbelievaBoat integration for stock trading

#### Integration Points:
- `StockMarket._calculate_market_params_from_economic_data()` - **Critical integration function**
- Economic data files in `economic_data/` drive stock market parameters
- Stock market parameters: `trend_direction`, `volatility`, `momentum`, `market_sentiment`, `long_term_outlook`

### Real Stock Universe (DO NOT USE FAKE STOCKS)

**❌ NEVER use these fake stocks:** GOV, DEF, EDU, HLT, BIP
**✅ ALWAYS use real stocks from these sectors:**

- **ENERGY**: XOM, CVX, COP
- **TECH**: AAPL, MSFT, GOOGL, NVDA  
- **FINANCE**: JPM, BAC, V, GS
- **HEALTH**: JNJ, UNH, PFE
- **RETAIL**: WMT, COST, HD
- **MANUFACTURING**: CAT, GE, LMT
- **ENTERTAINMENT**: NFLX, DIS, EA
- **TRANSPORT**: BA

### Integration Checklist

Before making ANY economic or stock market changes:

1. **Review Current Integration**:
   - Check `stock_market.py:_calculate_market_params_from_economic_data()`
   - Verify economic data files in `economic_data/` are current
   - Ensure no fake stock references exist

2. **When Modifying Economic Parameters**:
   - Update economic data files (inflation.json, gdp.json, etc.)
   - Trigger stock market parameter recalculation
   - Test that stock market reflects economic changes
   - Verify UnbelievaBoat trading uses current prices

3. **When Modifying Stock Market**:
   - Ensure prices come from economic-driven calculations
   - Never hardcode stock market parameters
   - Update both real-time and historical data
   - Test economic scenario integration

4. **When Adding New Features**:
   - Design with integration in mind from start
   - Use existing integration patterns
   - Test cross-system functionality
   - Document integration points

### Common Integration Errors to Avoid

1. **Treating systems as separate** - They are ONE integrated economic simulation
2. **Using fake stocks** - Only real companies from stock_market.py
3. **Hardcoding parameters** - Always read from economic data files
4. **Forgetting coordination** - Changes to one system affect the other
5. **Inconsistent data sources** - Economic data must drive market behavior

### Testing Integration

Always test these integration points:
- Economic parameter changes → Stock market parameter updates
- Stock price movements reflect current economic conditions
- UnbelievaBoat trading uses correct current prices
- Admin commands affect both systems appropriately
- Real stocks only (no fake GOV/DEF/EDU/HLT/BIP references)

### File Search Commands for Integration

When working on integration, use these searches:
```bash
# Find any fake stock references
grep -r "GOV\|DEF\|EDU\|HLT\|BIP" . --include="*.py"

# Find economic parameter usage
grep -r "inflation\|gdp\|unemployment" . --include="*.py"

# Find stock market parameter calculations
grep -r "market_params\|volatility\|trend_direction" . --include="*.py"
```

**Remember: The economic system and stock market are ONE integrated simulation. Never treat them as separate systems!**