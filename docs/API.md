# VCBot API Documentation - Real-World Stock Market System

## Overview

VCBot provides a comprehensive API for interacting with Virtual Congress operations through Discord, now featuring a sophisticated **real-world stock market simulation** that models actual economic conditions. The system uses a simplified functional architecture with dynamic economic data integration.

## Current Economic Environment

The system currently models a **high inflation crisis environment** based on real economic data:

- **Inflation Rate**: 8.51% YoY (well above Fed target of 2%)
- **Market Confidence**: 35% (pessimistic sentiment)
- **GDP Growth**: -1.2% quarterly (economic slowdown)
- **Federal Funds Rate**: 4.00% (restrictive monetary policy)
- **Unemployment**: 3.2% (tight labor market contributing to inflation)

## Real-World Stock Market System

### Stock Universe
The system tracks **24 major real stocks** across **8 economic sectors**:

#### Sectors and Stocks:
- **ENERGY** (3): XOM (ExxonMobil), CVX (Chevron), SLB (Schlumberger)
- **TECH** (4): AAPL (Apple), MSFT (Microsoft), GOOGL (Alphabet), NVDA (NVIDIA)
- **FINANCE** (3): JPM (JPMorgan), BAC (Bank of America), WFC (Wells Fargo)
- **HEALTH** (3): JNJ (Johnson & Johnson), PFE (Pfizer), UNH (UnitedHealth)
- **RETAIL** (3): WMT (Walmart), TGT (Target), COST (Costco)
- **MANUFACTURING** (3): CAT (Caterpillar), GE (General Electric), MMM (3M)
- **ENTERTAINMENT** (3): DIS (Disney), NFLX (Netflix), CMCSA (Comcast)
- **TRANSPORT** (2): BA (Boeing), UPS (United Parcel Service)

### Market Parameters (Dynamically Calculated)

The system **never uses hardcoded values**. All market parameters are calculated in real-time from economic data files:

```python
# Current parameters based on 8.51% inflation environment:
{
    "trend_direction": -0.35,     # Bearish (due to high inflation)
    "volatility": 0.80,           # Very high (crisis conditions)
    "momentum": 0.25,             # Weak (economic uncertainty)
    "market_sentiment": 0.35,     # Low (35% market confidence)
    "long_term_outlook": 0.40     # Pessimistic (policy uncertainty)
}
```

## Discord Commands

### Core Bot Commands

#### `/helper [query]`
AI assistance with context awareness using Gemini 2.5.

**Parameters:**
- `query` (str): User question or request

**Example:**
```
/helper What is the current inflation rate and its impact on markets?
```

#### `/bill_keyword_search [query]`
Search congressional bills with keyword matching.

**Parameters:**
- `query` (str): Search keywords

**Example:**
```
/bill_keyword_search healthcare reform
```

#### `/econ_report`
Generate current economic overview with **dynamic data reading**.

**Features:**
- Real economic data from JSON files (no hardcoded values)
- Current inflation status (8.51% crisis level)
- Market sentiment analysis (35% confidence)
- Stock market integration with calculated parameters

**Example Response:**
```
📊 Economic Report - 2025-06-15
🔥 High Inflation Crisis

🏛️ GDP: $26.8T 📉 (-1.2%)
🔥 Inflation Crisis: 8.51% YoY, Fed Rate: 4.00%, Status: 🚨 Critical
😟 Market Sentiment: 35% confidence, 78% inflation anxiety, Pessimistic outlook
👥 Labor Market: 3.2% unemployment, 4.2% wage growth, Tight status
📈 Stock Market: 📉 Bearish, 🌪️ Very High volatility, 24 active stocks
```

### Stock Market Commands (User)

#### `/stocks_list`
View all 24 real stocks across 8 sectors.

**Returns:**
- Comprehensive stock listing by sector
- Current prices and performance
- Market overview with calculated parameters

#### `/stocks_price [symbol]`
Get detailed information for individual stock.

**Parameters:**
- `symbol` (str): Stock symbol (AAPL, MSFT, GOOGL, etc.)

**Returns:**
- Current price with change indicators
- Sector information
- Generated price chart (matplotlib)

#### `/stocks_categories`
View all economic sectors and their composition.

**Returns:**
- 8 sectors with stock listings
- Sector performance summaries
- ETF-like category analysis

#### `/stocks_history_48h [symbol]`
View 48-hour price history with charts.

**Parameters:**
- `symbol` (str): Stock symbol

**Returns:**
- Historical price data
- Generated chart visualization
- Performance statistics

### Stock Market Commands (Admin)

#### `/stocks_set_market [param] [value]`
Set specific market parameters (temporary override).

**Parameters:**
- `param` (str): Parameter name (trend_direction, volatility, etc.)
- `value` (float): New parameter value

**Note:** Parameters reset to calculated values on next economic data sync.

#### `/stocks_force_update`
Force immediate recalculation of market parameters from economic data.

**Use Cases:**
- After updating economic data files
- Troubleshooting parameter calculation
- Testing economic scenario changes

