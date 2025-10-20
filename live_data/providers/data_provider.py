"""
Data Provider - Main orchestrator for data sources

This class implements the core logic for deciding between live and simulated data.
It follows the fallback pattern: try live data first, fall back to simulation if needed.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..storage.data_store import DataStore
from ..validators.data_validator import DataValidator
from .fallback_provider import FallbackProvider
from ..fetchers.yahoo_fetcher import YahooFetcher
from ..fetchers.snb_fetcher import SNBFetcher
from ..fetchers.coingecko_fetcher import CoinGeckoFetcher

logger = logging.getLogger(__name__)

class DataProvider:
    """
    Main data provider that orchestrates between live and simulated data sources.
    
    Algorithm:
    1. Check if live data exists and is fresh (< 15 minutes old)
    2. If yes, use live data
    3. If no, check simulated data
    4. If neither available, return error and trigger recovery
    5. Log all decisions with source, timestamp, and confidence score
    """
    
    def __init__(self, data_store: DataStore, validator: DataValidator):
        self.data_store = data_store
        self.validator = validator
        self.fallback_provider = FallbackProvider()
        
        # Initialize fetchers
        self.fetchers = {
            'yahoo': YahooFetcher(),
            'snb': SNBFetcher(),
            'coingecko': CoinGeckoFetcher()
        }
        
        # Data freshness threshold (15 minutes)
        self.freshness_threshold = 15 * 60  # seconds
        
        # Source trust scores (0-100)
        self.trust_scores = {
            'yahoo': 85,
            'snb': 95,
            'coingecko': 80,
            'simulation': 30
        }
    
    def get_market_data(self, symbol: str, data_type: str = 'price') -> Dict[str, Any]:
        """
        Get market data for a symbol, trying live sources first.
        
        Args:
            symbol: Market symbol (e.g., 'AAPL', 'EURCHF=X', 'BTC-USD')
            data_type: Type of data ('price', 'volume', 'financials')
            
        Returns:
            Dict containing data with metadata about source and quality
        """
        try:
            # Step 1: Check for fresh live data
            live_data = self._get_fresh_live_data(symbol, data_type)
            if live_data:
                logger.info(f"Using live data for {symbol} from {live_data['source']}")
                return live_data
            
            # Step 2: Try to fetch new live data
            live_data = self._fetch_live_data(symbol, data_type)
            if live_data and self.validator.validate_data(live_data, symbol):
                # Store the fresh data
                self.data_store.store_market_data(symbol, live_data)
                logger.info(f"Fetched and stored fresh live data for {symbol}")
                return live_data
            
            # Step 3: Fall back to simulation
            simulated_data = self.fallback_provider.get_simulated_data(symbol, data_type)
            if simulated_data:
                simulated_data['source'] = 'simulation'
                simulated_data['confidence_score'] = self.trust_scores['simulation']
                simulated_data['fallback_reason'] = 'live_data_unavailable'
                logger.warning(f"Using simulated data for {symbol} - live data unavailable")
                return simulated_data
            
            # Step 4: No data available
            return self._create_error_response(symbol, "No data available from any source")
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {str(e)}")
            return self._create_error_response(symbol, str(e))
    
    def _get_fresh_live_data(self, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Check if we have fresh live data in the database."""
        try:
            data = self.data_store.get_latest_market_data(symbol, data_type)
            if not data:
                return None
            
            # Check if data is fresh
            fetched_at = data.get('fetched_at')
            if not fetched_at:
                return None
            
            if isinstance(fetched_at, str):
                fetched_at = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
            
            age_seconds = (datetime.now() - fetched_at).total_seconds()
            if age_seconds < self.freshness_threshold:
                data['source'] = 'cache'
                data['confidence_score'] = self.trust_scores.get(data.get('source', 'unknown'), 50)
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking fresh live data for {symbol}: {str(e)}")
            return None
    
    def _fetch_live_data(self, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Fetch fresh live data from appropriate source."""
        try:
            # Determine the best fetcher for this symbol
            fetcher = self._select_fetcher(symbol)
            if not fetcher:
                return None
            
            # Fetch data
            raw_data = fetcher.fetch_data(symbol, data_type)
            if not raw_data:
                return None
            
            # Normalize and validate data
            normalized_data = self._normalize_data(raw_data, symbol, fetcher.source_name)
            if not self.validator.validate_data(normalized_data, symbol):
                logger.warning(f"Data validation failed for {symbol}")
                return None
            
            # Add metadata
            normalized_data.update({
                'source': fetcher.source_name,
                'confidence_score': self.trust_scores.get(fetcher.source_name, 50),
                'fetched_at': datetime.now().isoformat(),
                'data_type': data_type
            })
            
            return normalized_data
            
        except Exception as e:
            logger.error(f"Error fetching live data for {symbol}: {str(e)}")
            return None
    
    def _select_fetcher(self, symbol: str):
        """Select the most appropriate fetcher for a symbol."""
        symbol_upper = symbol.upper()
        
        # Swiss stocks and indices
        if symbol_upper.endswith('.SW') or symbol_upper in ['^SSMI', '^SLI', '^SPI']:
            return self.fetchers.get('yahoo')  # Yahoo has good Swiss data
        
        # FX pairs
        if 'CHF' in symbol_upper or symbol_upper.endswith('=X'):
            return self.fetchers.get('snb')  # SNB for Swiss Franc pairs
        
        # Cryptocurrencies
        if symbol_upper in ['BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD']:
            return self.fetchers.get('coingecko')
        
        # Default to Yahoo for most other symbols
        return self.fetchers.get('yahoo')
    
    def _normalize_data(self, raw_data: Dict[str, Any], symbol: str, source: str) -> Dict[str, Any]:
        """Normalize data from different sources to a common format."""
        try:
            normalized = {
                'symbol': symbol,
                'source': source,
                'raw_data': raw_data
            }
            
            # Extract common fields based on source
            if source == 'yahoo':
                normalized.update({
                    'price': raw_data.get('price', 0),
                    'change': raw_data.get('change', 0),
                    'change_percent': raw_data.get('change_percent', 0),
                    'volume': raw_data.get('volume', 0),
                    'market_cap': raw_data.get('market_cap', 0),
                    'currency': raw_data.get('currency', 'USD')
                })
            elif source == 'snb':
                normalized.update({
                    'price': raw_data.get('rate', 0),
                    'change': raw_data.get('change', 0),
                    'change_percent': raw_data.get('change_percent', 0),
                    'currency': 'CHF'
                })
            elif source == 'coingecko':
                normalized.update({
                    'price': raw_data.get('current_price', 0),
                    'change_percent': raw_data.get('price_change_percentage_24h', 0),
                    'market_cap': raw_data.get('market_cap', 0),
                    'volume': raw_data.get('total_volume', 0),
                    'currency': 'USD'
                })
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing data for {symbol}: {str(e)}")
            return raw_data
    
    def _create_error_response(self, symbol: str, error_message: str) -> Dict[str, Any]:
        """Create a standardized error response."""
        return {
            'symbol': symbol,
            'error': error_message,
            'source': 'error',
            'confidence_score': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_source_status(self) -> Dict[str, Any]:
        """Get status of all data sources."""
        status = {}
        
        for name, fetcher in self.fetchers.items():
            try:
                # Test each fetcher with a simple request
                test_data = fetcher.fetch_data('AAPL', 'price') if name == 'yahoo' else None
                status[name] = {
                    'available': test_data is not None,
                    'trust_score': self.trust_scores.get(name, 0),
                    'last_check': datetime.now().isoformat()
                }
            except Exception as e:
                status[name] = {
                    'available': False,
                    'error': str(e),
                    'trust_score': self.trust_scores.get(name, 0),
                    'last_check': datetime.now().isoformat()
                }
        
        return status
    
    def trigger_recovery_job(self, source: str, symbol: str):
        """Trigger a background job to recover from source failures."""
        logger.info(f"Triggering recovery job for {source} with symbol {symbol}")
        # This would typically queue a background job
        # For now, we'll just log it
        pass
