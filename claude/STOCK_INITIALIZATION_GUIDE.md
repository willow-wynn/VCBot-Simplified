# Stock Market Initialization Guide

This guide explains how to use the new `submit_daily_stock_initialization` tool to manually set stock market parameters via the MCP server.

## Overview

The tool allows Claude to submit complete stock market initialization data including:
- Market parameters (trend, volatility, momentum, etc.)
- Invisible market factors (institutional flow, liquidity, etc.)
- Individual stock prices and daily ranges for all 25 stocks
- Sector outlooks
- Analysis reasoning

## Required Stocks

All 25 stocks must be included:

### ENERGY (3 stocks)
- XOM (ExxonMobil)
- CVX (Chevron)
- COP (ConocoPhillips)

### ENTERTAINMENT (3 stocks)
- NFLX (Netflix)
- DIS (Disney)
- EA (Electronic Arts)

### FINANCE (5 stocks)
- JPM (JPMorgan Chase)
- BAC (Bank of America)
- V (Visa)
- GS (Goldman Sachs)
- BRK.B (Berkshire Hathaway B)

### HEALTH (3 stocks)
- JNJ (Johnson & Johnson)
- UNH (UnitedHealth Group)
- PFE (Pfizer)

### MANUFACTURING (3 stocks)
- CAT (Caterpillar)
- GE (General Electric)
- LMT (Lockheed Martin)

### RETAIL (3 stocks)
- WMT (Walmart)
- COST (Costco)
- HD (Home Depot)

### TECH (4 stocks)
- AAPL (Apple)
- MSFT (Microsoft)
- GOOGL (Alphabet/Google)
- NVDA (NVIDIA)

### TRANSPORT (1 stock)
- BA (Boeing)

## Parameter Ranges

### Market Parameters
- `trend_direction`: -1.0 to 1.0 (negative = bearish, positive = bullish)
- `volatility`: 0.0 to 1.0 (0 = calm, 1 = extremely volatile)
- `momentum`: 0.0 to 1.0 (strength of trend)
- `market_sentiment`: 0.0 to 1.0 (0 = fearful, 1 = greedy)
- `long_term_outlook`: 0.0 to 1.0 (0 = pessimistic, 1 = optimistic)

### Invisible Factors
- `institutional_flow`: -1.0 to 1.0 (negative = selling, positive = buying)
- `liquidity_factor`: 0.0 to 1.0 (market liquidity)
- `news_velocity`: 0.0 to 1.0 (speed of news impact)
- `sector_rotation`: -1.0 to 1.0 (money flow between sectors)
- `risk_appetite`: 0.0 to 1.0 (investor risk tolerance)

### Stock Price Data
Each stock requires:
- `open_price`: Opening price for the day
- `range_low`: Minimum price for the day
- `range_high`: Maximum price for the day
- `sector_factor`: 0.0 to 2.0 (how strongly stock responds to market)

## Range Guidelines

Per CLAUDE.md instructions:
- Normal market: 3-5% daily range
- High volatility: 5-7% daily range
- Extreme conditions: 7-10% daily range

In the current 8.51% inflation environment, most stocks should have 5-7% minimum ranges.

## Example Usage

See `example_stock_init.json` for a complete example matching the current economic environment.

## Important Notes

1. **All stocks required**: The tool validates that all 25 stocks are provided
2. **Parameter validation**: All parameters are clamped to valid ranges
3. **Logging**: Initialization is logged to `stock_data/analysis_logs/`
4. **Daily analysis**: Saved to `stock_data/daily_analysis.json`
5. **Market state**: Updated in `stock_data/market_data.json`

## When to Use

Use this tool when:
- Starting a new trading day
- Economic conditions have changed significantly
- Manual market adjustment is needed
- Testing specific market scenarios

## Integration with Economic Data

The tool respects the principle of being data-driven:
- Parameters should reflect actual economic indicators
- Use current inflation (8.51%), GDP growth, unemployment data
- Align with market confidence and sentiment indicators
- No random or fake data generation