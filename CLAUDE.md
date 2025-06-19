# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
- Run all tests: `pytest`
- Run specific test file: `pytest test_ai_price_preservation.py`
- Stock market testing: `python test_ai_price_preservation.py`

### Environment Management
- Start production: `./start_prod.sh`
- Start test environment: `./start_test.sh` (switches to .env.test)
- Main bot entry: `python bot.py`

### Data Management
- Economic data stored in JSON files under `economic_data/`
- Stock data in `stock_data/market_data.json` and `stock_history.json`
- User portfolios in guild-specific directories: `data/{guild_id}/portfolios/`

## Architecture Overview

VCBot is a sophisticated Discord bot implementing a complete government economic simulation with:

### Core Components
1. **AI Tools System** (`ai_tools.py`) - Gemini 2.0 Flash integration with 5 specialized tools for knowledge base, Discord context, bill search, document fetching, and economic data
2. **Economic Engine** (`economic_engine.py`) - Agentic hourly economic analysis generating GDP, inflation, unemployment, and sentiment indicators
3. **Stock Market** (`stock_market.py`) - Real 24-company stock simulation across 8 sectors with AI-driven daily analysis and Perlin noise price movements
4. **Stock Trading** (`stock_trading.py`) - UnbelievaBoat API integration for real Discord economy trading
5. **Legislative System** (`bill_utils.py`) - Congressional bill processing with Google Docs integration and PDF corpus management
6. **Data Managers** (`data_managers.py`) - Centralized data access layer preventing inconsistencies

### Key Data Flow
- Discord activity → Economic analysis → Stock market impacts → Trading opportunities
- Bill submissions → PDF corpus → Economic impact analysis → Market adjustments
- Bills-signed-into-law channel → Automatic processing with AI-generated titles → Interactive callbacks
- All systems use centralized data managers for consistency

### Integration Points
- **UnbelievaBoat**: Real Discord server economy for trading
- **Google Docs**: Bill text extraction and processing
- **Gemini AI**: Economic analysis and stock market intelligence
- **MCP Server**: Claude Desktop integration in `claude/` directory

### Testing Architecture
- Comprehensive stock market testing with multi-scenario validation
- Test environment isolation with separate configuration
- Automated test suite for price preservation and market accuracy

### Configuration
- Environment-based config via `config.py` and `.env` files
- Guild-specific data directories under `data/{guild_id}/`
- Channel restrictions and role-based permissions
- Production/test environment switching capabilities

## Important Notes
- Stock market uses 24 real companies across 8 economic sectors
- Economic analysis runs hourly with AI-generated insights
- All trading uses real Discord server economy balances
- Bill corpus maintains full-text search capabilities
- Data persistence through JSON files with automated backups

## New Features (Latest Implementation)
- **Automatic Bill Processing**: Bills-signed-into-law channel (655065748984561676) automatically processes Google Docs links
- **AI-Generated Titles**: Gemini 2.0 Flash generates professional titles for all new bills
- **Interactive Callbacks**: Success/error messages include buttons for immediate search and content viewing
- **Enhanced Bill Search Tool**: AI can now access full bill content by filename using `get_bill_content` tool
- **Retry Functionality**: Failed bill processing includes retry buttons with user-specific permissions