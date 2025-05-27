# VCBot Economic Analysis System - Planning Document

## Project Overview

**Goal**: Create an intelligent economic analysis system for a Virtual Congress Discord server that autonomously monitors governmental activity, analyzes legislative trends, and generates comprehensive economic data and forecasts.

## System Architecture

### Core Components

#### 1. Economic Data Collection Engine (`economic_engine.py`)
- **Agentic Loop**: Continuous analysis cycle using Gemini 2.5
- **Multi-Channel Monitoring**: Simultaneous analysis of all server channels
- **Document Integration**: Direct access to Google Docs legislative documents
- **Data Synthesis**: Transform Discord activity into economic indicators

#### 2. Data Storage System (`economic_data/`)
```
economic_data/
├── stocks.json          # Virtual stock market data
├── inflation.json       # Inflation metrics and trends
├── gdp.json            # GDP calculations based on activity
├── unemployment.json    # Job market indicators
├── budget.json         # Government budget analysis
├── trade.json          # Trade activity metrics
├── sentiment.json      # Market sentiment from discussions
└── parameters.json     # Admin-configurable economic variables
```

#### 3. Analysis Tools (`ai_tools.py` extensions)
- `fetch_document_content`: Extract text from Google Docs links
- `analyze_channel_history`: Deep analysis of channel messages
- `calculate_economic_indicators`: Transform activity into metrics
- `generate_economic_forecast`: Predictive analysis

#### 4. Administrative Control System
- **Steerable Economy**: Admin commands to adjust economic parameters
- **Real-time Tuning**: Modify inflation rates, stock volatility, GDP factors
- **Scenario Testing**: Simulate economic events and policy impacts

## Economic Indicators & Metrics

### Primary Indicators
1. **Virtual Stock Market**
   - Government efficiency stocks
   - Sector-based performance (Defense, Healthcare, Education)
   - Legislative productivity index
   - Bipartisan cooperation index

2. **Macroeconomic Metrics**
   - GDP (based on legislative output)
   - Inflation (policy impact analysis)
   - Unemployment (committee activity)
   - Trade balance (interstate relations)

3. **Government Performance Metrics**
   - Budget efficiency
   - Policy implementation rate
   - Public approval sentiment
   - Inter-branch cooperation

### Data Sources (Discord Channels)
- **Legislative Channels**: Bill discussions, voting records
- **Committee Channels**: Specialized policy development
- **News Channels**: Media coverage and public reaction
- **Administrative Channels**: Government operations
- **Public Forums**: Citizen engagement and sentiment

## Implementation Strategy

### Phase 1: Core Infrastructure
1. Create economic data cog with Discord.py
2. Implement Gemini 2.5 integration
3. Build document reading capabilities
4. Set up data storage system

### Phase 2: Analysis Engine
1. Develop agentic analysis loop
2. Create economic calculation algorithms
3. Implement sentiment analysis
4. Build trend detection systems

### Phase 3: Administrative Controls
1. Admin-only parameter adjustment commands
2. Real-time economic steering capabilities
3. Scenario simulation tools
4. Performance monitoring dashboard

### Phase 4: Testing & Validation
1. Mock data testing without Discord API
2. Economic model validation
3. Admin interface testing
4. Performance optimization

## Command Structure

### Public Commands
- `/econ_report` - Generate current economic overview
- `/stock_prices` - Display virtual stock market
- `/inflation_data` - Show inflation trends
- `/gdp_status` - Current GDP metrics
- `/economic_forecast` - AI-generated predictions

### Admin Commands
- `/econ_set_inflation [rate]` - Adjust inflation parameters
- `/econ_set_stock [symbol] [volatility]` - Control stock behavior
- `/econ_adjust_gdp [multiplier]` - Modify GDP calculation factors
- `/econ_simulate [scenario]` - Run economic scenario tests
- `/econ_reset` - Reset all economic parameters
- `/fetch_econ_data` - Trigger comprehensive data collection

## Technical Implementation

