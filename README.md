# Swiss Asset Pro - Professional Portfolio Management Platform

## Overview

Swiss Asset Pro is a comprehensive portfolio management and analysis platform designed for Swiss investors. The application provides real-time market data, advanced portfolio analytics, Swiss tax calculations, and professional-grade financial tools.

## 🚀 Key Features

### Live Data Integration
- **Real-time Market Data**: Live data from Yahoo Finance, Swiss National Bank, and CoinGecko
- **Multi-Source Fallback**: Automatic fallback to simulation when live sources are unavailable
- **Data Quality Assurance**: Comprehensive validation and quality scoring system
- **Source Health Monitoring**: Real-time monitoring of all data sources

### Portfolio Management
- **Portfolio Tracking**: Real-time portfolio valuation and performance tracking
- **Asset Allocation**: Visual portfolio allocation with interactive charts
- **Performance Analytics**: Advanced performance metrics and risk analysis
- **Swiss Tax Integration**: Automatic Swiss stamp tax and withholding tax calculations

### Financial Analysis
- **Technical Analysis**: SMA, EMA, RSI, Bollinger Bands, MACD indicators
- **Fundamental Analysis**: DCF valuation, financial statement analysis
- **Risk Management**: VaR, Max Drawdown, Sharpe Ratio calculations
- **Stress Testing**: Portfolio stress testing with various market scenarios

### Swiss Market Focus
- **Swiss Stocks**: Coverage of major Swiss companies (Nestlé, Novartis, Roche, UBS)
- **SIX Exchange**: Real-time data from Swiss stock exchange
- **CHF Exchange Rates**: Official Swiss National Bank exchange rates
- **Swiss Tax Compliance**: Built-in Swiss tax calculations and optimization

## 🏗️ Architecture

### Live Data System
```
Frontend (Dashboard) ↔ API Layer (Flask) ↔ Data Provider (Orchestrator)
                                                        ↓
Data Store (SQLite) ↔ Data Validator ↔ Live Fetchers (Yahoo/SNB/CoinGecko)
                                                        ↓
                                              Fallback Provider (Simulation)
```

### Data Sources
- **Primary Sources**: Yahoo Finance, SNB, CoinGecko
- **Fallback Source**: Realistic simulation system
- **Data Quality**: Multi-layer validation with 0-100 quality scoring
- **Storage**: SQLite (extensible to PostgreSQL/TimescaleDB)

## 🛠️ Technology Stack

### Backend
- **Flask**: Web framework with SocketIO for real-time updates
- **Python 3.11+**: Core application language
- **SQLite**: Primary database (extensible to PostgreSQL)
- **yfinance**: Yahoo Finance data integration
- **numpy/scipy**: Mathematical calculations and optimization

### Frontend
- **HTML5/CSS3**: Modern responsive design
- **JavaScript**: Interactive charts and real-time updates
- **Chart.js**: Professional financial charts
- **PWA**: Progressive Web App capabilities

### Data Integration
- **Live Data Fetchers**: Yahoo Finance, SNB, CoinGecko
- **Data Validation**: Comprehensive quality assurance
- **Caching**: Multi-layer caching strategy
- **Rate Limiting**: Respectful API usage

## 📊 Data Quality & Reliability

### Quality Metrics
- **Quality Score**: 0-100 comprehensive assessment
- **Source Trust**: Weighted trust scores for different sources
- **Data Freshness**: 15-minute freshness threshold
- **Validation**: Multi-layer data validation

### Fallback System
- **Automatic Fallback**: Seamless fallback to simulation
- **Source Monitoring**: Real-time source health tracking
- **Error Recovery**: Automatic recovery mechanisms
- **Audit Trail**: Complete logging of all data decisions

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- pip package manager

### Installation
```bash
# Clone the repository
git clone https://github.com/your-username/swiss-asset-manager.git
cd swiss-asset-manager

# Install dependencies
pip install -r requirements.txt

# Start the application
python app.py
```

### Environment Setup
```bash
# Optional: Set API keys for enhanced data access
export ALPHA_VANTAGE_API_KEY="your_api_key_here"
export POLYGON_API_KEY="your_api_key_here"
export FINNHUB_API_KEY="your_api_key_here"
```

### Access the Application
- **Local**: http://localhost:3000
- **Health Check**: http://localhost:3000/health
- **API Documentation**: http://localhost:3000/api/v1/live/sources/status

## 📈 API Endpoints

### Live Data API
- `GET /api/v1/live/data/<symbol>` - Get live market data
- `GET /api/v1/live/historical/<symbol>?days=30` - Historical data
- `GET /api/v1/live/sources/status` - Data source status
- `GET /api/v1/live/quality/<symbol>` - Data quality metrics

