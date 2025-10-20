"""
Data Validator - Validates data quality and consistency

This module provides comprehensive data validation to ensure that
fetched data meets quality standards before being stored or used.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Data validator for market data quality assurance.
    
    Validates data from different sources to ensure:
    - Data completeness
    - Value plausibility
    - Format consistency
    - Source reliability
    """
    
    def __init__(self):
        # Price validation thresholds
        self.price_thresholds = {
            'min_price': 0.001,  # Minimum reasonable price
            'max_price': 1000000,  # Maximum reasonable price
            'max_change_percent': 50,  # Maximum daily change
            'min_volume': 0,  # Minimum volume
            'max_volume': 1e15  # Maximum volume
        }
        
        # Currency validation
        self.valid_currencies = ['USD', 'CHF', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD']
        
        # Symbol validation patterns
        self.symbol_patterns = {
            'stock': r'^[A-Z]{1,5}(\.[A-Z]{2})?$',  # AAPL, NESN.SW
            'crypto': r'^[A-Z]{2,10}-USD$',  # BTC-USD
            'fx': r'^[A-Z]{3}[A-Z]{3}=X$',  # EURCHF=X
            'index': r'^\^[A-Z]{2,10}$',  # ^GSPC
            'commodity': r'^[A-Z]{1,3}=F$'  # GC=F
        }
    
    def validate_data(self, data: Dict[str, Any], symbol: str) -> bool:
        """
        Validate market data for a symbol.
        
        Args:
            data: Market data to validate
            symbol: Market symbol
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            if not data:
                logger.warning(f"Empty data for {symbol}")
                return False
            
            # Basic structure validation
            if not self._validate_structure(data, symbol):
                return False
            
            # Symbol validation
            if not self._validate_symbol(symbol):
                logger.warning(f"Invalid symbol format: {symbol}")
                return False
            
            # Price validation
            if not self._validate_price_data(data, symbol):
                return False
            
            # Currency validation
            if not self._validate_currency(data, symbol):
                return False
            
            # Volume validation
            if not self._validate_volume_data(data, symbol):
                return False
            
            # Timestamp validation
            if not self._validate_timestamp(data, symbol):
                return False
            
            # Source validation
            if not self._validate_source(data, symbol):
                return False
            
            logger.debug(f"Data validation passed for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating data for {symbol}: {str(e)}")
            return False
    
    def _validate_structure(self, data: Dict[str, Any], symbol: str) -> bool:
        """Validate basic data structure."""
        required_fields = ['symbol', 'price']
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field '{field}' for {symbol}")
                return False
        
        # Check if symbol matches
        if data.get('symbol') != symbol:
            logger.warning(f"Symbol mismatch: expected {symbol}, got {data.get('symbol')}")
            return False
        
        return True
    
    def _validate_symbol(self, symbol: str) -> bool:
        """Validate symbol format."""
        if not symbol or not isinstance(symbol, str):
            return False
        
        symbol_upper = symbol.upper()
        
        # Check against known patterns
        for pattern_name, pattern in self.symbol_patterns.items():
            if re.match(pattern, symbol_upper):
                return True
        
        # Allow some flexibility for edge cases
        if len(symbol_upper) <= 10 and symbol_upper.replace('.', '').replace('=', '').replace('^', '').replace('-', '').isalpha():
            return True
        
        return False
    
    def _validate_price_data(self, data: Dict[str, Any], symbol: str) -> bool:
        """Validate price-related data."""
        price = data.get('price', 0)
        
        # Check if price is a number
        if not isinstance(price, (int, float)):
            logger.warning(f"Invalid price type for {symbol}: {type(price)}")
            return False
        
        # Check price range
        if price < self.price_thresholds['min_price']:
            logger.warning(f"Price too low for {symbol}: {price}")
            return False
        
        if price > self.price_thresholds['max_price']:
            logger.warning(f"Price too high for {symbol}: {price}")
            return False
        
        # Validate change percentage if present
        change_percent = data.get('change_percent', 0)
        if isinstance(change_percent, (int, float)):
            if abs(change_percent) > self.price_thresholds['max_change_percent']:
                logger.warning(f"Change percentage too high for {symbol}: {change_percent}%")
                return False
        
        return True
    
    def _validate_currency(self, data: Dict[str, Any], symbol: str) -> bool:
        """Validate currency information."""
        currency = data.get('currency', 'USD')
        
        if currency not in self.valid_currencies:
            logger.warning(f"Invalid currency for {symbol}: {currency}")
            return False
        
        return True
    
    def _validate_volume_data(self, data: Dict[str, Any], symbol: str) -> bool:
        """Validate volume data."""
        volume = data.get('volume', 0)
        
        if volume is not None:
            if not isinstance(volume, (int, float)):
                logger.warning(f"Invalid volume type for {symbol}: {type(volume)}")
                return False
            
            if volume < self.price_thresholds['min_volume']:
                logger.warning(f"Volume too low for {symbol}: {volume}")
                return False
            
            if volume > self.price_thresholds['max_volume']:
                logger.warning(f"Volume too high for {symbol}: {volume}")
                return False
        
        return True
    
    def _validate_timestamp(self, data: Dict[str, Any], symbol: str) -> bool:
        """Validate timestamp data."""
        timestamp = data.get('timestamp')
        
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif isinstance(timestamp, datetime):
                    pass  # Already a datetime object
                else:
                    logger.warning(f"Invalid timestamp type for {symbol}: {type(timestamp)}")
                    return False
            except ValueError:
                logger.warning(f"Invalid timestamp format for {symbol}: {timestamp}")
                return False
        
        return True
    
    def _validate_source(self, data: Dict[str, Any], symbol: str) -> bool:
        """Validate data source information."""
        source = data.get('source')
        
        if not source:
            logger.warning(f"Missing source information for {symbol}")
            return False
        
        valid_sources = ['yahoo', 'snb', 'coingecko', 'simulation', 'cache']
        if source not in valid_sources:
            logger.warning(f"Unknown source for {symbol}: {source}")
            return False
        
        return True
    
    def calculate_quality_score(self, data: Dict[str, Any], symbol: str) -> float:
        """
        Calculate a data quality score (0-100).
        
        Args:
            data: Market data
            symbol: Market symbol
            
        Returns:
            Quality score between 0 and 100
        """
        try:
            score = 0
            max_score = 100
            
            # Basic structure (20 points)
            if self._validate_structure(data, symbol):
                score += 20
            
            # Price validation (30 points)
            if self._validate_price_data(data, symbol):
                score += 30
            
            # Currency validation (10 points)
            if self._validate_currency(data, symbol):
                score += 10
            
            # Volume validation (10 points)
            if self._validate_volume_data(data, symbol):
                score += 10
            
            # Timestamp validation (10 points)
            if self._validate_timestamp(data, symbol):
                score += 10
            
            # Source validation (10 points)
            if self._validate_source(data, symbol):
                score += 10
            
            # Additional quality checks
            if data.get('data_quality') == 'live':
                score += 5  # Bonus for live data
            
            if data.get('confidence_score', 0) > 50:
                score += 5  # Bonus for high confidence
            
            return min(score, max_score)
            
        except Exception as e:
            logger.error(f"Error calculating quality score for {symbol}: {str(e)}")
            return 0
    
    def validate_batch(self, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of data entries.
        
        Args:
            data_list: List of data dictionaries
            
        Returns:
            Validation results summary
        """
        results = {
            'total': len(data_list),
            'valid': 0,
            'invalid': 0,
            'errors': [],
            'quality_scores': []
        }
        
        for data in data_list:
            symbol = data.get('symbol', 'unknown')
            
            if self.validate_data(data, symbol):
                results['valid'] += 1
                quality_score = self.calculate_quality_score(data, symbol)
                results['quality_scores'].append(quality_score)
            else:
                results['invalid'] += 1
                results['errors'].append(f"Validation failed for {symbol}")
        
        # Calculate average quality score
        if results['quality_scores']:
            results['avg_quality_score'] = sum(results['quality_scores']) / len(results['quality_scores'])
        else:
            results['avg_quality_score'] = 0
        
        return results