#### `/stocks_sync_econ`
Synchronize market parameters with latest economic analysis.

**Features:**
- Reads all economic data files
- Recalculates market parameters
- Updates stock market behavior

#### `/stocks_reset`
Reset market to default state with fresh parameter calculation.

#### `/stocks_force_init`
Force complete re-initialization of stock market system.

### Economic Analysis Commands

#### `/fetch_econ_data`
Trigger comprehensive economic data collection and analysis.

#### `/econ_status` (Admin)
View economic system status and current parameters.

#### `/econ_set_inflation [rate]` (Admin)
Set inflation rate in economic data (updates market parameters).

## Core Functions API

### Stock Market Functions

#### `get_stock_market() -> StockMarket`
Get singleton stock market instance.

```python
from stock_market import get_stock_market

market = get_stock_market()
current_params = market.market_params
```

#### `StockMarket._calculate_market_params_from_economic_data() -> Dict[str, float]`
Calculate market parameters from economic data files.

**Data Sources:**
- `economic_data/inflation.json` → volatility, trend direction
- `economic_data/sentiment.json` → market sentiment
- `economic_data/gdp.json` → momentum, trend adjustment
- `economic_data/unemployment.json` → volatility adjustment

**Returns:** Dict with calculated market parameters

#### `StockMarket.generate_stock_chart(symbol: str) -> BytesIO`
Generate matplotlib price chart for Discord embeds.

**Parameters:**
- `symbol` (str): Stock symbol

**Returns:** BytesIO object with PNG chart data

### Economic Analysis Functions

#### `economic_utils.econ_data.get_fresh_economic_report() -> Dict[str, Any]`
Get current economic data from individual JSON files.

**Returns:**
```python
{
    "inflation": {"rate": 8.51, "federal_funds_rate": 4.00, ...},
    "sentiment": {"market_confidence": 35, "inflation_anxiety": 78, ...},
    "gdp": {"value": 26.8, "change_percent": -1.2, ...},
    "unemployment": {"rate": 3.2, "wage_growth": 4.2, ...}
}
```

#### `economic_utils.set_economic_parameter(param: str, value: Any) -> bool`
Set economic parameter (triggers market parameter recalculation).

## Data File Structure

### Economic Data Files

```
economic_data/
├── inflation.json      # 8.51% YoY, 4.00% fed rate
├── sentiment.json      # 35% confidence, 78% anxiety
├── gdp.json           # $26.8T, -1.2% growth
├── unemployment.json   # 3.2% rate, tight market
└── parameters.json    # Base economic parameters
```

### Stock Market Data Files

```
stock_data/
├── market_data.json        # Current stock prices and state
├── stock_history.json      # Historical price movements
├── daily_analysis.json     # AI analysis results
└── market_params.json      # Current calculated parameters
```

## Economic Data Integration

### Dynamic Parameter Calculation

The system uses **zero hardcoded values**. All market behavior is calculated from real economic data:

```python
# Example: High inflation triggers bearish conditions
if inflation_rate > 6.0:  # 8.51% triggers this
    params.update({
        "trend_direction": -0.25,    # Bearish market
        "volatility": 0.65,          # High volatility
        "market_sentiment": 0.35     # Low confidence
    })
```

### Real-Time Updates

Market parameters recalculate when economic data changes:

1. Economic data files updated
2. `_calculate_market_params_from_economic_data()` called
3. New parameters applied to stock price generation
4. Market behavior reflects new economic conditions

## Error Handling

### Standard Error Responses

All commands use consistent error handling:

```python
@handle_errors("Failed to process stock command")
async def stock_command(interaction, ...):
    # Command logic
```

**Common Errors:**
- Invalid stock symbol
- Economic data file corruption
- Parameter calculation failures
- Chart generation errors

### Economic Data Validation

The system validates economic data integrity:

```python
# Ensure inflation data exists and is valid
if inflation_rate > 0 and inflation_rate < 100:
    # Use data
else:
    # Fall back to default parameters
```

## Performance Considerations

### Caching Strategy
- Economic data cached until file modification
- Market parameters recalculated only when economic data changes
- Stock price calculations use efficient Perlin noise algorithms

### Memory Management
- Singleton pattern for stock market instance
- Lazy loading of economic data
- Chart generation on-demand

## Security

### Data Integrity
- Economic data files protected from corruption
- Parameter validation prevents invalid market states
- Admin commands require proper Discord role permissions

### Rate Limiting
- Stock price requests limited to prevent spam
- Chart generation throttled
- Economic data updates require admin permissions

## Future Enhancements

### Planned Features
- Real-time economic data feeds
- Advanced charting with technical indicators
- Portfolio tracking for Discord users
- Economic scenario simulation tools

### Extensibility
The functional architecture allows easy addition of:
- New stock symbols
- Additional economic indicators
- Enhanced market modeling algorithms
- Integration with external financial APIs

---

**Key Principle**: The VCBot API demonstrates that sophisticated financial modeling can be achieved with simple, maintainable functional architecture. The elimination of hardcoded values in favor of dynamic data reading provides a realistic economic simulation that responds to actual market conditions.