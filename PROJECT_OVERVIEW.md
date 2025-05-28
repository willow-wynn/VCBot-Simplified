# VCBot - Virtual Congress Discord Bot

A comprehensive Discord bot for the Virtual Congress server providing AI assistance, bill search, economic analysis, and stock market simulation.

## Core Features

### 🤖 AI Assistant
- **Intelligent Help**: Uses Google Gemini 2.5 to answer questions about Virtual Congress
- **Contextual Responses**: Accesses knowledge base and recent Discord activity
- **Bill Analysis**: Detailed analysis of legislation and policy impacts

### 📊 Economic Analysis System
- **AI-Powered Analysis**: Daily comprehensive economic analysis using Discord activity
- **Real Economic Indicators**: GDP, inflation, unemployment, market sentiment tracking
- **Professional Reports**: Clean, professional economic overview reports
- **Memory System**: Persistent memory for important economic context
- **Channel-Restricted Access**: Analyzes only authorized government channels (38 whitelisted)

### 📈 Stock Market Simulation
- **19 Individual Stocks**: Across 6 government sectors (NEWS, CONGRESS, EXECUTIVE, STATES, COURTS, PUBLIC_SQUARE)
- **AI-Driven Daily Analysis**: Sets market parameters based on Discord server activity
- **Realistic Price Movements**: Perlin noise generation with volatility modeling
- **Automated Trading**: 9 AM - 5 PM ET daily with hourly updates
- **Visual Charts**: Matplotlib-generated price charts embedded in Discord
- **ETF-Style Categories**: Sector tracking with individual stock composition

### 🔍 Bill Management
- **Keyword Search**: Intelligent bill search through titles and content
- **Reference Tracking**: Automated bill numbering system (HR, S, etc.)
- **PDF Processing**: Handles bill documents with full-text search
- **Corpus Management**: Add/remove bills from searchable database

## Architecture

VCBot uses a **simplified functional architecture** designed for maintainability:

- **Functions over Classes**: Simple functions instead of complex hierarchies
- **Direct Calls**: No dependency injection or service layers
- **Single Responsibility**: Each file has a clear, focused purpose
- **Professional Quality**: Enterprise-grade features with hobby-project simplicity

### Core Files
- `bot.py` - Main Discord bot with commands and message handling
- `economic_utils.py` - Economic analysis system with AI integration
- `stock_market.py` - Complete stock market simulation engine
- `bill_utils.py` - Bill search and management
- `ai_tools.py` - Gemini AI integration and tools
- `config.py` - Environment configuration

## Security & Access Control

### Channel Restrictions
Economic and stock analysis systems have restricted access to authorized channels only:
- **38 Whitelisted Channels** across government categories
- **Categorized by Function**: NEWS, CONGRESS, EXECUTIVE, STATES, COURTS, PUBLIC_SQUARE
- **Access Denied**: Non-whitelisted channels return permission errors
- **Audit Trail**: All access attempts logged

### Role-Based Commands
- **Admin Only**: System configuration, parameter modification, memory management
- **AI Access**: Economic reports, stock market overview, bill search
- **Public**: Basic help and information commands

## Data Storage

### Economic System
```
economic_data/
├── reports.json         # Public economic reports (no internal insights)
├── internal_insights.txt # AI insights for next iteration (private)
├── memory_entries.json  # Admin-managed persistent memory
├── parameters.json      # Economic simulation parameters
└── analysis_logs/       # Detailed AI analysis logs
```

### Stock Market
```
stock_data/
├── market_data.json     # Current market state and prices
├── stock_history.json   # Complete historical data
└── daily_analysis.json  # AI market analysis with reasoning
```

## Professional Standards

### Economic Reporting
- **No Internal Insights**: Public reports exclude AI reasoning and internal analysis
- **Professional Presentation**: Clean, government-style economic summaries
- **Realistic Metrics**: GDP in trillions, realistic inflation/unemployment rates
- **Confidential Markings**: Professional report formatting

### AI Analysis
- **Memory Continuity**: Previous insights inform future analysis
- **Context Preservation**: Important economic context persists across sessions
- **Channel-Focused**: Only analyzes relevant government communications
- **Rate-Limited**: Proper API management with exponential backoff

## Commands Overview

### Economic System
- `/fetch_econ_data` - Trigger comprehensive economic analysis
- `/econ_report` - Generate professional economic overview
- `/econ_memory_list` - View memory entries (Admin/RP Events Team)
- `/econ_memory add/remove` - Manage memory entries (Admin/RP Events Team)

### Stock Market
- `/stocks` - Market overview with parameters and ETF prices
- `/stocks_sector [sector]` - Detailed sector analysis
- `/stocks_stock [symbol]` - Individual stock with charts
- `/stocks_history` - Historical performance data

### Bill Management
- `/bill_keyword_search [query]` - Search bills with PDF attachments
- `/reference [link] [type]` - Assign bill reference numbers
- `/add_bill [link]` - Add new bills to corpus

### General
- `/helper [query]` - AI assistance with context awareness
- `/role [users] [role]` - Role management (Admin)

## Technical Implementation

### AI Integration
- **Gemini 2.5 Flash**: Primary AI model for all analysis
- **Tool-Based Architecture**: Proper function calling with structured tools
- **Agentic Analysis**: Multi-turn AI conversations with comprehensive channel analysis
- **Context Management**: Previous insights and memory inform new analysis

### Real-Time Features
- **Daily Market Prep**: 8:40 AM ET daily analysis and parameter setting
- **Hourly Updates**: Trading hours price updates with Discord embeds
- **Live Charts**: Dynamic price chart generation and display
- **Background Tasks**: Automated scheduling with error handling

### Integration Points
- **Economic ↔ Stock**: Economic data initializes stock market parameters
- **Memory System**: Persistent context for economic analysis continuity
- **Channel Restrictions**: Unified whitelist across both systems
- **Professional Reporting**: Clean separation of internal/external data

---

VCBot demonstrates that sophisticated features can be implemented with clean, maintainable code. The system provides enterprise-grade functionality while maintaining the simplicity and transparency of a well-designed hobby project.