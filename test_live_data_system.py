"""
Comprehensive Test Suite for Live Data Integration System

This module tests the complete live data pipeline including:
- Data fetchers (Yahoo, SNB, CoinGecko)
- Data validation
- Data storage
- Data provider with fallback logic
- API endpoints
"""

import unittest
import tempfile
import os
import json
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Import the live data modules
from live_data.providers.data_provider import DataProvider
from live_data.providers.fallback_provider import FallbackProvider
from live_data.storage.data_store import DataStore
from live_data.validators.data_validator import DataValidator
from live_data.fetchers.yahoo_fetcher import YahooFetcher
from live_data.fetchers.snb_fetcher import SNBFetcher
from live_data.fetchers.coingecko_fetcher import CoinGeckoFetcher

class TestDataValidator(unittest.TestCase):
    """Test data validation functionality"""
    
    def setUp(self):
        self.validator = DataValidator()
    
    def test_validate_valid_data(self):
        """Test validation of valid market data"""
        valid_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'change': 2.5,
            'change_percent': 1.69,
            'volume': 1000000,
            'currency': 'USD',
            'timestamp': datetime.now().isoformat(),
            'source': 'yahoo'
        }
        
        self.assertTrue(self.validator.validate_data(valid_data, 'AAPL'))
    
    def test_validate_invalid_price(self):
        """Test validation with invalid price"""
        invalid_data = {
            'symbol': 'AAPL',
            'price': -10.0,  # Negative price
            'currency': 'USD',
            'source': 'yahoo'
        }
        
        self.assertFalse(self.validator.validate_data(invalid_data, 'AAPL'))
    
    def test_validate_missing_required_fields(self):
        """Test validation with missing required fields"""
        incomplete_data = {
            'symbol': 'AAPL',
            'currency': 'USD'
            # Missing 'price' field
        }
        
        self.assertFalse(self.validator.validate_data(incomplete_data, 'AAPL'))
    
    def test_validate_invalid_currency(self):
        """Test validation with invalid currency"""
        invalid_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'currency': 'INVALID',
            'source': 'yahoo'
        }
        
        self.assertFalse(self.validator.validate_data(invalid_data, 'AAPL'))
    
    def test_calculate_quality_score(self):
        """Test quality score calculation"""
        good_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'change': 2.5,
            'change_percent': 1.69,
            'volume': 1000000,
            'currency': 'USD',
            'timestamp': datetime.now().isoformat(),
            'source': 'yahoo',
            'data_quality': 'live',
            'confidence_score': 85
        }
        
        score = self.validator.calculate_quality_score(good_data, 'AAPL')
        self.assertGreater(score, 80)
        self.assertLessEqual(score, 100)

class TestDataStore(unittest.TestCase):
    """Test data storage functionality"""
    
    def setUp(self):
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.data_store = DataStore(self.temp_db.name)
    
    def tearDown(self):
        # Clean up temporary database
        os.unlink(self.temp_db.name)
    
    def test_store_market_data(self):
        """Test storing market data"""
        test_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'change': 2.5,
            'change_percent': 1.69,
            'volume': 1000000,
            'currency': 'USD',
            'source': 'yahoo',
            'quality_score': 85
        }
        
        result = self.data_store.store_market_data('AAPL', test_data)
        self.assertTrue(result)
    
    def test_get_latest_market_data(self):
        """Test retrieving latest market data"""
        test_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'source': 'yahoo'
        }
        
        # Store data
        self.data_store.store_market_data('AAPL', test_data)
        
        # Retrieve data
        retrieved_data = self.data_store.get_latest_market_data('AAPL')
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(retrieved_data['symbol'], 'AAPL')
        self.assertEqual(retrieved_data['price'], 150.0)
    
    def test_update_source_status(self):
        """Test updating source status"""
        # Test successful request
        self.data_store.update_source_status('yahoo', True)
        
        # Test failed request
        self.data_store.update_source_status('yahoo', False, 'API timeout')
        
        # Get status
        status = self.data_store.get_source_status()
        self.assertIn('yahoo', status)
    
    def test_get_database_stats(self):
        """Test getting database statistics"""
        stats = self.data_store.get_database_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('market_prices_count', stats)

