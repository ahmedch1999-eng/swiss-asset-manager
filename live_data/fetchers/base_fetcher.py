"""
Base Fetcher - Abstract base class for all data fetchers

This module provides the common interface and functionality that all
data fetchers must implement.
"""

import time
import requests
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BaseFetcher(ABC):
    """
    Abstract base class for all data fetchers.
    
    Provides common functionality like rate limiting, error handling,
    and caching. All specific fetchers should inherit from this class.
    """
    
    def __init__(self, source_name: str, rate_limit: float = 1.0):
        """
        Initialize the fetcher.
        
        Args:
            source_name: Name of the data source
            rate_limit: Minimum seconds between requests
        """
        self.source_name = source_name
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.session = requests.Session()
        
        # Set common headers
        self.session.headers.update({
            'User-Agent': 'Swiss Asset Pro/1.0 (Educational Use)',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        # Request timeout
        self.timeout = 30
    
    @abstractmethod
    def fetch_data(self, symbol: str, data_type: str = 'price') -> Optional[Dict[str, Any]]:
        """
        Fetch data for a symbol.
        
        Args:
            symbol: Market symbol
            data_type: Type of data to fetch
            
        Returns:
            Dict containing the fetched data or None if failed
        """
        pass
    
    def _rate_limit_check(self):
        """Ensure we don't exceed rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Make a rate-limited HTTP request.
        
        Args:
            url: Request URL
            params: Query parameters
            
        Returns:
            JSON response data or None if failed
        """
        try:
            self._rate_limit_check()
            
            logger.debug(f"Making request to {url} with params: {params}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            # Try to parse as JSON
            try:
                return response.json()
            except ValueError:
                # If not JSON, return text content
                return {'content': response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {self.source_name}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in {self.source_name}: {str(e)}")
            return None
    
    def _validate_response(self, data: Dict[str, Any], symbol: str) -> bool:
        """
        Validate that the response contains expected data.
        
        Args:
            data: Response data
            symbol: Requested symbol
            
        Returns:
            True if data is valid, False otherwise
        """
        if not data:
            return False
        
        # Basic validation - should have some content
        if isinstance(data, dict) and len(data) == 0:
            return False
        
        return True
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format for the specific data source.
        
        Args:
            symbol: Original symbol
            
        Returns:
            Normalized symbol
        """
        return symbol.upper()
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get information about this data source."""
        return {
            'name': self.source_name,
            'rate_limit': self.rate_limit,
            'timeout': self.timeout,
            'last_request': datetime.fromtimestamp(self.last_request_time).isoformat() if self.last_request_time > 0 else None
        }
    
    def test_connection(self) -> bool:
        """
        Test if the data source is accessible.
        
        Returns:
            True if accessible, False otherwise
        """
        try:
            # This should be implemented by subclasses
            # For now, just return True
            return True
        except Exception as e:
            logger.error(f"Connection test failed for {self.source_name}: {str(e)}")
            return False