### Agentic Loop Design
```python
async def economic_analysis_loop():
    while True:
        # 1. Collect data from all channels
        channel_data = await collect_channel_activity()
        
        # 2. Analyze documents from recent links
        documents = await analyze_linked_documents()
        
        # 3. Calculate economic indicators
        indicators = await calculate_indicators(channel_data, documents)
        
        # 4. Generate insights using Gemini 2.5
        insights = await gemini_analysis(indicators)
        
        # 5. Update economic data files
        await update_economic_data(insights)
        
        # 6. Sleep for next cycle (configurable interval)
        await asyncio.sleep(ANALYSIS_INTERVAL)
```

### Economic Calculation Examples

#### GDP Calculation
```python
def calculate_gdp(legislative_activity, committee_work, public_engagement):
    """
    GDP = (Bills Passed × Weight) + (Committee Hours × Weight) + 
          (Public Participation × Weight) × Economic Multiplier
    """
    return (
        legislative_activity * GDP_LEGISLATIVE_WEIGHT +
        committee_work * GDP_COMMITTEE_WEIGHT +
        public_engagement * GDP_PUBLIC_WEIGHT
    ) * GDP_MULTIPLIER
```

#### Stock Market Simulation
```python
def update_stock_prices(government_efficiency, public_sentiment, legislative_productivity):
    """
    Stock prices based on government performance metrics
    """
    for stock in TRACKED_STOCKS:
        base_change = calculate_base_change(stock, efficiency_metrics)
        sentiment_modifier = public_sentiment * SENTIMENT_WEIGHT
        volatility = stock['volatility'] * random.uniform(0.8, 1.2)
        
        new_price = stock['price'] * (1 + base_change + sentiment_modifier + volatility)
        stock['price'] = max(0.01, new_price)  # Prevent negative prices
```

## Data Collection Strategy

### Channel Analysis Priorities
1. **High Impact**: Legislative voting, budget discussions
2. **Medium Impact**: Committee meetings, policy debates
3. **Low Impact**: General discussion, off-topic channels

### Document Processing
- Automatic detection of Google Docs links in messages
- Content extraction and summarization
- Policy impact assessment
- Economic relevance scoring

### Sentiment Analysis
- Message tone analysis for market sentiment
- Public approval tracking
- Policy reception measurement
- Inter-party cooperation indicators

## Testing Framework

### Mock Data Generation
```python
class MockDiscordData:
    """Generate realistic Discord activity for testing"""
    
    def generate_legislative_session(self):
        """Simulate a legislative session with bills, votes, debates"""
        
    def generate_committee_meeting(self):
        """Simulate committee activity and document creation"""
        
    def generate_public_discussion(self):
        """Simulate citizen engagement and reactions"""
```

### Economic Model Validation
- Historical data backtesting
- Parameter sensitivity analysis
- Prediction accuracy measurement
- Edge case scenario testing

## Performance Considerations

### Optimization Strategies
- Channel activity caching
- Incremental data processing
- Efficient document parsing
- Rate limiting for external APIs

### Scalability
- Configurable analysis intervals
- Selective channel monitoring
- Data compression for storage
- Background processing queues

## Security & Privacy

### Data Protection
- No storage of personal messages
- Aggregate data only
- Admin command authentication
- Rate limiting on sensitive operations

### API Key Management
- Secure Gemini API key storage
- Google Docs API authentication
- Discord permissions management

## Success Metrics

### System Performance
- Data collection accuracy
- Analysis speed and efficiency
- Prediction quality
- Admin usability

### Economic Model Quality
- Realistic indicator movements
- Responsive to actual events
- Useful insights generation
- Stable long-term trends

---

## Next Steps

1. **Implementation Start**: Create core economic cog structure
2. **Tool Development**: Build Gemini integration and document tools
3. **Data System**: Set up JSON-based storage
4. **Testing Phase**: Comprehensive validation without Discord API
5. **Integration**: Connect with existing bot.py architecture

This system will provide a sophisticated, steerable economic simulation that transforms Virtual Congress Discord activity into meaningful economic data and insights.