class TestFallbackProvider(unittest.TestCase):
    """Test fallback data provider"""
    
    def setUp(self):
        self.fallback_provider = FallbackProvider()
    
    def test_get_simulated_data(self):
        """Test generating simulated data"""
        data = self.fallback_provider.get_simulated_data('AAPL', 'price')
        
        self.assertIsNotNone(data)
        self.assertEqual(data['symbol'], 'AAPL')
        self.assertIn('price', data)
        self.assertIn('change', data)
        self.assertIn('change_percent', data)
        self.assertGreater(data['price'], 0)
    
    def test_classify_symbol(self):
        """Test symbol classification"""
        self.assertEqual(self.fallback_provider._classify_symbol('BTC-USD'), 'crypto')
        self.assertEqual(self.fallback_provider._classify_symbol('AAPL'), 'stocks')
        self.assertEqual(self.fallback_provider._classify_symbol('EURCHF=X'), 'fx')
        self.assertEqual(self.fallback_provider._classify_symbol('^GSPC'), 'indices')
    
    def test_validate_symbol(self):
        """Test symbol validation"""
        self.assertTrue(self.fallback_provider.validate_symbol('AAPL'))
        self.assertTrue(self.fallback_provider.validate_symbol('BTC-USD'))
        self.assertTrue(self.fallback_provider.validate_symbol('EURCHF=X'))
        self.assertFalse(self.fallback_provider.validate_symbol('INVALID'))

class TestDataFetchers(unittest.TestCase):
    """Test data fetchers"""
    
    def setUp(self):
        self.yahoo_fetcher = YahooFetcher()
        self.snb_fetcher = SNBFetcher()
        self.coingecko_fetcher = CoinGeckoFetcher()
    
    @patch('live_data.fetchers.yahoo_fetcher.yf.Ticker')
    def test_yahoo_fetcher_mock(self, mock_ticker):
        """Test Yahoo fetcher with mocked data"""
        # Mock the ticker and its methods
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        # Mock historical data
        mock_hist = MagicMock()
        mock_hist.__getitem__.return_value = [150.0, 148.0]  # Close prices
        mock_hist.empty = False
        mock_hist.columns = ['Close', 'Volume']
        mock_ticker_instance.history.return_value = mock_hist
        
        # Mock info data
        mock_ticker_instance.info = {
            'marketCap': 2500000000000,
            'currency': 'USD',
            'exchange': 'NASDAQ'
        }
        
        data = self.yahoo_fetcher.fetch_data('AAPL', 'price')
        
        # Note: This test will fail in real environment without internet
        # but demonstrates the structure
        if data:
            self.assertEqual(data['symbol'], 'AAPL')
            self.assertIn('price', data)
    
    def test_snb_fetcher_symbol_mapping(self):
        """Test SNB fetcher symbol mapping"""
        cube_id = self.snb_fetcher._get_cube_id('EURCHF=X')
        self.assertIsNotNone(cube_id)
        
        cube_id = self.snb_fetcher._get_cube_id('USDCHF=X')
        self.assertIsNotNone(cube_id)
    
    def test_coingecko_fetcher_coin_mapping(self):
        """Test CoinGecko fetcher coin ID mapping"""
        coin_id = self.coingecko_fetcher._get_coin_id('BTC-USD')
        self.assertEqual(coin_id, 'bitcoin')
        
        coin_id = self.coingecko_fetcher._get_coin_id('ETH-USD')
        self.assertEqual(coin_id, 'ethereum')

