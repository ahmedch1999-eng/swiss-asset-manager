"""
Scheduler Cache Integration Module (Enhanced Version)
Initializes and integrates the enhanced cache manager with the scheduler system
"""

import os
import logging
from cache_manager import CacheManager
from cache_enhancements import EnhancedCacheManager, enhance_cache_system
from scheduler_config import SchedulerConfig

# Configure logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logger = logging.getLogger("enhanced_cache_integration")
handler = logging.FileHandler(os.path.join(log_dir, 'enhanced_cache_integration.log'))
formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(getattr(logging, SchedulerConfig.LOG_LEVEL))

def init_enhanced_cache_system():
    """
    Initialize the enhanced cache system and configure it based on environment settings
    
    Returns:
        EnhancedCacheManager instance
    """
    logger.info("Initializing enhanced cache system...")
    
    try:
        # Enhance the cache system
        enhanced_cache = enhance_cache_system()
        
        # Configure the cache manager based on SchedulerConfig settings
        enhanced_cache.default_ttl = int(os.environ.get('DEFAULT_CACHE_TTL', 900))  # Default: 15 minutes
        enhanced_cache.disk_cache_enabled = SchedulerConfig.ENABLE_DISK_CACHE if hasattr(SchedulerConfig, 'ENABLE_DISK_CACHE') else True
        
        # Configure enhanced features
        enhanced_cache.compression_threshold = int(os.environ.get('CACHE_COMPRESSION_THRESHOLD', 10 * 1024))  # 10KB default
        enhanced_cache.memory_limit = int(os.environ.get('CACHE_MEMORY_LIMIT', 100 * 1024 * 1024))  # 100MB default
        enhanced_cache.cache_size_limit = int(os.environ.get('CACHE_SIZE_LIMIT', 10000))  # 10K items default
        
        # Create cache directory if not exists
        if enhanced_cache.disk_cache_enabled and not os.path.exists('cache'):
            os.makedirs('cache')
            logger.info("Created cache directory")
            
        # Start the cache warming thread
        from cache_manager import start_cache_warming_thread
        start_cache_warming_thread()
        
        # Register common warming tasks
        register_cache_warming_tasks(enhanced_cache)
        
        logger.info(f"Enhanced cache system initialized successfully (TTL: {enhanced_cache.default_ttl}s, "
                   f"Disk cache: {enhanced_cache.disk_cache_enabled}, "
                   f"Compression: {enhanced_cache.compression_threshold/1024}KB, "
                   f"Memory limit: {enhanced_cache.memory_limit/1024/1024}MB)")
        return enhanced_cache
        
    except Exception as e:
        logger.error(f"Error initializing enhanced cache system: {e}")
        # Fall back to basic cache manager
        logger.info("Falling back to basic cache manager")
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
        
        # Register key market indices for warming with different priorities
        high_priority_symbols = ['SMI', 'DAX', 'S&P 500', 'NASDAQ']
        medium_priority_symbols = ['Gold', 'Bitcoin', 'EUR/CHF']
        low_priority_symbols = ['Nestlé', 'Novartis', 'Roche', 'UBS']
        
        # Register high priority symbols (warm 5 minutes before expiry)
        for symbol in high_priority_symbols:
            cache.schedule_warming(
                f"market_data:{symbol}",
                DataServices.get_market_data,
                args=(symbol, False),  # symbol, use_cache=False
                time_before=300  # 5 minutes before expiry
            )
            logger.debug(f"Registered high priority warming task for {symbol}")
            
        # Register medium priority symbols (warm 3 minutes before expiry)
        for symbol in medium_priority_symbols:
            cache.schedule_warming(
                f"market_data:{symbol}",
                DataServices.get_market_data,
                args=(symbol, False),
                time_before=180  # 3 minutes before expiry
            )
            logger.debug(f"Registered medium priority warming task for {symbol}")
            
        # Register low priority symbols (warm 1 minute before expiry)
        for symbol in low_priority_symbols:
            cache.schedule_warming(
                f"market_data:{symbol}",
                DataServices.get_market_data,
                args=(symbol, False),
                time_before=60  # 1 minute before expiry
            )
            logger.debug(f"Registered low priority warming task for {symbol}")
        
        # Register news warming
        cache.schedule_warming(
            "financial_news",
            DataServices.get_news,
            args=(False,),  # use_cache=False
            time_before=300
        )
        
        logger.info(f"Registered {len(high_priority_symbols) + len(medium_priority_symbols) + len(low_priority_symbols) + 1} cache warming tasks")
        
    except Exception as e:
        logger.error(f"Error registering cache warming tasks: {e}")

# Initialize cache when the module is imported
enhanced_cache_manager = init_enhanced_cache_system()

def get_enhanced_cache_manager():
    """
    Get the global enhanced cache manager instance
    
    Returns:
        EnhancedCacheManager instance
    """
    return enhanced_cache_manager

def get_enhanced_cache_stats():
    """
    Get enhanced cache statistics for monitoring
    
    Returns:
        Dict with cache statistics
    """
    try:
        if isinstance(enhanced_cache_manager, EnhancedCacheManager):
            return enhanced_cache_manager.get_enhanced_stats()
        else:
            return enhanced_cache_manager.get_stats()
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {"error": str(e)}