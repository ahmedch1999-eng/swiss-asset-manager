"""
Cache System Enhancements

This module implements advanced enhancements to the existing cache system:
1. Compression for large objects
2. LRU eviction policy
3. Dynamic TTL adjustment
4. Memory usage monitoring and limits
"""

import time
import zlib
import pickle
import logging
import threading
import psutil
from typing import Any, Dict, List, Optional, Tuple
from cache_manager import CacheManager, CacheItem

# Configure logging
logger = logging.getLogger('cache_enhancements')
handler = logging.FileHandler('logs/cache_enhancements.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Constants
DEFAULT_COMPRESSION_THRESHOLD = 10 * 1024  # 10KB
DEFAULT_MEMORY_LIMIT = 100 * 1024 * 1024  # 100MB
DEFAULT_CACHE_SIZE_LIMIT = 10000  # Maximum number of items
LRU_PRUNE_PERCENT = 20  # Remove 20% of items when limit reached

class EnhancedCacheItem(CacheItem):
    """Extended cache item with compression support and LRU tracking"""
    
    def __init__(self, key: str, value: Any, ttl: int = 900, 
                 compress_threshold: int = DEFAULT_COMPRESSION_THRESHOLD):
        """Initialize enhanced cache item.
        
        Args:
            key: Cache key
            value: Data to cache
            ttl: Time to live in seconds (default: 15 minutes)
            compress_threshold: Size threshold for compression in bytes
        """
        self.compress_threshold = compress_threshold
        self._size_estimate = self._estimate_size(value)
        self.is_compressed = False
        
        # Compress if needed before passing to parent
        if self._size_estimate > self.compress_threshold:
            compressed_value = self._compress_value(value)
            self.is_compressed = True
            super().__init__(key, compressed_value, ttl)
        else:
            super().__init__(key, value, ttl)
            
        # LRU metadata
        self.last_accessed = time.time()
        self.access_count = 0
    
    def _compress_value(self, value: Any) -> bytes:
        """Compress a value using zlib compression."""
        try:
            # Pickle and compress the value
            pickled = pickle.dumps(value)
            compressed = zlib.compress(pickled)
            logger.debug(f"Compressed item {self.key} from {len(pickled)} bytes to {len(compressed)} bytes")
            return compressed
        except Exception as e:
            logger.error(f"Compression error for {self.key}: {e}")
            return value  # Fall back to uncompressed storage
    
    def _decompress_value(self, compressed_value: bytes) -> Any:
        """Decompress a value using zlib decompression."""
        try:
            # Decompress and unpickle the value
            decompressed = zlib.decompress(compressed_value)
            return pickle.loads(decompressed)
        except Exception as e:
            logger.error(f"Decompression error for {self.key}: {e}")
            return compressed_value  # Return the raw value as fallback
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate the memory size of a value."""
        try:
            # Use pickle to get a rough size estimate
            return len(pickle.dumps(value))
        except Exception:
            # If we can't pickle, use a conservative estimate
            return 1000  # Default size assumption
    
    @property
    def value(self) -> Any:
        """Get the cache item value, decompressing if necessary."""
        if self.is_compressed:
            return self._decompress_value(self._value)
        return self._value
    
    @value.setter
    def value(self, new_value: Any) -> None:
        """Set the cache item value, compressing if necessary."""
        self._size_estimate = self._estimate_size(new_value)
        if self._size_estimate > self.compress_threshold:
            self._value = self._compress_value(new_value)
            self.is_compressed = True
        else:
            self._value = new_value
            self.is_compressed = False
    
    def access(self) -> None:
        """Record an access to this cache item."""
        self.access_count += 1
        self.last_accessed = time.time()


class EnhancedCacheManager(CacheManager):
    """Enhanced cache manager with advanced features."""
    
    _instance = None
    _lock = threading.RLock()
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance of the enhanced cache manager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
    
    def __init__(self):
        """Initialize the enhanced cache manager."""
        # Don't call parent's __init__, replace it completely
        self.cache = {}
        self.disk_cache_enabled = True
        self.default_ttl = 900  # 15 minutes
        self.warming_tasks = {}
        self.warming_lock = threading.RLock()
        self.statistics = {
            'hits': 0,
            'misses': 0,
            'fallbacks': 0,
            'updates': 0,
            'compressions': 0,
            'evictions': 0,
            'memory_alerts': 0
        }
        
        # Enhanced settings
        self.compression_threshold = DEFAULT_COMPRESSION_THRESHOLD
        self.memory_limit = DEFAULT_MEMORY_LIMIT
        self.cache_size_limit = DEFAULT_CACHE_SIZE_LIMIT
        self.memory_warning_threshold = 0.8  # 80% of limit
        self.last_memory_check = 0
        self.memory_check_interval = 60  # Check memory every 60 seconds
        self.market_hours = False  # Flag to track if we're in market hours
        
        # Start background threads
        self._start_cleanup_thread()
        self._start_memory_monitor_thread()
        self._start_ttl_adjuster_thread()
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set an item in the cache with compression support.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        ttl = ttl if ttl is not None else self.default_ttl
        
        with self._lock:
            # Check memory limits before adding
            if self._check_memory_pressure():
                self._evict_items_lru()
            
            # Check if we already have this key
            if key in self.cache:
                cache_item = self.cache[key]
                if not cache_item.has_changed(value):
                    # Data hasn't changed, just update the TTL and access time
                    cache_item.ttl = ttl
                    cache_item.created_at = time.time()  # Reset expiration timer
                    cache_item.access()
                    return
                
                # Data has changed, update it
                cache_item.update_value(value)
                cache_item.ttl = ttl
                cache_item.access()
            else:
                # New cache item with potential compression
                self.cache[key] = EnhancedCacheItem(key, value, ttl, self.compression_threshold)
                # Check if we need to evict items due to size limit
                if len(self.cache) > self.cache_size_limit:
                    self._evict_items_lru()
            
            self.statistics['updates'] += 1
            
            # Save to disk if enabled
            if self.disk_cache_enabled:
                self._save_to_disk(key, value)
    
    def get(self, key: str, default: Any = None) -> Tuple[Any, bool]:
        """Get an item from the cache with LRU tracking.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Tuple of (value, is_stale)
        """
        with self._lock:
            # Check memory cache
            cache_item = self.cache.get(key)
            if cache_item:
                cache_item.access()  # Update LRU tracking
                
                # Check if expired
                if cache_item.is_expired():
                    # If expired, keep the value but mark as stale
                    self.statistics['fallbacks'] += 1
                    logger.debug(f"Using expired cache for {key}")
                    return cache_item.value, True
                
                # Valid cache hit
                self.statistics['hits'] += 1
                return cache_item.value, cache_item.is_stale()
            
            # Check disk cache if enabled
            if self.disk_cache_enabled:
                disk_value = self._load_from_disk(key)
                if disk_value is not None:
                    # Cache hit from disk
                    self.statistics['hits'] += 1
                    self._save_to_memory(key, disk_value)
                    return disk_value, True  # Mark disk cache as stale
            
            # Cache miss
            self.statistics['misses'] += 1
            return default, False
    
    def _evict_items_lru(self) -> int:
        """Evict least recently used items from the cache.
        
        Returns:
            Number of items evicted
        """
        if not self.cache:
            return 0
        
        # Calculate number of items to remove (at least 1)
        to_remove = max(1, int(len(self.cache) * (LRU_PRUNE_PERCENT / 100)))
        
        # Sort by last accessed time (oldest first)
        sorted_items = sorted(
            self.cache.items(), 
            key=lambda x: x[1].last_accessed
        )
        
        # Remove the oldest items
        evicted = 0
        for i in range(min(to_remove, len(sorted_items))):
            key, _ = sorted_items[i]
            if key in self.cache:
                del self.cache[key]
                evicted += 1
                
        if evicted:
            self.statistics['evictions'] += evicted
            logger.info(f"Evicted {evicted} items from cache using LRU policy")
            
        return evicted
    
    def _check_memory_pressure(self) -> bool:
        """Check if we're experiencing memory pressure.
        
        Returns:
            True if memory pressure detected, False otherwise
        """
        now = time.time()
        
        # Only check periodically to avoid excessive overhead
        if now - self.last_memory_check < self.memory_check_interval:
            return False
            
        self.last_memory_check = now
            
        try:
            # Get current process memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_usage = memory_info.rss  # Resident Set Size
            
            # Calculate memory pressure
            memory_pressure = memory_usage >= (self.memory_limit * self.memory_warning_threshold)
            
            if memory_pressure:
                self.statistics['memory_alerts'] += 1
                logger.warning(f"Memory pressure detected: {memory_usage/1024/1024:.2f}MB used of {self.memory_limit/1024/1024:.2f}MB limit")
                
            return memory_pressure
        except Exception as e:
            logger.error(f"Error checking memory pressure: {e}")
            return False
    
    def _start_memory_monitor_thread(self) -> None:
        """Start a background thread to monitor memory usage."""
        def memory_monitor_worker():
            while True:
                try:
                    if self._check_memory_pressure():
                        # If memory pressure detected, perform eviction
                        self._evict_items_lru()
                except Exception as e:
                    logger.error(f"Error in memory monitor thread: {e}")
                time.sleep(60)  # Check every minute
        
        thread = threading.Thread(target=memory_monitor_worker, daemon=True)
        thread.start()
        logger.info("Memory monitor thread started")
    
    def _start_ttl_adjuster_thread(self) -> None:
        """Start a background thread to adjust TTLs based on market hours."""
        def ttl_adjuster_worker():
            while True:
                try:
                    # Check if we're in market hours (9:30 AM to 4:00 PM ET, simplified)
                    now = time.localtime()
                    is_weekday = now.tm_wday < 5  # Monday to Friday
                    is_market_hours = (
                        is_weekday and 
                        ((now.tm_hour == 9 and now.tm_min >= 30) or 
                         (now.tm_hour > 9 and now.tm_hour < 16) or 
                         (now.tm_hour == 16 and now.tm_min == 0))
                    )
                    
                    # Market hours changed
                    if is_market_hours != self.market_hours:
                        self.market_hours = is_market_hours
                        logger.info(f"Market hours changed to: {'open' if is_market_hours else 'closed'}")
                        
                        # Adjust TTLs based on market hours
                        if is_market_hours:
                            # Shorter TTLs during market hours (more frequent updates)
                            self._adjust_ttls(market_data_multiplier=0.5, news_multiplier=0.7)
                        else:
                            # Longer TTLs outside market hours (less frequent updates)
                            self._adjust_ttls(market_data_multiplier=2.0, news_multiplier=1.5)
                except Exception as e:
                    logger.error(f"Error in TTL adjuster thread: {e}")
                time.sleep(300)  # Check every 5 minutes
        
        thread = threading.Thread(target=ttl_adjuster_worker, daemon=True)
        thread.start()
        logger.info("TTL adjuster thread started")
    
    def _adjust_ttls(self, market_data_multiplier: float = 1.0, news_multiplier: float = 1.0) -> None:
        """Adjust TTLs for different data types.
        
        Args:
            market_data_multiplier: Multiplier for market data TTLs
            news_multiplier: Multiplier for news data TTLs
        """
        with self._lock:
            for key, item in self.cache.items():
                if "market_data:" in key:
                    item.ttl = int(item.ttl * market_data_multiplier)
                elif "news" in key:
                    item.ttl = int(item.ttl * news_multiplier)
                # Other types keep their current TTLs
        
        logger.info(f"Adjusted TTLs: market_data={market_data_multiplier}x, news={news_multiplier}x")
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced cache statistics."""
        with self._lock:
            stats = self.get_stats()  # Get basic stats from parent
            
            # Add enhanced stats
            stats['compressions'] = self.statistics.get('compressions', 0)
            stats['evictions'] = self.statistics.get('evictions', 0)
            stats['memory_alerts'] = self.statistics.get('memory_alerts', 0)
            stats['compression_threshold'] = f"{self.compression_threshold/1024:.1f}KB"
            stats['memory_limit'] = f"{self.memory_limit/1024/1024:.1f}MB"
            stats['cache_size_limit'] = self.cache_size_limit
            stats['market_hours'] = self.market_hours
            
            # Count compressed items
            compressed_count = 0
            compressed_bytes = 0
            uncompressed_bytes = 0
            for item in self.cache.values():
                if hasattr(item, 'is_compressed') and item.is_compressed:
                    compressed_count += 1
                    if hasattr(item, '_size_estimate'):
                        uncompressed_bytes += item._size_estimate
                        compressed_bytes += len(item._value)
            
            stats['compressed_items'] = compressed_count
            stats['compressed_ratio'] = f"{compressed_bytes/uncompressed_bytes:.2f}" if uncompressed_bytes > 0 else "N/A"
            
            # Calculate memory savings
            memory_saved = uncompressed_bytes - compressed_bytes
            stats['memory_saved'] = f"{memory_saved/1024:.1f}KB" if memory_saved > 0 else "0KB"
            
            return stats


def enhance_cache_system():
    """Enhance the existing cache system with advanced features."""
    try:
        # Create enhanced cache manager
        enhanced_cache = EnhancedCacheManager.get_instance()
        
        # Copy existing configuration
        original_cache = CacheManager.get_instance()
        enhanced_cache.default_ttl = original_cache.default_ttl
        enhanced_cache.disk_cache_enabled = original_cache.disk_cache_enabled
        
        # Copy statistics
        for key, value in original_cache.statistics.items():
            if key in enhanced_cache.statistics:
                enhanced_cache.statistics[key] = value
        
        # Copy existing cache data
        for key, item in original_cache.cache.items():
            enhanced_cache.set(key, item.value, item.ttl)
        
        # Replace the original singleton instance with our enhanced version
        CacheManager._instance = enhanced_cache
        
        logger.info("Cache system enhanced with compression, LRU eviction, and dynamic TTLs")
        return enhanced_cache
        
    except Exception as e:
        logger.error(f"Error enhancing cache system: {e}")
        # Return the original cache manager if enhancement fails
        return CacheManager.get_instance()


# When imported, enhance the cache system
if __name__ != "__main__":
    enhanced_cache = enhance_cache_system()
    logger.info(f"Enhanced cache system initialized with {len(enhanced_cache.cache)} items")


# Test function
if __name__ == "__main__":
    # Test the enhanced cache
    print("Testing enhanced cache system...")
    
    # Enable verbose logging
    logger.setLevel(logging.DEBUG)
    
    # Enhance the cache
    cache = enhance_cache_system()
    
    # Test basic operations
    cache.set("test:small", "Small value")
    cache.set("test:large", "x" * 20000)  # Should be compressed
    
    # Verify retrieval
    small_value, _ = cache.get("test:small")
    large_value, _ = cache.get("test:large")
    
    print(f"Small value retrieved: {len(small_value)} chars")
    print(f"Large value retrieved: {len(large_value)} chars")
    
    # Check compression
    for key, item in cache.cache.items():
        if hasattr(item, 'is_compressed'):
            print(f"Item {key}: compressed={item.is_compressed}")
    
    # Print enhanced stats
    stats = cache.get_enhanced_stats()
    import json
    print("Enhanced cache stats:")
    print(json.dumps(stats, indent=2))