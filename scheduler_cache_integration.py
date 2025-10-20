"""
Scheduler Cache Integration Module
Initializes and integrates the cache manager with the scheduler system
"""

import os
import logging
from cache_manager import CacheManager, start_cache_warming_thread
from scheduler_config import SchedulerConfig

# Configure logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logger = logging.getLogger("cache_integration")
handler = logging.FileHandler(os.path.join(log_dir, 'cache_integration.log'))
formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(getattr(logging, SchedulerConfig.LOG_LEVEL))

def init_cache_system():
    """
    Initialize the cache system and configure it based on environment settings
    
    Returns:
        CacheManager instance
    """
    logger.info("Initializing cache system...")
    
    try:
        # Get the cache manager instance
        cache = CacheManager.get_instance()
        
        # Configure the cache manager based on SchedulerConfig settings
        cache.default_ttl = int(os.environ.get('DEFAULT_CACHE_TTL', 900))  # Default: 15 minutes
        cache.disk_cache_enabled = SchedulerConfig.ENABLE_DISK_CACHE if hasattr(SchedulerConfig, 'ENABLE_DISK_CACHE') else True
        
        # Create cache directory if not exists
        if cache.disk_cache_enabled and not os.path.exists('cache'):
            os.makedirs('cache')
            logger.info("Created cache directory")
            
        # Start the cache warming thread
        start_cache_warming_thread()
        
        # Register common warming tasks
        register_cache_warming_tasks(cache)
        
        logger.info(f"Cache system initialized successfully (TTL: {cache.default_ttl}s, Disk cache: {cache.disk_cache_enabled})")
        return cache
        
    except Exception as e:
        logger.error(f"Error initializing cache system: {e}")
        # Return cache manager anyway - with default settings
        return CacheManager.get_instance()

def register_cache_warming_tasks(cache):
    """
    Register common cache warming tasks for frequently accessed data
    
    Args:
        cache: CacheManager instance
    """
    logger.info("Registering cache warming tasks...")
    
    try:
        # Import data services here to avoid circular imports
        from data_services_cached import DataServices
        
        # Register key market indices for warming
        important_symbols = ['SMI', 'DAX', 'S&P 500', 'NASDAQ', 'Gold', 'Bitcoin', 'EUR/CHF', 'Nestlé']
        for symbol in important_symbols:
            cache.schedule_warming(
                f"market_data:{symbol}",
                DataServices.get_market_data,
                args=(symbol, False),  # symbol, use_cache=False
                time_before=300  # 5 minutes before expiry
            )
            logger.debug(f"Registered warming task for {symbol}")
        
        # Register news warming
        cache.schedule_warming(
            "financial_news",
            DataServices.get_news,
            args=(False,),  # use_cache=False
            time_before=300
        )
        
        logger.info(f"Registered {len(important_symbols) + 1} cache warming tasks")
        
    except Exception as e:
        logger.error(f"Error registering cache warming tasks: {e}")

# Initialize cache when the module is imported
cache_manager = init_cache_system()

def get_cache_manager():
    """
    Get the global cache manager instance
    
    Returns:
        CacheManager instance
    """
    return cache_manager

def get_cache_stats():
    """
    Get cache statistics for monitoring
    
    Returns:
        Dict with cache statistics
    """
    try:
        return cache_manager.get_stats()
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {"error": str(e)}