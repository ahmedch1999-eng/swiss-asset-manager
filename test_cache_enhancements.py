#!/usr/bin/env python
"""
Test script for enhanced cache functionality.
This script tests the compression, LRU eviction, and dynamic TTL features
added by cache_enhancements.py
"""

import os
import time
import sys
import logging
import random
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/test_cache_enhancements.log')
    ]
)
logger = logging.getLogger('test_cache_enhancements')

# Import the cache systems
from cache_manager import CacheManager
import cache_enhancements
from cache_enhancements import EnhancedCacheManager

def generate_test_data(size_kb):
    """Generate random test data of approximately size_kb kilobytes"""
    # Each character is roughly 1 byte
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=size_kb * 1024))

def print_separator(title):
    """Print a separator with title"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def test_compression():
    """Test the compression feature"""
    print_separator("COMPRESSION TEST")
    
    # Get enhanced cache manager
    cache = EnhancedCacheManager.get_instance()
    
    # Set compression threshold to 5KB for testing
    cache.compression_threshold = 5 * 1024
    
    # Test with different data sizes
    sizes = [1, 5, 10, 50, 100]
    results = []
    
    for size in sizes:
        # Generate test data
        test_key = f"compression_test:{size}kb"
        test_data = generate_test_data(size)
        data_size = len(test_data)
        
        # Store in cache
        start_time = time.time()
        cache.set(test_key, test_data)
        set_time = time.time() - start_time
        
        # Get from cache
        start_time = time.time()
        retrieved_data, is_stale = cache.get(test_key)
        get_time = time.time() - start_time
        
        # Check if data is correct
        is_correct = test_data == retrieved_data
        
        # Check if item was compressed
        cache_item = cache.cache.get(test_key)
        was_compressed = hasattr(cache_item, 'is_compressed') and cache_item.is_compressed
        
        compressed_size = len(cache_item._value) if was_compressed else data_size
        compression_ratio = data_size / compressed_size if was_compressed else 1.0
        
        # Record results
        results.append({
            'size_kb': size,
            'was_compressed': was_compressed,
            'original_bytes': data_size,
            'stored_bytes': compressed_size,
            'compression_ratio': compression_ratio,
            'set_time_ms': set_time * 1000,
            'get_time_ms': get_time * 1000,
            'is_correct': is_correct
        })
        
        logger.info(f"Tested {size}KB: compressed={was_compressed}, ratio={compression_ratio:.2f}x")
    
    # Print results table
    print("\nCompression Test Results:")
    print(f"{'Size (KB)':<10} {'Compressed':<12} {'Ratio':<10} {'Set (ms)':<10} {'Get (ms)':<10}")
    print("-" * 60)
    
    for result in results:
        print(f"{result['size_kb']:<10} {str(result['was_compressed']):<12} {result['compression_ratio']:.2f}x" +
              f"{result['set_time_ms']:.2f}ms".rjust(12) + 
              f"{result['get_time_ms']:.2f}ms".rjust(12))
    
    # Verify all data is correct
    all_correct = all(r['is_correct'] for r in results)
    print(f"\nAll data retrieved correctly: {all_correct}")
    
    return all_correct

def test_lru_eviction():
    """Test the LRU eviction policy"""
    print_separator("LRU EVICTION TEST")
    
    # Get enhanced cache manager
    cache = EnhancedCacheManager.get_instance()
    
    # Set a small cache size limit for testing
    original_limit = cache.cache_size_limit
    cache.cache_size_limit = 10
    
    try:
        # Clear cache for clean test
        cache.cache.clear()
        
        # Add items
        for i in range(20):
            cache.set(f"lru_test:{i}", f"Value {i}")
            logger.info(f"Added item {i}, cache size: {len(cache.cache)}")
        
        # Check how many items were kept
        kept_items = len(cache.cache)
        print(f"\nItems kept in cache: {kept_items} (limit was {cache.cache_size_limit})")
        
        # List the kept items - should be the most recently added
        kept_keys = list(cache.cache.keys())
        print(f"Kept keys: {kept_keys}")
        
        # Access some older items to change their LRU status
        access_keys = ["lru_test:1", "lru_test:3", "lru_test:5"]
        for key in access_keys:
            if key in cache.cache:
                value, _ = cache.get(key)
                print(f"Accessed {key}: {value}")
        
        # Add more items to trigger eviction again
        for i in range(20, 25):
            cache.set(f"lru_test:{i}", f"Value {i}")
        
        # Check which items were kept after the second eviction
        final_kept_keys = list(cache.cache.keys())
        print(f"Final kept keys: {final_kept_keys}")
        
        # The accessed items should still be in cache
        accessed_items_kept = sum(1 for key in access_keys if key in final_kept_keys)
        print(f"Accessed items still in cache: {accessed_items_kept}/{len(access_keys)}")
        
        eviction_working = accessed_items_kept > 0 and len(cache.cache) <= cache.cache_size_limit
        print(f"LRU eviction working correctly: {eviction_working}")
        
        return eviction_working
    
    finally:
        # Restore original limit
        cache.cache_size_limit = original_limit

def test_dynamic_ttl():
    """Test the dynamic TTL adjustment"""
    print_separator("DYNAMIC TTL TEST")
    
    # Get enhanced cache manager
    cache = EnhancedCacheManager.get_instance()
    
    # Add test items with different categories
    cache.set("market_data:test1", "Market data 1", ttl=600)
    cache.set("news:test1", "News data 1", ttl=1800)
    cache.set("other:test1", "Other data 1", ttl=3600)
    
    # Get initial TTLs
    initial_ttls = {
        "market": cache.cache["market_data:test1"].ttl,
        "news": cache.cache["news:test1"].ttl,
        "other": cache.cache["other:test1"].ttl
    }
    
    print(f"Initial TTLs: {json.dumps(initial_ttls, indent=2)}")
    
    # Simulate market hours adjustment
    print("\nSimulating market hours adjustment...")
    cache._adjust_ttls(market_data_multiplier=0.5, news_multiplier=0.7)
    
    # Get adjusted TTLs
    market_hours_ttls = {
        "market": cache.cache["market_data:test1"].ttl,
        "news": cache.cache["news:test1"].ttl,
        "other": cache.cache["other:test1"].ttl
    }
    
    print(f"Market hours TTLs: {json.dumps(market_hours_ttls, indent=2)}")
    
    # Simulate non-market hours adjustment
    print("\nSimulating non-market hours adjustment...")
    cache._adjust_ttls(market_data_multiplier=2.0, news_multiplier=1.5)
    
    # Get adjusted TTLs
    non_market_hours_ttls = {
        "market": cache.cache["market_data:test1"].ttl,
        "news": cache.cache["news:test1"].ttl,
        "other": cache.cache["other:test1"].ttl
    }
    
    print(f"Non-market hours TTLs: {json.dumps(non_market_hours_ttls, indent=2)}")
    
    # Verify that market and news TTLs changed but other stayed the same
    market_changed = market_hours_ttls["market"] != initial_ttls["market"]
    news_changed = market_hours_ttls["news"] != initial_ttls["news"]
    other_unchanged = market_hours_ttls["other"] == initial_ttls["other"]
    
    all_correct = market_changed and news_changed and other_unchanged
    print(f"\nDynamic TTL working correctly: {all_correct}")
    
    return all_correct

def test_memory_monitoring():
    """Test memory monitoring and stats"""
    print_separator("MEMORY MONITORING TEST")
    
    # Get enhanced cache manager
    cache = EnhancedCacheManager.get_instance()
    
    # Get initial stats
    initial_stats = cache.get_enhanced_stats()
    print(f"Initial stats:\n{json.dumps(initial_stats, indent=2)}")
    
    # Add some large items to trigger memory pressure
    print("\nAdding large items to cache...")
    large_data = generate_test_data(500)  # 500KB
    for i in range(5):
        cache.set(f"memory_test:large:{i}", large_data)
    
    # Force memory check
    cache.last_memory_check = 0
    memory_pressure = cache._check_memory_pressure()
    print(f"Memory pressure detected: {memory_pressure}")
    
    # Get updated stats
    updated_stats = cache.get_enhanced_stats()
    print(f"\nUpdated stats:\n{json.dumps(updated_stats, indent=2)}")
    
    # Check if memory monitoring is working
    monitoring_working = (
        'memory_usage_mb' in updated_stats and
        'memory_limit' in updated_stats
    )
    
    print(f"Memory monitoring working: {monitoring_working}")
    
    return monitoring_working

def test_cache_metrics():
    """Test cache metrics collection"""
    print_separator("CACHE METRICS TEST")
    
    # Get enhanced cache manager
    cache = EnhancedCacheManager.get_instance()
    
    # Reset some stats for clean test
    cache.statistics['hits'] = 0
    cache.statistics['misses'] = 0
    
    # Perform cache operations
    print("Performing cache operations...")
    
    # Add some items
    for i in range(10):
        cache.set(f"metrics_test:{i}", f"Value {i}")
    
    # Get existing items (hits)
    for i in range(5):
        cache.get(f"metrics_test:{i}")
    
    # Get non-existent items (misses)
    for i in range(100, 105):
        cache.get(f"metrics_test:{i}")
    
    # Get metrics
    metrics = cache.get_enhanced_stats()
    
    print(f"\nCache hits: {metrics['hits']}")
    print(f"Cache misses: {metrics['misses']}")
    print(f"Hit ratio: {metrics['hit_ratio']:.2f}")
    
    # Verify metrics
    metrics_correct = (
        metrics['hits'] == 5 and
        metrics['misses'] == 5 and
        abs(metrics['hit_ratio'] - 0.5) < 0.01
    )
    
    print(f"\nMetrics collection working correctly: {metrics_correct}")
    
    # Print enhanced metrics
    print("\nEnhanced metrics:")
    enhanced_keys = ['compressions', 'evictions', 'memory_alerts', 
                    'compressed_items', 'compressed_ratio', 'memory_saved']
    
    for key in enhanced_keys:
        if key in metrics:
            print(f"{key}: {metrics[key]}")
    
    return metrics_correct

def main():
    """Run all tests"""
    print_separator("ENHANCED CACHE SYSTEM TESTS")
    print(f"Starting tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    results = {}
    
    try:
        # Test compression
        results['compression'] = test_compression()
        
        # Test LRU eviction
        results['lru_eviction'] = test_lru_eviction()
        
        # Test dynamic TTL
        results['dynamic_ttl'] = test_dynamic_ttl()
        
        # Test memory monitoring
        results['memory_monitoring'] = test_memory_monitoring()
        
        # Test cache metrics
        results['cache_metrics'] = test_cache_metrics()
        
        # Print final results
        print_separator("TEST RESULTS")
        
        for test, passed in results.items():
            status = "PASSED" if passed else "FAILED"
            print(f"{test:20}: {status}")
        
        all_passed = all(results.values())
        print(f"\nOverall result: {'PASSED' if all_passed else 'FAILED'}")
        
        print(f"\nTests completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0 if all_passed else 1
        
    except Exception as e:
        logger.error(f"Error during tests: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())