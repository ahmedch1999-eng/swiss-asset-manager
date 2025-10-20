# Swiss Asset Pro - Live Data Architecture

## Overview

The Swiss Asset Pro application has been enhanced with a comprehensive live data integration system that fetches real-time market data from multiple trusted sources while maintaining a robust fallback mechanism to simulated data.

## Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Layer     │    │  Data Provider  │
│   (Dashboard)   │◄──►│   (Flask)       │◄──►│   (Orchestrator)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Store    │◄──►│  Data Validator │◄──►│  Live Fetchers  │
│  (SQLite/DB)    │    │  (Quality Check)│    │  (Yahoo/SNB/    │
└─────────────────┘    └─────────────────┘    │  CoinGecko)     │
                                              └─────────────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │ Fallback Provider│
                                              │ (Simulation)    │
                                              └─────────────────┘
```

## Data Flow

### 1. Data Request Flow
```
User Request → API Endpoint → Data Provider → Source Selection → Data Fetching
     ↓
Data Validation → Quality Assessment → Storage → Response to User
```

### 2. Fallback Flow
```
Live Data Request → Source Failure → Fallback Provider → Simulated Data
     ↓
Log Fallback Event → Trigger Recovery Job → Continue Service
```

## Components

### 1. Data Provider (`live_data/providers/data_provider.py`)
- **Purpose**: Main orchestrator for data sources
- **Responsibilities**:
  - Decide between live and simulated data
  - Manage data freshness (15-minute threshold)
  - Handle source selection based on symbol type
  - Implement fallback logic
  - Log all data source decisions

### 2. Live Data Fetchers (`live_data/fetchers/`)

#### Yahoo Finance Fetcher (`yahoo_fetcher.py`)
- **Sources**: Yahoo Finance API
- **Data Types**: Stocks, ETFs, indices
- **Rate Limit**: 2 requests/second
- **Trust Score**: 85/100

#### SNB Fetcher (`snb_fetcher.py`)
- **Sources**: Swiss National Bank API
- **Data Types**: Swiss Franc exchange rates
- **Rate Limit**: 1 request/2 seconds
- **Trust Score**: 95/100

#### CoinGecko Fetcher (`coingecko_fetcher.py`)
- **Sources**: CoinGecko API
- **Data Types**: Cryptocurrency prices and market data
- **Rate Limit**: 1 request/second
- **Trust Score**: 80/100

### 3. Data Validator (`live_data/validators/data_validator.py`)
- **Purpose**: Ensure data quality and consistency
- **Validations**:
  - Price range validation (0.001 - 1,000,000)
  - Currency validation (USD, CHF, EUR, GBP, JPY, CAD, AUD)
  - Symbol format validation
  - Volume plausibility checks
  - Timestamp validation
  - Source verification

### 4. Data Store (`live_data/storage/data_store.py`)
- **Database**: SQLite (extensible to PostgreSQL/TimescaleDB)
- **Tables**:
  - `market_prices`: Real-time price data
  - `financial_statements`: Company financial data
  - `source_status`: Data source health monitoring
  - `data_quality_metrics`: Quality assessment history

### 5. Fallback Provider (`live_data/providers/fallback_provider.py`)
- **Purpose**: Generate realistic simulated data when live sources fail
- **Features**:
  - Asset class-specific simulation (stocks, crypto, commodities, bonds, indices, FX)
  - Realistic price movements using geometric Brownian motion
  - Market hours simulation
  - Mean reversion modeling

## Data Sources

### Primary Sources (Live Data)
1. **Yahoo Finance**
   - Stocks: AAPL, MSFT, GOOGL, NESN.SW, NOVN.SW
   - Indices: ^GSPC, ^SSMI, ^SLI
   - ETFs: SPY, QQQ, BND

2. **Swiss National Bank (SNB)**
   - FX Rates: EURCHF=X, USDCHF=X, GBPCHF=X, JPYCHF=X
   - Official Swiss Franc exchange rates

3. **CoinGecko**
   - Cryptocurrencies: BTC-USD, ETH-USD, ADA-USD, DOT-USD, LINK-USD
   - Market data, historical prices, trending coins

### Fallback Source (Simulation)
- **Simulated Data Provider**: Generates realistic market data for all asset classes
- **Trust Score**: 30/100 (clearly marked as simulated)
- **Use Case**: When live sources are unavailable or fail

## API Endpoints

### Live Data Endpoints
- `GET /api/v1/live/data/<symbol>` - Get live data for a symbol
- `GET /api/v1/live/historical/<symbol>?days=30` - Get historical data
- `GET /api/v1/live/sources/status` - Get data source status
- `GET /api/v1/live/quality/<symbol>` - Get data quality metrics

### Legacy Endpoints (Enhanced)
- `GET /get_live_data/<symbol>` - Enhanced with live data integration
- All existing endpoints now use the new data provider system

## Data Quality Metrics

### Quality Score Calculation (0-100)
- **Basic Structure** (20 points): Required fields present
- **Price Validation** (30 points): Price within reasonable range
- **Currency Validation** (10 points): Valid currency code
- **Volume Validation** (10 points): Volume within reasonable range
- **Timestamp Validation** (10 points): Valid timestamp format
- **Source Validation** (10 points): Known data source
- **Live Data Bonus** (5 points): Data from live source
- **High Confidence Bonus** (5 points): High confidence score

### Quality Thresholds
- **Excellent**: 90-100 points
- **Good**: 70-89 points
- **Fair**: 50-69 points
- **Poor**: 30-49 points
- **Unacceptable**: 0-29 points

## Error Handling

### Source Failure Handling
1. **Immediate Fallback**: Switch to simulation when live source fails
2. **Logging**: Record all fallback events in `/logs/fallback_events.log`
3. **Recovery Jobs**: Trigger background recovery for failed sources
4. **Status Monitoring**: Track source health and success rates

### Data Validation Failures
1. **Rejection**: Invalid data is rejected and logged
2. **Fallback**: Switch to simulation for invalid live data
3. **Quality Scoring**: Assign low quality scores to problematic data
4. **Alerting**: Log validation failures for monitoring

## Performance Considerations

### Caching Strategy
- **In-Memory Cache**: 5-minute cache for frequently requested data
- **Database Storage**: Persistent storage for historical data
- **Rate Limiting**: Respect API rate limits for all sources

### Database Optimization
- **Indexes**: Optimized indexes on symbol and timestamp fields
- **Cleanup**: Automatic cleanup of data older than 30 days
- **Batch Operations**: Efficient batch inserts for bulk data

## Security & Compliance

### API Key Management
- **Environment Variables**: All API keys stored in environment variables
- **No Hardcoding**: No secrets in source code
- **Rotation Support**: Easy API key rotation

### Rate Limiting Compliance
- **Respectful Scraping**: Follow robots.txt and API terms
- **Rate Limits**: Implemented for all data sources
- **Backoff Strategy**: Exponential backoff on rate limit hits

### Data Privacy
- **No PII**: No personal information stored
- **Anonymized Logging**: All logs anonymized
- **GDPR Compliance**: Data retention policies implemented

## Monitoring & Observability

### Health Checks
- **Source Status**: Monitor all data source health
- **Data Quality**: Track quality metrics over time
- **Performance**: Monitor response times and throughput

### Logging
- **Structured Logging**: JSON-formatted logs for easy parsing
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Rotation**: Automatic log rotation to prevent disk space issues

### Metrics
- **Success Rates**: Track success rates for each data source
- **Response Times**: Monitor API response times
- **Data Freshness**: Track how fresh the data is
- **Fallback Usage**: Monitor fallback frequency

## Future Enhancements

### Planned Improvements
1. **PostgreSQL/TimescaleDB**: Upgrade to time-series database
2. **Real-time Streaming**: WebSocket integration for real-time updates
3. **Machine Learning**: Predictive data quality assessment
4. **Additional Sources**: Integration with more data providers
5. **Advanced Analytics**: Real-time portfolio analytics

### Scalability Considerations
1. **Microservices**: Split into separate microservices
2. **Message Queues**: Implement message queues for async processing
3. **Load Balancing**: Distribute load across multiple instances
4. **CDN Integration**: Cache static data in CDN

## Testing Strategy

### Test Coverage
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end pipeline testing
- **Performance Tests**: Load and stress testing
- **Quality Tests**: Data quality validation testing

### Test Data
- **Mock Data**: Comprehensive mock data for testing
- **Edge Cases**: Test boundary conditions and error scenarios
- **Real Data**: Integration tests with real data sources

## Deployment

### Environment Configuration
- **Development**: Local SQLite database
- **Staging**: PostgreSQL with test data
- **Production**: PostgreSQL/TimescaleDB with live data

### Monitoring Setup
- **Health Endpoints**: `/health` and `/metrics` endpoints
- **Log Aggregation**: Centralized logging system
- **Alerting**: Automated alerts for system issues

## Conclusion

The live data integration system provides a robust, scalable foundation for real-time market data while maintaining reliability through comprehensive fallback mechanisms. The architecture is designed to be extensible, maintainable, and performant while ensuring data quality and system reliability.
