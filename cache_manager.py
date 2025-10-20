"""
Cache layer for Swiss Asset Manager.

This module implements an intelligent caching system with:
- TTL-based cache invalidation
- Differential updates
- Cache warming
- Automatic fallback to cached data
- Data consistency checks
"""

import os
import json
import time
import pickle
import hashlib
import logging
import threading
import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from functools import wraps

# Configure logging
logger = logging.getLogger('cache_manager')
handler = logging.FileHandler('logs/cache.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Ensure cache directory exists
os.makedirs('cache', exist_ok=True)


class CacheItem:
    """Represents a single cached item with metadata."""
    
    def __init__(self, key: str, value: Any, ttl: int = 900):
        """Initialize a cache item.
        
        Args:
            key: Cache key
            value: Data to cache
            ttl: Time to live in seconds (default: 15 minutes)
        """
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = self.created_at
        self.metadata = {}
        
        # Create hash of the data for consistency checks
        self.data_hash = self._hash_data(value)
    
    def is_expired(self) -> bool:
        """Check if the cache item is expired."""
        return (time.time() - self.created_at) > self.ttl
    
    def is_stale(self, threshold: int = 1800) -> bool:
        """Check if the cache item is stale but not expired.
        
        Args:
            threshold: Staleness threshold in seconds (default: 30 minutes)
        """
        age = time.time() - self.created_at
        return age > threshold and age <= self.ttl
    
    def access(self) -> None:
        """Record an access to this cache item."""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def _hash_data(self, data: Any) -> str:
        """Create a hash of the data for consistency checks."""
        try:
            data_str = json.dumps(data, sort_keys=True) if not isinstance(data, bytes) else data
            return hashlib.md5(str(data_str).encode('utf-8')).hexdigest()
        except TypeError:
            # If data is not JSON serializable, use pickle
            return hashlib.md5(pickle.dumps(data)).hexdigest()
    
    def has_changed(self, new_data: Any) -> bool:
        """Check if the data has changed compared to the cached version."""
        new_hash = self._hash_data(new_data)
        return new_hash != self.data_hash
    
    def update_value(self, value: Any) -> None:
        """Update the cached value and reset the creation time."""
        self.value = value
        self.created_at = time.time()
        self.data_hash = self._hash_data(value)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the cache item."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the cache item."""
        return self.metadata.get(key, default)


class CacheManager:
    """Intelligent cache manager with TTL, differential updates, and fallbacks."""
    
    _instance = None
    _lock = threading.RLock()
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance of the cache manager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
    
    def __init__(self):
        """Initialize the cache manager."""
        self.cache = {}
        self.disk_cache_enabled = True
        self.default_ttl = 900  # 15 minutes
        self.warming_tasks = {}
        self.warming_lock = threading.RLock()
        self.statistics = {
            'hits': 0,
            'misses': 0,
            'fallbacks': 0,
            'updates': 0
        }
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self) -> None:
        """Start a background thread to clean up expired items."""
        def cleanup_worker():
            while True:
                try:
                    self._cleanup_expired()
                except Exception as e:
                    logger.error(f"Error in cache cleanup: {e}")
                time.sleep(300)  # Run every 5 minutes
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
    
    def _cleanup_expired(self) -> None:
        """Remove expired items from the cache."""
        with self._lock:
            expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
            for key in expired_keys:
                logger.debug(f"Removing expired cache item: {key}")
                del self.cache[key]
    
    def get(self, key: str, default: Any = None) -> Tuple[Any, bool]:
        """Get an item from the cache.
        
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
                cache_item.access()
                
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
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set an item in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 15 minutes)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        
        with self._lock:
            # Check if we already have this key
            if key in self.cache:
                cache_item = self.cache[key]
                if not cache_item.has_changed(value):
                    # Data hasn't changed, just update the TTL
                    cache_item.ttl = ttl
                    cache_item.created_at = time.time()  # Reset expiration timer
                    return
                
                # Data has changed, update it
                cache_item.update_value(value)
                cache_item.ttl = ttl
            else:
                # New cache item
                self.cache[key] = CacheItem(key, value, ttl)
            
            self.statistics['updates'] += 1
            
            # Save to disk if enabled
            if self.disk_cache_enabled:
                self._save_to_disk(key, value)
    
    def set_many(self, items: Dict[str, Any], ttl: int = None) -> None:
        """Set multiple items in the cache at once.
        
        Args:
            items: Dictionary of key-value pairs
            ttl: Time to live in seconds (default: 15 minutes)
        """
        for key, value in items.items():
            self.set(key, value, ttl)
    
    def _save_to_memory(self, key: str, value: Any, ttl: int = None) -> None:
        """Save an item to the memory cache."""
        ttl = ttl if ttl is not None else self.default_ttl
        self.cache[key] = CacheItem(key, value, ttl)
    
    def _save_to_disk(self, key: str, value: Any) -> bool:
        """Save an item to the disk cache.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            bool: Success status
        """
        try:
            cache_file = os.path.join('cache', f"{key.replace(':', '_')}.cache")
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'value': value,
                    'created_at': time.time()
                }, f)
            return True
        except Exception as e:
            logger.error(f"Error saving to disk cache: {e}")
            return False
    
    def _load_from_disk(self, key: str) -> Optional[Any]:
        """Load an item from the disk cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            cache_file = os.path.join('cache', f"{key.replace(':', '_')}.cache")
            if not os.path.exists(cache_file):
                return None
            
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            
            # Check if disk cache is too old (1 day)
            if time.time() - data['created_at'] > 86400:
                os.remove(cache_file)
                return None
                
            return data['value']
        except Exception as e:
            logger.error(f"Error loading from disk cache: {e}")
            return None
    
    def invalidate(self, key: str) -> None:
        """Invalidate a cache item.
        
        Args:
            key: Cache key
        """
        with self._lock:
            if key in self.cache:
                del self.cache[key]
            
            # Also remove from disk if exists
            try:
                cache_file = os.path.join('cache', f"{key.replace(':', '_')}.cache")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            except Exception as e:
                logger.error(f"Error removing disk cache: {e}")
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache items matching a pattern.
        
        Args:
            pattern: Pattern to match keys against
            
        Returns:
            Number of items invalidated
        """
        count = 0
        with self._lock:
            keys_to_remove = [k for k in self.cache if pattern in k]
            for key in keys_to_remove:
                self.invalidate(key)
                count += 1
        return count
    
    def schedule_warming(self, key: str, func: Callable, args: tuple = (), kwargs: dict = None, 
                         time_before: int = 300) -> None:
        """Schedule a cache warming task.
        
        Args:
            key: Cache key to warm
            func: Function to call to get fresh data
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            time_before: Time in seconds before expiration to warm cache
        """
        if kwargs is None:
            kwargs = {}
            
        with self.warming_lock:
            self.warming_tasks[key] = {
                'func': func,
                'args': args,
                'kwargs': kwargs,
                'time_before': time_before,
                'next_run': 0  # Initialize to run immediately on first check
            }
    
    def process_warming_tasks(self) -> None:
        """Process all scheduled cache warming tasks."""
        now = time.time()
        tasks_to_run = []
        
        with self.warming_lock:
            for key, task in self.warming_tasks.items():
                # If it's time to run this task
                if now >= task['next_run']:
                    tasks_to_run.append((key, task))
        
        # Run tasks outside the lock to prevent blocking
        for key, task in tasks_to_run:
            try:
                # Check if we have this item in cache and when it expires
                with self._lock:
                    cache_item = self.cache.get(key)
                    if cache_item:
                        # Calculate time until expiration
                        expires_at = cache_item.created_at + cache_item.ttl
                        time_until_expiry = expires_at - now
                        
                        # Only warm if approaching expiry
                        if time_until_expiry <= task['time_before']:
                            self._run_warming_task(key, task)
                        else:
                            # Schedule next check
                            with self.warming_lock:
                                self.warming_tasks[key]['next_run'] = expires_at - task['time_before']
                    else:
                        # Not in cache, run now
                        self._run_warming_task(key, task)
            except Exception as e:
                logger.error(f"Error processing warming task for {key}: {e}")
    
    def _run_warming_task(self, key: str, task: dict) -> None:
        """Run a single warming task.
        
        Args:
            key: Cache key
            task: Task configuration
        """
        logger.info(f"Running cache warming task for {key}")
        try:
            # Call the function to get fresh data
            result = task['func'](*task['args'], **task['kwargs'])
            
            # Update the cache with the fresh data
            self.set(key, result)
            
            # Mark as warmed
            with self._lock:
                if key in self.cache:
                    self.cache[key].set_metadata('warmed', True)
                    self.cache[key].set_metadata('warmed_at', time.time())
            
            # Reset next run time based on new TTL
            with self.warming_lock:
                with self._lock:
                    if key in self.cache:
                        cache_item = self.cache[key]
                        expires_at = cache_item.created_at + cache_item.ttl
                        self.warming_tasks[key]['next_run'] = expires_at - task['time_before']
                    else:
                        # If somehow the item disappeared, schedule for near future
                        self.warming_tasks[key]['next_run'] = time.time() + 60
            
            logger.info(f"Cache warming completed for {key}")
        except Exception as e:
            logger.error(f"Error in cache warming task for {key}: {e}")
            # Schedule retry in 5 minutes
            with self.warming_lock:
                self.warming_tasks[key]['next_run'] = time.time() + 300
    
    def diff_update(self, key: str, fetch_func: Callable, 
                  compare_key: str = None, ttl: int = None) -> Tuple[Any, bool]:
        """Update cache with differential update if possible.
        
        Args:
            key: Cache key
            fetch_func: Function to fetch fresh data
            compare_key: Key to use for comparison (default: use the main key)
            ttl: Time to live for the cache entry
            
        Returns:
            Tuple of (data, was_updated)
        """
        compare_key = compare_key or key
        
        # Check if we have existing data
        with self._lock:
            cache_item = self.cache.get(key)
            current_data = cache_item.value if cache_item else None
        
        if current_data is None:
            # No existing data, do a full fetch
            try:
                new_data = fetch_func(full_refresh=True)
                self.set(key, new_data, ttl)
                return new_data, True
            except Exception as e:
                logger.error(f"Error in full fetch for {key}: {e}")
                return None, False
        
        # We have existing data, try differential update
        try:
            # Get metadata needed for differential update
            meta = {}
            if cache_item:
                meta = {
                    'last_update': cache_item.get_metadata('last_update'),
                    'etag': cache_item.get_metadata('etag'),
                    'last_modified': cache_item.get_metadata('last_modified')
                }
            
            # Fetch only changes
            new_data, diff_meta = fetch_func(
                current_data=current_data, 
                meta=meta,
                full_refresh=False
            )
            
            # If nothing changed, update timestamp and return current
            if new_data is None:
                if cache_item:
                    cache_item.set_metadata('checked_at', time.time())
                return current_data, False
            
            # Store the new data with metadata
            self.set(key, new_data, ttl)
            
            # Add differential update metadata
            with self._lock:
                if key in self.cache and diff_meta:
                    for meta_key, meta_value in diff_meta.items():
                        self.cache[key].set_metadata(meta_key, meta_value)
                    self.cache[key].set_metadata('last_update', time.time())
            
            return new_data, True
            
        except Exception as e:
            logger.error(f"Error in differential update for {key}: {e}")
            # Return the existing data with stale flag
            return current_data, False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            stats = self.statistics.copy()
            stats['size'] = len(self.cache)
            stats['disk_enabled'] = self.disk_cache_enabled
            
            # Calculate hit ratio
            total_requests = stats['hits'] + stats['misses']
            stats['hit_ratio'] = stats['hits'] / total_requests if total_requests > 0 else 0
            
            # Add memory usage estimation (rough)
            try:
                import sys
                cache_size = sum(sys.getsizeof(v.value) for v in self.cache.values())
                stats['memory_usage_bytes'] = cache_size
                stats['memory_usage_mb'] = cache_size / (1024 * 1024)
            except:
                stats['memory_usage'] = 'unknown'
            
            return stats


# Helper decorators for the cache
def cached(key_prefix: str = "", ttl: int = None):
    """Decorator to cache function results.
    
    Args:
        key_prefix: Prefix to add to the cache key
        ttl: Time to live in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a cache key from the function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{_args_to_key(args)}:{_args_to_key(kwargs)}"
            
            # Get the cache manager
            cache = CacheManager.get_instance()
            
            # Try to get from cache
            value, is_stale = cache.get(cache_key)
            
            # If found and not stale, return it
            if value is not None and not is_stale:
                return value
            
            # Otherwise, call the function
            result = func(*args, **kwargs)
            
            # Cache the result
            cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def _args_to_key(args):
    """Convert function arguments to a string for cache keys."""
    try:
        return hashlib.md5(str(args).encode()).hexdigest()
    except:
        return str(hash(str(args)))


# Initialize the cache manager singleton
cache = CacheManager.get_instance()


def start_cache_warming_thread():
    """Start a background thread to handle cache warming."""
    def warming_worker():
        while True:
            try:
                CacheManager.get_instance().process_warming_tasks()
            except Exception as e:
                logger.error(f"Error in cache warming thread: {e}")
            time.sleep(60)  # Check every minute
    
    thread = threading.Thread(target=warming_worker, daemon=True)
    thread.start()
    logger.info("Cache warming thread started")


# Start the cache warming thread
start_cache_warming_thread()