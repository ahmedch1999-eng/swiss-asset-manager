"""
Yahoo Finance Fetcher

Fetches real-time market data from Yahoo Finance API.
This is the primary source for stocks, ETFs, and indices.
"""

import yfinance as yf
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)

class YahooFetcher(BaseFetcher):
    """
    Yahoo Finance data fetcher.
    
    Provides access to real-time and historical market data
    for stocks, ETFs, indices, and other financial instruments.
    """
    
    def __init__(self):
        super().__init__('yahoo', rate_limit=0.5)  # 2 requests per second max
    
    def fetch_data(self, symbol: str, data_type: str = 'price') -> Optional[Dict[str, Any]]:
        """
        Fetch data from Yahoo Finance.
        
        Args:
            symbol: Market symbol (e.g., 'AAPL', '^GSPC', 'NESN.SW')
            data_type: Type of data ('price', 'info', 'financials')
            
        Returns:
            Dict containing market data or None if failed
        """
        try:
            logger.info(f"Fetching {data_type} data for {symbol} from Yahoo Finance")
            
            # Create ticker object
            ticker = yf.Ticker(symbol)
            
            if data_type == 'price':
                return self._fetch_price_data(ticker, symbol)
            elif data_type == 'info':
                return self._fetch_info_data(ticker, symbol)
            elif data_type == 'financials':
                return self._fetch_financial_data(ticker, symbol)
            else:
                return self._fetch_price_data(ticker, symbol)  # Default to price
                
        except Exception as e:
            logger.error(f"Error fetching Yahoo data for {symbol}: {str(e)}")
            return None
    
    def _fetch_price_data(self, ticker: yf.Ticker, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch current price data."""
        try:
            # Get current price data
            hist = ticker.history(period="2d", interval="1d")
            if hist.empty:
                logger.warning(f"No price data available for {symbol}")
                return None
            
            # Get current price
            current_price = hist['Close'].iloc[-1]
            previous_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            
            # Calculate change
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close > 0 else 0
            
            # Get additional info
            info = ticker.info
            
            return {
                'symbol': symbol,
                'price': float(current_price),
                'previous_close': float(previous_close),
                'change': float(change),
                'change_percent': float(change_percent),
                'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0,
                'market_cap': info.get('marketCap', 0),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'timestamp': datetime.now().isoformat(),
                'source': 'yahoo',
                'data_quality': 'live'
            }
            
        except Exception as e:
            logger.error(f"Error fetching price data for {symbol}: {str(e)}")
            return None
    
    def _fetch_info_data(self, ticker: yf.Ticker, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch company information."""
        try:
            info = ticker.info
            
            if not info:
                logger.warning(f"No info data available for {symbol}")
                return None
            
            return {
                'symbol': symbol,
                'name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'country': info.get('country', ''),
                'website': info.get('website', ''),
                'employees': info.get('fullTimeEmployees', 0),
                'description': info.get('longBusinessSummary', ''),
                'timestamp': datetime.now().isoformat(),
                'source': 'yahoo'
            }
            
        except Exception as e:
            logger.error(f"Error fetching info data for {symbol}: {str(e)}")
            return None
    
    def _fetch_financial_data(self, ticker: yf.Ticker, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch financial statement data."""
        try:
            # Get financial statements
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cashflow = ticker.cashflow
            
            if financials.empty:
                logger.warning(f"No financial data available for {symbol}")
                return None
            
            # Extract key metrics from latest period
            latest_period = financials.columns[0]
            
            return {
                'symbol': symbol,
                'period': latest_period.strftime('%Y-%m-%d'),
                'revenue': float(financials.loc['Total Revenue', latest_period]) if 'Total Revenue' in financials.index else 0,
                'net_income': float(financials.loc['Net Income', latest_period]) if 'Net Income' in financials.index else 0,
                'total_assets': float(balance_sheet.loc['Total Assets', latest_period]) if not balance_sheet.empty and 'Total Assets' in balance_sheet.index else 0,
                'total_debt': float(balance_sheet.loc['Total Debt', latest_period]) if not balance_sheet.empty and 'Total Debt' in balance_sheet.index else 0,
                'cash': float(balance_sheet.loc['Cash And Cash Equivalents', latest_period]) if not balance_sheet.empty and 'Cash And Cash Equivalents' in balance_sheet.index else 0,
                'free_cash_flow': float(cashflow.loc['Free Cash Flow', latest_period]) if not cashflow.empty and 'Free Cash Flow' in cashflow.index else 0,
                'timestamp': datetime.now().isoformat(),
                'source': 'yahoo'
            }
            
        except Exception as e:
            logger.error(f"Error fetching financial data for {symbol}: {str(e)}")
            return None
    
    def get_historical_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> Optional[Dict[str, Any]]:
        """
        Get historical price data.
        
        Args:
            symbol: Market symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            Dict containing historical data
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return None
            
            # Convert to list format for JSON serialization
            data = {
                'symbol': symbol,
                'period': period,
                'interval': interval,
                'data_points': len(hist),
                'start_date': hist.index[0].strftime('%Y-%m-%d'),
                'end_date': hist.index[-1].strftime('%Y-%m-%d'),
                'prices': hist['Close'].tolist(),
                'volumes': hist['Volume'].tolist() if 'Volume' in hist.columns else [],
                'dates': [d.strftime('%Y-%m-%d') for d in hist.index],
                'timestamp': datetime.now().isoformat(),
                'source': 'yahoo'
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """Test Yahoo Finance connection."""
        try:
            # Test with a simple request
            ticker = yf.Ticker('AAPL')
            hist = ticker.history(period="1d")
            return not hist.empty
        except Exception as e:
            logger.error(f"Yahoo Finance connection test failed: {str(e)}")
            return False
