"""
Data services with intelligent caching.

This module provides data retrieval services with:
- TTL-based caching
- Differential updates
- Cache warming
- Fallback to stale data on API errors
"""

import os
import time
import json
import logging
import hashlib
import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import requests
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

from cache_manager import CacheManager, cached

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger('data_services')
handler = logging.FileHandler('logs/data_services.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Cache TTL settings (in seconds)
MARKET_DATA_TTL = int(os.environ.get('MARKET_DATA_TTL', 900))  # 15 minutes default
PORTFOLIO_DATA_TTL = int(os.environ.get('PORTFOLIO_DATA_TTL', 3600))  # 1 hour default
NEWS_DATA_TTL = int(os.environ.get('NEWS_DATA_TTL', 1800))  # 30 minutes default
FINANCIAL_DATA_TTL = int(os.environ.get('FINANCIAL_DATA_TTL', 86400))  # 24 hours default

# Get cache manager
cache = CacheManager.get_instance()


class DataServices:
    """Data services with intelligent caching."""
    
    @staticmethod
    def get_market_data(symbol: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get market data for a symbol with caching.
        
        Args:
            symbol: Market symbol to fetch
            use_cache: Whether to use cache (default: True)
            
        Returns:
            Market data dict with price, change, etc.
        """
        cache_key = f"market_data:{symbol}"
        
        if use_cache:
            # Try to get from cache
            data, is_stale = cache.get(cache_key)
            if data is not None:
                # Add stale flag if data is stale
                if is_stale:
                    data['is_stale'] = True
                return data
        
        # Not in cache or cache disabled, fetch fresh data
        try:
            # Try Yahoo Finance first
            yahoo_data = DataServices._fetch_yahoo_data(symbol)
            if yahoo_data:
                # Add source and timestamp
                yahoo_data['source'] = 'Yahoo Finance'
                yahoo_data['timestamp'] = datetime.datetime.now().isoformat()
                yahoo_data['is_live'] = True
                
                # Cache the data
                if use_cache:
                    cache.set(cache_key, yahoo_data, MARKET_DATA_TTL)
                    
                    # Schedule cache warming 5 minutes before expiry
                    cache.schedule_warming(
                        cache_key,
                        DataServices.get_market_data,
                        args=(symbol, False),  # Don't use cache for warming
                        time_before=300
                    )
                
                return yahoo_data
            
            # Try Alpha Vantage as fallback
            alpha_data = DataServices._fetch_alpha_vantage_data(symbol)
            if alpha_data:
                # Add source and timestamp
                alpha_data['source'] = 'Alpha Vantage'
                alpha_data['timestamp'] = datetime.datetime.now().isoformat()
                alpha_data['is_live'] = True
                
                # Cache the data
                if use_cache:
                    cache.set(cache_key, alpha_data, MARKET_DATA_TTL)
                    
                    # Schedule cache warming
                    cache.schedule_warming(
                        cache_key,
                        DataServices.get_market_data,
                        args=(symbol, False),
                        time_before=300
                    )
                
                return alpha_data
                
            # No data available from any source
            logger.warning(f"Could not fetch data for {symbol} from any source")
            return {'error': f"No data available for {symbol}", 'is_live': False}
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            
            # Try to get stale data from cache as fallback
            if use_cache:
                data, _ = cache.get(cache_key)
                if data is not None:
                    # Mark as stale and add error
                    data['is_stale'] = True
                    data['error'] = f"API Error: {str(e)}"
                    return data
            
            # No fallback available
            return {'error': f"Error fetching data: {str(e)}", 'is_live': False}
    
    @staticmethod
    def _fetch_yahoo_data(symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch data from Yahoo Finance."""
        try:
            # Symbol correction for Yahoo Finance
            yahoo_symbol = symbol
            
            # Handle special cases for symbol format
            if symbol.endswith('.SW') or symbol.startswith('^') or '=' in symbol:
                yahoo_symbol = symbol
            elif symbol in ['DAX', 'SMI', 'CAC', 'FTSE']:
                symbol_map = {
                    'DAX': '^GDAXI', 'SMI': '^SSMI', 
                    'CAC': '^FCHI', 'FTSE': '^FTSE'
                }
                yahoo_symbol = symbol_map.get(symbol, f"^{symbol}")
            
            logger.debug(f"Fetching from Yahoo Finance: {yahoo_symbol}")
            
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            hist = ticker.history(period="2d", interval="1d")
            
            if hist.empty:
                return None
            
            current_price = hist['Close'].iloc[-1]
            
            # Calculate previous close
            if len(hist) > 1:
                previous_close = hist['Close'].iloc[-2]
            else:
                previous_close = info.get('previousClose', current_price * 0.99)
            
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100
            
            return {
                "symbol": symbol,
                "yahoo_symbol": yahoo_symbol,
                "price": round(current_price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "currency": info.get('currency', 'USD'),
                "name": info.get('longName', info.get('shortName', symbol)),
                "volume": hist['Volume'].iloc[-1] if 'Volume' in hist else None,
                "market_cap": info.get('marketCap'),
                "fetch_time": time.time()
            }
        except Exception as e:
            logger.error(f"Yahoo Finance error for {symbol}: {e}")
            return None
    
    @staticmethod
    def _fetch_alpha_vantage_data(symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch data from Alpha Vantage API."""
        try:
            # Get API key from environment or use default demo key
            api_key = os.environ.get('ALPHA_VANTAGE_API_KEY', 'demo')
            
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if "Global Quote" in data:
                quote = data["Global Quote"]
                price = float(quote["05. price"])
                change = float(quote["09. change"])
                change_percent = float(quote["10. change percent"].rstrip('%'))
                
                return {
                    "symbol": symbol,
                    "price": price,
                    "change": change,
                    "change_percent": change_percent,
                    "currency": "USD",  # Alpha Vantage doesn't provide currency info
                    "name": symbol,
                    "volume": int(quote["06. volume"]) if "06. volume" in quote else None,
                    "fetch_time": time.time()
                }
            return None
        except Exception as e:
            logger.error(f"Alpha Vantage error for {symbol}: {e}")
            return None
    
    @staticmethod
    def refresh_all_market_data(symbols: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """Refresh all market data with differential updates.
        
        Args:
            symbols: List of symbols to refresh. If None or empty, will not load any data.
            
        Returns:
            Dictionary with refresh statistics
        """
        if not symbols:
            logger.info("No symbols specified for market data refresh, skipping...")
            return {
                "updated": 0,
                "stale": 0,
                "errors": 0,
                "time_taken": 0,
                "message": "No symbols provided, skipping data load"
            }
            
        # Limit the number of symbols to load at once (performance optimization)
        max_symbols = 10
        if len(symbols) > max_symbols:
            logger.info(f"Too many symbols requested ({len(symbols)}), limiting to {max_symbols}")
            symbols = symbols[:max_symbols]
            
        logger.info(f"Starting market data refresh for {len(symbols)} symbols")
        start_time = time.time()
        
        results = {}
        error_count = 0
        stale_count = 0
        updated_count = 0
        
        for symbol in symbols:
            try:
                # Use cache but handle differential updates
                cache_key = f"market_data:{symbol}"
                
                try:
                    # Get new data
                    data = DataServices.get_market_data_from_source(symbol)
                    
                    # If we got valid data
                    if data and 'error' not in data:
                        # Check if data exists in cache to compare
                        cached_data = cache.get(cache_key)
                        
                        if cached_data:
                            # Compare if data has changed meaningfully
                            if DataServices._has_market_data_changed(cached_data, data):
                                # Data changed, update cache
                                cache.set(cache_key, data, ttl=MARKET_DATA_TTL)
                                logger.info(f"Updated market data for {symbol}")
                                updated_count += 1
                            else:
                                # Data didn't change, just update timestamp
                                cache.touch(cache_key)
                                stale_count += 1
                        else:
                            # New data, set in cache
                            cache.set(cache_key, data, ttl=MARKET_DATA_TTL)
                            updated_count += 1
                    else:
                        logger.warning(f"Could not fetch data for {symbol} from any source")
                        error_count += 1
                except Exception as e:
                    logger.error(f"Error refreshing market data for {symbol}: {str(e)}")
                    error_count += 1
            except Exception as e:
                logger.error(f"Unexpected error handling {symbol}: {str(e)}")
                error_count += 1
                
        elapsed = time.time() - start_time
        logger.info(f"Market data refresh completed: {updated_count} updated, {stale_count} stale, {error_count} errors")
        
        return {
            "updated": updated_count,
            "stale": stale_count,
            "errors": error_count,
            "time_taken": elapsed
        }
    
    @staticmethod
    def get_news(use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get financial news with caching.
        
        Args:
            use_cache: Whether to use cache
            
        Returns:
            List of news items
        """
        cache_key = "financial_news"
        
        if use_cache:
            # Try to get from cache
            data, is_stale = cache.get(cache_key)
            if data is not None:
                # If data is stale but not too old, use it and mark as stale
                if is_stale:
                    for item in data:
                        item['is_stale'] = True
                return data
        
        try:
            # Fetch news from multiple sources
            news_items = DataServices._fetch_news()
            
            if news_items:
                # Cache the news items
                if use_cache:
                    cache.set(cache_key, news_items, NEWS_DATA_TTL)
                    
                    # Schedule warming
                    cache.schedule_warming(
                        cache_key,
                        DataServices.get_news,
                        args=(False,),
                        time_before=300
                    )
                
                return news_items
            
            # No news items
            return []
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            
            # Try to get stale data as fallback
            if use_cache:
                data, _ = cache.get(cache_key)
                if data is not None:
                    # Mark all items as stale
                    for item in data:
                        item['is_stale'] = True
                    return data
            
            # No fallback
            return []
    
    @staticmethod
    def _fetch_news() -> List[Dict[str, Any]]:
        """Fetch financial news from various sources."""
        # Implement news fetching from RSS feeds, APIs, etc.
        # This is a placeholder - actual implementation would depend on your news sources
        news_items = []
        
        # Add mock data - replace with actual news fetching logic
        news_items.append({
            'title': 'Market update: Stocks rally on positive economic data',
            'summary': 'Stock markets rallied today as economic data showed stronger than expected growth.',
            'source': 'Financial Times',
            'url': 'https://ft.com/markets',
            'published_at': datetime.datetime.now().isoformat(),
            'is_live': True
        })
        
        return news_items
    
    @staticmethod
    def get_historical_data(symbol: str, period: str = '1y', 
                           interval: str = '1d', use_cache: bool = True) -> Dict[str, Any]:
        """Get historical price data with caching.
        
        Args:
            symbol: Market symbol
            period: Time period (e.g., '1d', '1mo', '1y')
            interval: Data interval (e.g., '1m', '1h', '1d')
            use_cache: Whether to use cache
            
        Returns:
            Dict with historical data
        """
        cache_key = f"historical:{symbol}:{period}:{interval}"
        
        if use_cache:
            # Try to get from cache
            data, is_stale = cache.get(cache_key)
            if data is not None and not is_stale:
                return data
        
        try:
            # Fetch from Yahoo Finance
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                logger.warning(f"No historical data for {symbol}")
                return {'error': f"No historical data available for {symbol}"}
            
            # Convert to dict format for easy JSON serialization
            result = {
                'dates': hist.index.strftime('%Y-%m-%d').tolist(),
                'open': hist['Open'].tolist(),
                'high': hist['High'].tolist(),
                'low': hist['Low'].tolist(),
                'close': hist['Close'].tolist(),
                'volume': hist['Volume'].tolist() if 'Volume' in hist else [],
                'symbol': symbol,
                'period': period,
                'interval': interval,
                'fetch_time': time.time()
            }
            
            # Set longer TTL for historical data
            ttl = FINANCIAL_DATA_TTL
            
            # Cache the data
            if use_cache:
                cache.set(cache_key, result, ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            
            # Try to get stale data as fallback
            if use_cache:
                data, _ = cache.get(cache_key)
                if data is not None:
                    data['is_stale'] = True
                    return data
            
            # No fallback
            return {'error': f"Error fetching historical data: {str(e)}"}
    
    @staticmethod
    def get_portfolio_performance(portfolio_symbols: List[str], use_cache: bool = True) -> Dict[str, Any]:
        """Get portfolio performance data with caching.
        
        Args:
            portfolio_symbols: List of symbols in the portfolio
            use_cache: Whether to use cache
            
        Returns:
            Portfolio performance data
        """
        # Create a unique cache key based on the portfolio composition
        symbols_key = hashlib.md5(''.join(sorted(portfolio_symbols)).encode()).hexdigest()
        cache_key = f"portfolio:performance:{symbols_key}"
        
        if use_cache:
            # Try to get from cache
            data, is_stale = cache.get(cache_key)
            if data is not None and not is_stale:
                return data
        
        try:
            # Fetch historical data for all symbols
            start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
            end_date = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # Use pandas_datareader or yfinance for bulk data
            all_data = {}
            
            for symbol in portfolio_symbols:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1y")
                
                if not hist.empty:
                    all_data[symbol] = hist['Close']
            
            if not all_data:
                logger.warning("No portfolio data available")
                return {'error': "Could not fetch portfolio data"}
            
            # Create a DataFrame with all price data
            df = pd.DataFrame(all_data)
            
            # Calculate returns
            returns = df.pct_change().dropna()
            
            # Calculate portfolio metrics
            total_return = ((df.iloc[-1] / df.iloc[0]) - 1).mean() * 100
            volatility = returns.std().mean() * (252 ** 0.5) * 100  # Annualized
            sharpe = total_return / volatility if volatility > 0 else 0
            
            # Calculate correlation matrix
            corr_matrix = returns.corr().to_dict()
            
            # Format the result
            result = {
                'total_return': round(total_return, 2),
                'volatility': round(volatility, 2),
                'sharpe_ratio': round(sharpe, 2),
                'correlation': corr_matrix,
                'fetch_time': time.time(),
                'period': '1y'
            }
            
            # Cache the result
            if use_cache:
                cache.set(cache_key, result, PORTFOLIO_DATA_TTL)
                
                # Schedule warming
                cache.schedule_warming(
                    cache_key,
                    DataServices.get_portfolio_performance,
                    args=(portfolio_symbols, False),
                    time_before=300
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating portfolio performance: {e}")
            
            # Try to get stale data as fallback
            if use_cache:
                data, _ = cache.get(cache_key)
                if data is not None:
                    data['is_stale'] = True
                    return data
            
            # No fallback
            return {'error': f"Error calculating portfolio performance: {str(e)}"}

# Register for scheduled cache warming
def register_warming_tasks():
    """Register common tasks for cache warming."""
    # Example: pre-cache important market indices
    important_symbols = ['SPX', 'MSCIW', '^GSPC', 'SMI', 'DAX']
    for symbol in important_symbols:
        cache.schedule_warming(
            f"market_data:{symbol}",
            DataServices.get_market_data,
            args=(symbol, False),
            time_before=300
        )
    
    # Pre-cache news
    cache.schedule_warming(
        "financial_news",
        DataServices.get_news,
        args=(False,),
        time_before=300
    )

# Initialize warming tasks
register_warming_tasks()