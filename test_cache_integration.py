#!/usr/bin/env python3
"""
Test script for cache integration with the scheduler system.
This script validates that the cache system is properly integrated with the scheduler.
"""

import os
import logging
import time
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)
logger = logging.getLogger("integration_test")

def main():
    """Test the integration between the cache system and scheduler"""
    logger.info("===== Testing Cache Integration with Scheduler =====")
    
    # Step 1: Verify the scheduler cache integration module
    test_scheduler_cache_integration()
    
    # Step 2: Verify that the cache manager is initialized in the scheduler
    test_cache_initialization()
    
    # Step 3: Test cache warming with the scheduler
    test_cache_warming()
    
    # Step 4: Test data services with cache
    test_cached_data_services()
    
    logger.info("===== Cache Integration Tests Completed =====")

def test_scheduler_cache_integration():
    """Test the scheduler cache integration module"""
    logger.info("----- Testing Scheduler Cache Integration -----")
    
    try:
        from scheduler_cache_integration import get_cache_manager, get_cache_stats
        
        # Get the cache manager singleton
        cache_manager = get_cache_manager()
        if cache_manager is None:
            logger.error("Cache manager not initialized by scheduler_cache_integration")
            return False
        
        # Get cache stats
        stats = get_cache_stats()
        logger.info(f"Cache statistics retrieved: {json.dumps(stats, indent=2)}")
        
        logger.info("Scheduler cache integration: PASSED")
        return True
    except Exception as e:
        logger.error(f"Error testing scheduler cache integration: {e}")
        return False

def test_cache_initialization():
    """Test that the cache manager is initialized in the scheduler"""
    logger.info("----- Testing Cache Initialization in Scheduler -----")
    
    try:
        # Check if scheduler integration initializes the cache
        from scheduler_integration import init_scheduler
        from flask import Flask
        
        # Create a test Flask app
        test_app = Flask("test_app")
        
        # Initialize the scheduler (which should initialize the cache)
        init_scheduler(test_app)
        
        # Check if cache manager is attached to the app
        if hasattr(test_app, '_cache_manager'):
            logger.info("Cache manager successfully initialized by scheduler")
            logger.info("Cache initialization in scheduler: PASSED")
            return True
        else:
            logger.error("Cache manager not found in Flask app after scheduler initialization")
            return False
    except Exception as e:
        logger.error(f"Error testing cache initialization in scheduler: {e}")
        return False

def test_cache_warming():
    """Test cache warming with the scheduler"""
    logger.info("----- Testing Cache Warming -----")
    
    try:
        from scheduler_cache_integration import get_cache_manager
        from data_services_cached import DataServices
        
        # Get cache manager
        cache = get_cache_manager()
        
        # Register a warming task
        test_key = "test:warming"
        
        # Define a function that simulates data retrieval
        def get_test_data():
            logger.info("Test data retrieval function called")
            return {
                "timestamp": datetime.now().isoformat(),
                "value": "Test warming data"
            }
        
        # Schedule warming task with a short time_before
        cache.schedule_warming(
            test_key,
            get_test_data,
            time_before=1  # 1 second before expiry
        )
        
        # Set data with short TTL to trigger warming
        cache.set(test_key, {"initial": "data"}, ttl=2)
        
        # Wait for warming task to potentially run
        logger.info("Waiting for cache warming to occur...")
        time.sleep(3)
        
        # Check if warming tasks are being processed
        cache.process_warming_tasks()
        
        # Check if data was warmed
        value, is_stale = cache.get(test_key)
        
        if value and "value" in value and value["value"] == "Test warming data":
            logger.info("Cache warming successfully updated the data")
            logger.info("Cache warming: PASSED")
            return True
        else:
            logger.warning(f"Cache warming test inconclusive: {value}")
            return False
    except Exception as e:
        logger.error(f"Error testing cache warming: {e}")
        return False

def test_cached_data_services():
    """Test that data services use the cache"""
    logger.info("----- Testing Cached Data Services -----")
    
    try:
        from data_services_cached import DataServices
        
        # Test getting market data with cache
        logger.info("Getting market data with cache...")
        start_time = time.time()
        first_result = DataServices.get_market_data("SMI")
        first_duration = time.time() - start_time
        
        logger.info(f"First request took {first_duration:.3f}s")
        
        # Get the same data again (should be from cache)
        logger.info("Getting same market data again (should use cache)...")
        start_time = time.time()
        second_result = DataServices.get_market_data("SMI")
        second_duration = time.time() - start_time
        
        logger.info(f"Second request took {second_duration:.3f}s")
        
        # Check if second request was significantly faster
        if second_duration < first_duration / 10:
            logger.info(f"Cache provided significant speedup: {first_duration/second_duration:.1f}x faster")
            logger.info("Cached data services: PASSED")
            return True
        else:
            logger.warning(f"Cache did not provide expected speedup: {first_duration/second_duration:.1f}x")
            return False
    except Exception as e:
        logger.error(f"Error testing cached data services: {e}")
        return False

if __name__ == "__main__":
    main()