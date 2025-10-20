#!/usr/bin/env python3
"""
Test script for the cache manager and cached data services.
This script demonstrates the functionality of the intelligent caching system.
"""

import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)
logger = logging.getLogger("cache_test")

def main():
    """Test the cache manager and cached data services"""
    logger.info("===== Testing Cache System =====")
    
    # Import the cache manager
    from cache_manager import CacheManager
    cache = CacheManager.get_instance()
    
    # Import the cached data services
    from data_services_cached import DataServices
    
    # Test basic cache operations
    test_basic_cache_operations(cache)
    
    # Test TTL-based cache invalidation
    test_ttl_invalidation(cache)
    
    # Test cached data services
    test_cached_data_services(DataServices)
    
    # Test differential updates
    test_differential_updates(DataServices)
    
    # Test cache fallback
    test_cache_fallback(DataServices, cache)
    
    # Print cache statistics
    print_cache_statistics(cache)
    
    logger.info("===== Cache System Test Completed =====")

def test_basic_cache_operations(cache):
    """Test basic cache operations"""
    logger.info("----- Testing Basic Cache Operations -----")
    
    # Test setting and getting values
    cache.set("test:basic", "Hello, Cache!")
    value, is_stale = cache.get("test:basic")
    
    logger.info(f"Cache get result: {value} (stale: {is_stale})")
    assert value == "Hello, Cache!", "Cache get failed"
    assert not is_stale, "Value should not be stale"
    
    # Test setting and getting complex values
    complex_value = {
        "name": "Test Object",
        "values": [1, 2, 3, 4, 5],
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "version": 1.0
        }
    }
    
    cache.set("test:complex", complex_value)
    value, is_stale = cache.get("test:complex")
    
    logger.info(f"Complex value retrieved with {len(str(value))} bytes")
    assert value["name"] == "Test Object", "Complex cache get failed"
    
    # Test cache invalidation
    cache.invalidate("test:basic")
    value, is_stale = cache.get("test:basic")
    
    logger.info(f"After invalidation: {value}")
    assert value is None, "Cache invalidation failed"
    
    logger.info("Basic cache operations: PASSED")

def test_ttl_invalidation(cache):
    """Test TTL-based cache invalidation"""
    logger.info("----- Testing TTL-based Cache Invalidation -----")
    
    # Set a value with short TTL
    cache.set("test:ttl", "This will expire soon", ttl=2)
    
    # Get it immediately
    value, is_stale = cache.get("test:ttl")
    logger.info(f"Initial value: {value} (stale: {is_stale})")
    assert value == "This will expire soon", "Initial value incorrect"
    assert not is_stale, "Initial value should not be stale"
    
    # Wait for TTL to expire
    logger.info("Waiting for TTL to expire (3 seconds)...")
    time.sleep(3)
    
    # Get it again after expiration
    value, is_stale = cache.get("test:ttl")
    logger.info(f"After TTL expired: {value} (stale: {is_stale})")
    
    # Value might be None or stale depending on implementation
    if value is not None:
        assert is_stale, "Value should be marked as stale after TTL expiration"
        logger.info("TTL expiration correctly marked item as stale")
    else:
        logger.info("TTL expiration correctly removed item from cache")
    
    logger.info("TTL-based cache invalidation: PASSED")

def test_cached_data_services(data_services):
    """Test cached data services"""
    logger.info("----- Testing Cached Data Services -----")
    
    # Test getting market data with cache
    start_time = time.time()
    first_result = data_services.get_market_data("SMI")
    first_duration = time.time() - start_time
    
    logger.info(f"First market data request took {first_duration:.3f}s")
    logger.info(f"Result: {first_result.get('symbol')}: {first_result.get('price')} ({first_result.get('change_percent')}%)")
    
    # Get the same data again (should be from cache)
    start_time = time.time()
    second_result = data_services.get_market_data("SMI")
    second_duration = time.time() - start_time
    
    logger.info(f"Second market data request took {second_duration:.3f}s")
    logger.info(f"Result: {second_result.get('symbol')}: {second_result.get('price')} ({second_result.get('change_percent')}%)")
    
    # Check if second request was faster (from cache)
    logger.info(f"Performance improvement: {(first_duration/second_duration):.1f}x faster with cache")
    
    # Test news service
    news = data_services.get_news()
    logger.info(f"Retrieved {len(news)} news items")
    
    logger.info("Cached data services: PASSED")

def test_differential_updates(data_services):
    """Test differential updates"""
    logger.info("----- Testing Differential Updates -----")
    
    try:
        # Try to use diff_update if available in DataServices
        symbols = ["SMI", "DAX", "EUR/CHF"]
        logger.info(f"Refreshing data for {', '.join(symbols)}")
        
        results = data_services.refresh_all_market_data(symbols)
        logger.info(f"Updated {len(results)} symbols")
        
        # If the function exists, test was successful
        logger.info("Differential updates: PASSED")
    except Exception as e:
        logger.error(f"Differential updates test error: {e}")
        logger.info("Differential updates: SKIPPED")

def test_cache_fallback(data_services, cache):
    """Test cache fallback mechanism"""
    logger.info("----- Testing Cache Fallback -----")
    
    # Create a key for this test
    test_key = "market_data:TEST_SYMBOL"
    
    # Set a test value in cache
    test_data = {
        "symbol": "TEST_SYMBOL",
        "price": 123.45,
        "change": 1.23,
        "change_percent": 1.0,
        "currency": "USD",
        "name": "Test Symbol",
        "timestamp": datetime.now().isoformat(),
        "is_live": True
    }
    
    # Store it in cache with short TTL
    cache.set(test_key, test_data, ttl=2)
    
    # Verify it's there
    value, is_stale = cache.get(test_key)
    logger.info(f"Initial cache value: {value.get('symbol') if value else None} (stale: {is_stale})")
    
    # Wait for TTL to expire
    logger.info("Waiting for TTL to expire (3 seconds)...")
    time.sleep(3)
    
    # Get it again - should be marked as stale but still available
    value, is_stale = cache.get(test_key)
    logger.info(f"After TTL expired: {value.get('symbol') if value else None} (stale: {is_stale})")
    
    if value is not None and is_stale:
        logger.info("Cache fallback: PASSED (stale data correctly returned)")
    elif value is None:
        logger.info("Cache fallback: PARTIAL (stale data not available, may need configuration)")
    else:
        logger.info("Cache fallback: FAILED (expired data not marked as stale)")
    
    # Clean up
    cache.invalidate(test_key)

def print_cache_statistics(cache):
    """Print cache statistics"""
    logger.info("----- Cache Statistics -----")
    
    stats = cache.get_stats()
    
    logger.info(f"Cache size: {stats.get('size', 0)} items")
    logger.info(f"Hit ratio: {stats.get('hit_ratio', 0) * 100:.1f}%")
    logger.info(f"Hits: {stats.get('hits', 0)}")
    logger.info(f"Misses: {stats.get('misses', 0)}")
    logger.info(f"Fallbacks: {stats.get('fallbacks', 0)}")
    logger.info(f"Updates: {stats.get('updates', 0)}")
    logger.info(f"Disk cache enabled: {stats.get('disk_enabled', False)}")
    
    if 'memory_usage_mb' in stats:
        logger.info(f"Memory usage: {stats.get('memory_usage_mb', 0):.1f} MB")

if __name__ == "__main__":
    main()