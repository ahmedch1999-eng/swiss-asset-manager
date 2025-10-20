"""
SNB (Swiss National Bank) Fetcher

Fetches Swiss Franc exchange rates from the Swiss National Bank.
This is the authoritative source for CHF exchange rates.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import requests

from .base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)

class SNBFetcher(BaseFetcher):
    """
    Swiss National Bank data fetcher.
    
    Provides access to official Swiss Franc exchange rates
    and other Swiss financial data.
    """
    
    def __init__(self):
        super().__init__('snb', rate_limit=2.0)  # Conservative rate limit for official API
        self.base_url = "https://data.snb.ch/api/cube"
    
    def fetch_data(self, symbol: str, data_type: str = 'price') -> Optional[Dict[str, Any]]:
        """
        Fetch Swiss Franc exchange rate data.
        
        Args:
            symbol: Currency pair (e.g., 'EURCHF=X', 'USDCHF=X')
            data_type: Type of data ('price', 'rates')
            
        Returns:
            Dict containing exchange rate data or None if failed
        """
        try:
            logger.info(f"Fetching {data_type} data for {symbol} from SNB")
            
            # Map symbol to SNB cube ID
            cube_id = self._get_cube_id(symbol)
            if not cube_id:
                logger.warning(f"No SNB data available for {symbol}")
                return None
            
            # Fetch data from SNB API
            data = self._fetch_snb_data(cube_id, symbol)
            if not data:
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching SNB data for {symbol}: {str(e)}")
            return None
    
    def _get_cube_id(self, symbol: str) -> Optional[str]:
        """Map currency symbol to SNB cube ID."""
        symbol_upper = symbol.upper()
        
        # SNB cube mappings for major currency pairs
        cube_mappings = {
            'EURCHF=X': 'am.USD.EUR.SP00',
            'USDCHF=X': 'am.USD.CHF.SP00',
            'GBPCHF=X': 'am.USD.GBP.SP00',
            'JPYCHF=X': 'am.USD.JPY.SP00',
            'CHFUSD=X': 'am.USD.CHF.SP00',  # Inverse of USD/CHF
            'CHFEUR=X': 'am.USD.EUR.SP00'   # Inverse of EUR/CHF
        }
        
        return cube_mappings.get(symbol_upper)
    
    def _fetch_snb_data(self, cube_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch data from SNB API."""
        try:
            # SNB API endpoint
            url = f"{self.base_url}/{cube_id}/data"
            
            # SNB API parameters
            params = {
                'format': 'json',
                'lang': 'en'
            }
            
            # Make request
            response_data = self._make_request(url, params)
            if not response_data:
                return None
            
            # Parse SNB response
            return self._parse_snb_response(response_data, symbol)
            
        except Exception as e:
            logger.error(f"Error fetching SNB data: {str(e)}")
            return None
    
    def _parse_snb_response(self, data: Dict[str, Any], symbol: str) -> Optional[Dict[str, Any]]:
        """Parse SNB API response."""
        try:
            # SNB response structure
            if 'data' not in data or not data['data']:
                return None
            
            # Get the latest data point
            latest_data = data['data'][-1] if data['data'] else None
            if not latest_data:
                return None
            
            # Extract rate information
            rate = latest_data.get('value', 0)
            if rate == 0:
                return None
            
            # Calculate change (simplified - would need historical data for accurate change)
            change = 0  # SNB doesn't provide change directly
            change_percent = 0
            
            return {
                'symbol': symbol,
                'rate': float(rate),
                'price': float(rate),  # For compatibility
                'change': float(change),
                'change_percent': float(change_percent),
                'currency': 'CHF',
                'source': 'snb',
                'timestamp': datetime.now().isoformat(),
                'data_quality': 'official',
                'description': f'Official SNB exchange rate for {symbol}'
            }
            
        except Exception as e:
            logger.error(f"Error parsing SNB response: {str(e)}")
            return None
    
    def get_available_currencies(self) -> Dict[str, str]:
        """Get list of available currency pairs from SNB."""
        return {
            'EURCHF=X': 'Euro to Swiss Franc',
            'USDCHF=X': 'US Dollar to Swiss Franc',
            'GBPCHF=X': 'British Pound to Swiss Franc',
            'JPYCHF=X': 'Japanese Yen to Swiss Franc'
        }
    
    def test_connection(self) -> bool:
        """Test SNB API connection."""
        try:
            # Test with EUR/CHF rate
            test_data = self.fetch_data('EURCHF=X')
            return test_data is not None and test_data.get('rate', 0) > 0
        except Exception as e:
            logger.error(f"SNB connection test failed: {str(e)}")
            return False
