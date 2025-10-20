#!/usr/bin/env python
"""
Script to upgrade the basic cache system to the enhanced version
without disrupting the running application.
"""

import os
import sys
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/cache_upgrade.log')
    ]
)
logger = logging.getLogger('cache_upgrade')

def print_separator(title):
    """Print a separator with title"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def upgrade_cache():
    """Upgrade the basic cache system to the enhanced version"""
    print_separator("CACHE SYSTEM UPGRADE")
    print(f"Starting upgrade at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Import the basic cache manager
        print("1. Importing basic cache manager...")
        from cache_manager import CacheManager
        basic_cache = CacheManager.get_instance()
        
        # Get basic cache stats
        basic_stats = basic_cache.get_stats()
        print(f"Basic cache stats: {basic_stats['size']} items, "
              f"{basic_stats.get('hit_ratio', 0)*100:.1f}% hit ratio")
        
        # Import the enhanced cache manager
        print("\n2. Importing enhanced cache integration...")
        from enhanced_cache_integration import init_enhanced_cache_system
        
        # Initialize enhanced cache
        print("3. Initializing enhanced cache system...")
        enhanced_cache = init_enhanced_cache_system()
        
        # Check if enhancement was successful
        from cache_enhancements import EnhancedCacheManager
        if isinstance(enhanced_cache, EnhancedCacheManager):
            print("✅ Enhanced cache system initialized successfully")
        else:
            print("❌ Enhanced cache system initialization failed, still using basic cache")
            return False
        
        # Get enhanced cache stats
        enhanced_stats = enhanced_cache.get_enhanced_stats()
        print(f"Enhanced cache stats: {enhanced_stats['size']} items, "
              f"{enhanced_stats.get('hit_ratio', 0)*100:.1f}% hit ratio, "
              f"{enhanced_stats.get('compressed_items', 0)} compressed items")
        
        # Replace references in scheduler integration
        print("\n4. Updating scheduler cache integration...")
        try:
            import scheduler_cache_integration
            # Replace the cache manager instance
            scheduler_cache_integration.cache_manager = enhanced_cache
            print("✅ Updated scheduler_cache_integration.cache_manager")
        except Exception as e:
            print(f"❌ Error updating scheduler integration: {e}")
        
        # Update data services reference
        print("\n5. Updating data services cached reference...")
        try:
            import data_services_cached
            # Replace the cache reference
            data_services_cached.cache = enhanced_cache
            print("✅ Updated data_services_cached.cache")
        except Exception as e:
            print(f"❌ Error updating data services reference: {e}")
        
        # Perform a test operation
        print("\n6. Testing enhanced cache...")
        test_key = "cache_upgrade_test"
        test_value = "Enhanced cache test value"
        enhanced_cache.set(test_key, test_value)
        retrieved_value, _ = enhanced_cache.get(test_key)
        
        if retrieved_value == test_value:
            print("✅ Cache test successful")
        else:
            print(f"❌ Cache test failed: got '{retrieved_value}', expected '{test_value}'")
            return False
        
        # Update environment variables for persistence
        print("\n7. Setting environment variables for persistence...")
        os.environ['USE_ENHANCED_CACHE'] = 'true'
        os.environ['CACHE_COMPRESSION_THRESHOLD'] = str(enhanced_cache.compression_threshold)
        os.environ['CACHE_MEMORY_LIMIT'] = str(enhanced_cache.memory_limit)
        os.environ['CACHE_SIZE_LIMIT'] = str(enhanced_cache.cache_size_limit)
        
        print("\n✅ Cache system upgraded successfully!")
        print(f"Upgrade completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except Exception as e:
        logger.error(f"Error during cache upgrade: {e}", exc_info=True)
        print(f"\n❌ Cache upgrade failed: {e}")
        return False

def main():
    """Main entry point"""
    success = upgrade_cache()
    
    if success:
        print_separator("NEXT STEPS")
        print("To complete the upgrade:")
        print("1. Restart the application to ensure all components use the enhanced cache")
        print("2. Monitor cache metrics in the scheduler dashboard")
        print("3. Run test_cache_enhancements.py to verify all enhanced features")
        
        return 0
    else:
        print_separator("UPGRADE FAILED")
        print("The cache system could not be upgraded.")
        print("Please check the logs for details and try again.")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())