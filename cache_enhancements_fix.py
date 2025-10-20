"""
Cache Enhancements Fix

This module implements a quick fix to speed up page loading by:
1. Implementing aggressive initial caching
2. Ensuring the cache system is properly initialized
3. Adding forced stale data fallback for initial page load
"""

import logging
import os
import time
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger('cache_fix')
handler = logging.FileHandler('logs/cache_fix.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def apply_quick_cache_fix():
    """
    Apply quick fixes to the cache system for better performance
    """
    logger.info("Applying quick cache fix for faster initial loading...")
    
    try:
        # Import modules carefully to avoid circular imports
        from cache_manager import CacheManager
        from enhanced_cache_integration import get_enhanced_cache_manager
        
        # Get the active cache manager
        cache = get_enhanced_cache_manager()
        if not cache:
            logger.warning("Enhanced cache manager not found, using default")
            cache = CacheManager.get_instance()
        
        # 1. Increase stale data tolerance for initial page load
        # This allows using older cached data to avoid API calls during startup
        cache.initial_load_mode = True
        cache.stale_data_fallback_ttl = 86400  # Accept up to 1 day old data for initial load
        
        # 2. Force cache check on startup to ensure disk cache is loaded
        cache_dir = 'cache'
        if os.path.exists(cache_dir):
            cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.cache')]
            logger.info(f"Found {len(cache_files)} cache files on disk")
            
            # Pre-load critical cache files into memory
            critical_prefixes = ['market_data_', 'financial_news.']
            for cache_file in cache_files:
                if any(cache_file.startswith(prefix) for prefix in critical_prefixes):
                    key = cache_file.replace('_', ':').replace('.cache', '')
                    # Force load from disk without API calls
                    try:
                        value = cache._load_from_disk(key)
                        if value is not None:
                            logger.info(f"Pre-loaded {key} from disk cache")
                            cache._save_to_memory(key, value)
                    except Exception as e:
                        logger.error(f"Error pre-loading {key}: {e}")
        else:
            logger.warning("Cache directory not found")
        
        # 3. Add optimized get_with_quick_fallback method
        def get_with_quick_fallback(cache_obj, key, default=None):
            """Get an item with quick fallback to stale data for faster initial load"""
            try:
                # Try memory cache first
                if hasattr(cache_obj, 'cache') and key in cache_obj.cache:
                    cache_item = cache_obj.cache[key]
                    # During initial load, accept stale data unconditionally
                    if hasattr(cache_obj, 'initial_load_mode') and cache_obj.initial_load_mode:
                        return cache_item.value, True
                    
                    # Normal operation
                    if not cache_item.is_expired():
                        return cache_item.value, False
                    else:
                        return cache_item.value, True
                
                # Try disk cache directly
                if cache_obj.disk_cache_enabled:
                    disk_value = cache_obj._load_from_disk(key)
                    if disk_value is not None:
                        return disk_value, True
                
                return default, False
            except Exception as e:
                logger.error(f"Error in quick fallback for {key}: {e}")
                return default, False
        
        # Add the method to the cache manager
        cache.get_with_quick_fallback = lambda key, default=None: get_with_quick_fallback(cache, key, default)
        
        # 4. Optimize TTLs for faster loading
        cache.default_ttl = max(cache.default_ttl, 1800)  # Minimum 30 minutes TTL
        
        logger.info("Quick cache fix applied successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error applying quick cache fix: {e}")
        return False


def optimize_initial_data_load(symbols: list) -> Dict[str, Any]:
    """
    Optimize initial data load by using cached data aggressively
    
    Args:
        symbols: List of symbols to load
        
    Returns:
        Dict of data by symbol
    """
    from cache_manager import CacheManager
    
    logger.info(f"Optimizing initial data load for {len(symbols)} symbols...")
    start_time = time.time()
    
    # Get cache manager
    cache = CacheManager.get_instance()
    
    # Results container
    results = {}
    
    # Try to get all data from cache first
    for symbol in symbols:
        cache_key = f"market_data_{symbol}"
        
        # Use quick fallback method if available
        if hasattr(cache, 'get_with_quick_fallback'):
            value, _ = cache.get_with_quick_fallback(cache_key)
            if value is not None:
                results[symbol] = value
                continue
        
        # Standard method fallback
        value, _ = cache.get(cache_key)
        if value is not None:
            results[symbol] = value
    
    end_time = time.time()
    logger.info(f"Initial data load completed in {end_time - start_time:.2f}s, got {len(results)}/{len(symbols)} from cache")
    
    return results