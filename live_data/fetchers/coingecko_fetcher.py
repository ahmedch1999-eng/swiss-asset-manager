"""
CoinGecko Fetcher

Fetches cryptocurrency data from CoinGecko API.
This is a reliable source for crypto prices, market data, and statistics.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)

class CoinGeckoFetcher(BaseFetcher):
    """
    CoinGecko cryptocurrency data fetcher.
    
    Provides access to real-time cryptocurrency prices,
    market data, and statistics.
    """
    
    def __init__(self):
        super().__init__('coingecko', rate_limit=1.0)  # 1 request per second
        self.base_url = "https://api.coingecko.com/api/v3"
        
        # CoinGecko coin ID mappings
        self.coin_mappings = {
            'BTC-USD': 'bitcoin',
            'ETH-USD': 'ethereum',
            'ADA-USD': 'cardano',
            'DOT-USD': 'polkadot',
            'LINK-USD': 'chainlink',
            'UNI-USD': 'uniswap',
            'SOL-USD': 'solana',
            'MATIC-USD': 'matic-network',
            'AVAX-USD': 'avalanche-2',
            'ATOM-USD': 'cosmos'
        }
    
    def fetch_data(self, symbol: str, data_type: str = 'price') -> Optional[Dict[str, Any]]:
        """
        Fetch cryptocurrency data from CoinGecko.
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC-USD', 'ETH-USD')
            data_type: Type of data ('price', 'market', 'info')
            
        Returns:
            Dict containing crypto data or None if failed
        """
        try:
            logger.info(f"Fetching {data_type} data for {symbol} from CoinGecko")
            
            # Get CoinGecko coin ID
            coin_id = self._get_coin_id(symbol)
            if not coin_id:
                logger.warning(f"No CoinGecko data available for {symbol}")
                return None
            
            if data_type == 'price':
                return self._fetch_price_data(coin_id, symbol)
            elif data_type == 'market':
                return self._fetch_market_data(coin_id, symbol)
            elif data_type == 'info':
                return self._fetch_info_data(coin_id, symbol)
            else:
                return self._fetch_price_data(coin_id, symbol)  # Default to price
                
        except Exception as e:
            logger.error(f"Error fetching CoinGecko data for {symbol}: {str(e)}")
            return None
    
    def _get_coin_id(self, symbol: str) -> Optional[str]:
        """Get CoinGecko coin ID from symbol."""
        return self.coin_mappings.get(symbol.upper())
    
    def _fetch_price_data(self, coin_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch current price data."""
        try:
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true',
                'include_market_cap': 'true'
            }
            
            response_data = self._make_request(url, params)
            if not response_data or coin_id not in response_data:
                return None
            
            coin_data = response_data[coin_id]
            
            return {
                'symbol': symbol,
                'price': float(coin_data.get('usd', 0)),
                'change_percent': float(coin_data.get('usd_24h_change', 0)),
                'volume': float(coin_data.get('usd_24h_vol', 0)),
                'market_cap': float(coin_data.get('usd_market_cap', 0)),
                'currency': 'USD',
                'timestamp': datetime.now().isoformat(),
                'source': 'coingecko',
                'data_quality': 'live'
            }
            
        except Exception as e:
            logger.error(f"Error fetching price data for {symbol}: {str(e)}")
            return None
    
    def _fetch_market_data(self, coin_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed market data."""
        try:
            url = f"{self.base_url}/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            }
            
            response_data = self._make_request(url, params)
            if not response_data:
                return None
            
            market_data = response_data.get('market_data', {})
            
            return {
                'symbol': symbol,
                'price': float(market_data.get('current_price', {}).get('usd', 0)),
                'market_cap': float(market_data.get('market_cap', {}).get('usd', 0)),
                'total_volume': float(market_data.get('total_volume', {}).get('usd', 0)),
                'price_change_24h': float(market_data.get('price_change_24h', 0)),
                'price_change_percentage_24h': float(market_data.get('price_change_percentage_24h', 0)),
                'market_cap_rank': market_data.get('market_cap_rank', 0),
                'circulating_supply': float(market_data.get('circulating_supply', 0)),
                'total_supply': float(market_data.get('total_supply', 0)),
                'max_supply': float(market_data.get('max_supply', 0)) if market_data.get('max_supply') else None,
                'currency': 'USD',
                'timestamp': datetime.now().isoformat(),
                'source': 'coingecko'
            }
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            return None
    
    def _fetch_info_data(self, coin_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch coin information."""
        try:
            url = f"{self.base_url}/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'false',
                'community_data': 'true',
                'developer_data': 'true',
                'sparkline': 'false'
            }
            
            response_data = self._make_request(url, params)
            if not response_data:
                return None
            
            return {
                'symbol': symbol,
                'name': response_data.get('name', ''),
                'symbol_cg': response_data.get('symbol', ''),
                'description': response_data.get('description', {}).get('en', ''),
                'website': response_data.get('links', {}).get('homepage', [''])[0],
                'github': response_data.get('links', {}).get('repos_url', {}).get('github', [''])[0],
                'twitter': response_data.get('links', {}).get('twitter_screen_name', ''),
                'reddit': response_data.get('links', {}).get('subreddit_url', ''),
                'categories': response_data.get('categories', []),
                'timestamp': datetime.now().isoformat(),
                'source': 'coingecko'
            }
            
        except Exception as e:
            logger.error(f"Error fetching info data for {symbol}: {str(e)}")
            return None
    
    def get_historical_data(self, symbol: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """
        Get historical price data.
        
        Args:
            symbol: Crypto symbol
            days: Number of days of historical data
            
        Returns:
            Dict containing historical data
        """
        try:
            coin_id = self._get_coin_id(symbol)
            if not coin_id:
                return None
            
            url = f"{self.base_url}/coins/{coin_id}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'daily' if days > 1 else 'hourly'
            }
            
            response_data = self._make_request(url, params)
            if not response_data:
                return None
            
            prices = response_data.get('prices', [])
            volumes = response_data.get('total_volumes', [])
            
            return {
                'symbol': symbol,
                'days': days,
                'data_points': len(prices),
                'prices': [price[1] for price in prices],
                'volumes': [volume[1] for volume in volumes],
                'dates': [datetime.fromtimestamp(price[0]/1000).strftime('%Y-%m-%d') for price in prices],
                'timestamp': datetime.now().isoformat(),
                'source': 'coingecko'
            }
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
    
    def get_trending_coins(self) -> Optional[Dict[str, Any]]:
        """Get trending cryptocurrencies."""
        try:
            url = f"{self.base_url}/search/trending"
            response_data = self._make_request(url)
            
            if not response_data:
                return None
            
            trending = response_data.get('coins', [])
            
            return {
                'trending_coins': [
                    {
                        'symbol': coin.get('item', {}).get('symbol', '').upper() + '-USD',
                        'name': coin.get('item', {}).get('name', ''),
                        'market_cap_rank': coin.get('item', {}).get('market_cap_rank', 0),
                        'thumb': coin.get('item', {}).get('thumb', '')
                    }
                    for coin in trending
                ],
                'timestamp': datetime.now().isoformat(),
                'source': 'coingecko'
            }
            
        except Exception as e:
            logger.error(f"Error fetching trending coins: {str(e)}")
            return None
    
    def get_available_coins(self) -> Dict[str, str]:
        """Get list of available cryptocurrencies."""
        return self.coin_mappings.copy()
    
    def test_connection(self) -> bool:
        """Test CoinGecko API connection."""
        try:
            # Test with Bitcoin
            test_data = self.fetch_data('BTC-USD')
            return test_data is not None and test_data.get('price', 0) > 0
        except Exception as e:
            logger.error(f"CoinGecko connection test failed: {str(e)}")
            return False