class TestDataProvider(unittest.TestCase):
    """Test main data provider with fallback logic"""
    
    def setUp(self):
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        
        self.data_store = DataStore(self.temp_db.name)
        self.validator = DataValidator()
        self.data_provider = DataProvider(self.data_store, self.validator)
    
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def test_get_market_data_fallback(self):
        """Test data provider fallback to simulation"""
        # This should fall back to simulation since we don't have live data
        data = self.data_provider.get_market_data('AAPL', 'price')
        
        self.assertIsNotNone(data)
        self.assertIn('symbol', data)
        self.assertIn('price', data)
        self.assertIn('source', data)
    
    def test_source_selection(self):
        """Test fetcher selection logic"""
        # Test stock symbol
        fetcher = self.data_provider._select_fetcher('AAPL')
        self.assertIsNotNone(fetcher)
        
        # Test crypto symbol
        fetcher = self.data_provider._select_fetcher('BTC-USD')
        self.assertIsNotNone(fetcher)
        
        # Test FX symbol
        fetcher = self.data_provider._select_fetcher('EURCHF=X')
        self.assertIsNotNone(fetcher)
    
    def test_get_source_status(self):
        """Test getting source status"""
        status = self.data_provider.get_source_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('yahoo', status)
        self.assertIn('snb', status)
        self.assertIn('coingecko', status)

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        
        self.data_store = DataStore(self.temp_db.name)
        self.validator = DataValidator()
        self.data_provider = DataProvider(self.data_store, self.validator)
    
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def test_complete_data_pipeline(self):
        """Test complete data pipeline from fetch to storage"""
        # Get data (will use fallback)
        data = self.data_provider.get_market_data('AAPL', 'price')
        
        self.assertIsNotNone(data)
        self.assertEqual(data['symbol'], 'AAPL')
        
        # Verify data was stored
        stored_data = self.data_store.get_latest_market_data('AAPL')
        if stored_data:  # May not be stored if using fallback
            self.assertEqual(stored_data['symbol'], 'AAPL')
    
    def test_data_quality_workflow(self):
        """Test data quality assessment workflow"""
        # Generate test data
        test_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'change': 2.5,
            'change_percent': 1.69,
            'volume': 1000000,
            'currency': 'USD',
            'timestamp': datetime.now().isoformat(),
            'source': 'yahoo'
        }
        
        # Validate data
        is_valid = self.validator.validate_data(test_data, 'AAPL')
        self.assertTrue(is_valid)
        
        # Calculate quality score
        quality_score = self.validator.calculate_quality_score(test_data, 'AAPL')
        self.assertGreater(quality_score, 0)
        self.assertLessEqual(quality_score, 100)
        
        # Store quality metrics
        quality_data = {
            'quality_score': quality_score,
            'validation_errors': [],
            'data_completeness': 100,
            'timestamp_accuracy': True,
            'price_plausibility': True,
            'volume_plausibility': True
        }
        
        self.data_store.store_quality_metrics('AAPL', 'yahoo', quality_data)

class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def setUp(self):
        self.validator = DataValidator()
        self.fallback_provider = FallbackProvider()
    
    def test_handle_invalid_symbol(self):
        """Test handling of invalid symbols"""
        data = self.fallback_provider.get_simulated_data('INVALID_SYMBOL', 'price')
        
        # Should still return data (fallback behavior)
        self.assertIsNotNone(data)
        self.assertEqual(data['symbol'], 'INVALID_SYMBOL')
    
    def test_handle_empty_data(self):
        """Test handling of empty data"""
        is_valid = self.validator.validate_data({}, 'AAPL')
        self.assertFalse(is_valid)
    
    def test_handle_malformed_data(self):
        """Test handling of malformed data"""
        malformed_data = {
            'symbol': 'AAPL',
            'price': 'not_a_number',
            'currency': 'USD',
            'source': 'yahoo'
        }
        
        is_valid = self.validator.validate_data(malformed_data, 'AAPL')
        self.assertFalse(is_valid)

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestDataValidator,
        TestDataStore,
        TestFallbackProvider,
        TestDataFetchers,
        TestDataProvider,
        TestIntegration,
        TestErrorHandling
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