### Portfolio API
- `GET /api/portfolio_analysis` - Portfolio performance analysis
- `POST /api/swiss_tax_calculation` - Swiss tax calculations
- `POST /api/stress_test` - Portfolio stress testing
- `POST /api/portfolio_optimization` - Portfolio optimization

### Technical Analysis API
- `GET /api/technical_analysis/<symbol>` - Technical indicators
- `GET /api/market_sentiment` - Market sentiment analysis
- `GET /api/v1/valuation/dcf` - DCF valuation

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python -m pytest test_live_data_system.py -v

# Run specific test categories
python test_live_data_system.py

# Run with coverage
python -m pytest --cov=live_data test_live_data_system.py
```

### Test Coverage
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end pipeline testing
- **Error Handling**: Failure scenario testing
- **Performance Tests**: Load and response time testing

## 📚 Documentation

### Architecture Documentation
- [Data Architecture](docs/data_architecture.md) - Complete system architecture
- [API Documentation](docs/api_documentation.md) - API reference
- [Deployment Guide](docs/deployment_guide.md) - Production deployment

### Development Reports
- [Live Data Integration Report](dev-reports/live-data/summary.md) - Implementation details
- [Performance Analysis](dev-reports/performance/analysis.md) - Performance metrics
- [Security Assessment](dev-reports/security/assessment.md) - Security analysis

## 🔧 Configuration

### Data Source Configuration
```python
# Trust scores for different sources
TRUST_SCORES = {
    'yahoo': 85,
    'snb': 95,
    'coingecko': 80,
    'simulation': 30
}

# Rate limits (requests per second)
RATE_LIMITS = {
    'yahoo': 2.0,
    'snb': 0.5,
    'coingecko': 1.0
}
```

### Quality Thresholds
```python
# Data quality thresholds
QUALITY_THRESHOLDS = {
    'excellent': 90,
    'good': 70,
    'fair': 50,
    'poor': 30
}
```

## 🚀 Deployment

### Development
```bash
# Local development
python app.py
```

### Production
```bash
# Using Docker
docker-compose up -d

# Using systemd
sudo systemctl start swiss-asset-pro
```

### Environment Variables
```bash
# Database configuration
DATABASE_URL=postgresql://user:pass@localhost/swiss_asset_pro

# API keys
ALPHA_VANTAGE_API_KEY=your_key
POLYGON_API_KEY=your_key
FINNHUB_API_KEY=your_key

# Application settings
FLASK_ENV=production
SECRET_KEY=your_secret_key
```

## 📊 Monitoring

### Health Checks
- **Application Health**: `/health` endpoint
- **Data Source Status**: `/api/v1/live/sources/status`
- **Database Health**: Automatic database health monitoring
- **Performance Metrics**: Response time and throughput monitoring

### Logging
- **Structured Logging**: JSON-formatted logs
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Rotation**: Automatic log rotation
- **Error Tracking**: Comprehensive error logging

## 🔒 Security

### Data Security
- **No PII Storage**: No personal information stored
- **API Key Management**: Secure API key storage
- **Rate Limiting**: Protection against abuse
- **Input Validation**: Comprehensive input validation

### Compliance
- **GDPR Compliance**: Data retention policies
- **Swiss Regulations**: Swiss financial regulations compliance
- **API Terms**: Respect for all API terms of service
- **Data Privacy**: Anonymized logging and monitoring

## 🤝 Contributing

### Development Setup
```bash
# Fork the repository
git clone https://github.com/your-username/swiss-asset-manager.git

# Create feature branch
git checkout -b feature/your-feature

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Submit pull request
```

### Code Standards
- **PEP 8**: Python code style guidelines
- **Type Hints**: Use type hints for better code clarity
- **Documentation**: Comprehensive docstrings
- **Testing**: Write tests for all new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Yahoo Finance**: Market data provider
- **Swiss National Bank**: Official CHF exchange rates
- **CoinGecko**: Cryptocurrency data
- **Chart.js**: Charting library
- **Flask**: Web framework

## 📞 Support

### Documentation
- [Architecture Guide](docs/data_architecture.md)
- [API Reference](docs/api_documentation.md)
- [Troubleshooting Guide](docs/troubleshooting.md)

### Issues
- [GitHub Issues](https://github.com/your-username/swiss-asset-manager/issues)
- [Discussions](https://github.com/your-username/swiss-asset-manager/discussions)

---

**Swiss Asset Pro** - Professional portfolio management for Swiss investors

*Built with ❤️ in Switzerland*
