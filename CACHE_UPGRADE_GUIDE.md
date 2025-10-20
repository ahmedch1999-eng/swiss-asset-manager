# Enhanced Caching System Installation Guide

This guide provides step-by-step instructions for upgrading your Swiss Asset Manager application with the enhanced caching system that includes compression, LRU eviction, dynamic TTLs, and advanced memory management.

## Prerequisites

- Existing Swiss Asset Manager application with the base caching system
- Python 3.7 or higher
- `psutil` package installed (`pip install psutil`)

## Installation Steps

### 1. Backup Your Data

Before upgrading, create a backup of your application:

```bash
# Create backup directory
mkdir -p ~/swiss-asset-manager-backup

# Copy important files
cp -r /Users/achi/swiss-asset-manager/cache_manager.py ~/swiss-asset-manager-backup/
cp -r /Users/achi/swiss-asset-manager/scheduler_cache_integration.py ~/swiss-asset-manager-backup/
cp -r /Users/achi/swiss-asset-manager/data_services_cached.py ~/swiss-asset-manager-backup/
cp -r /Users/achi/swiss-asset-manager/cache/ ~/swiss-asset-manager-backup/
```

### 2. Install Required Packages

The enhanced caching system requires the `psutil` package for memory monitoring:

```bash
pip install psutil
```

### 3. Copy New Files

Make sure all the enhanced caching files are in your application directory:

- `cache_enhancements.py` - Core enhancements implementation
- `enhanced_cache_integration.py` - Integration with scheduler
- `test_cache_enhancements.py` - Test script
- `upgrade_cache.py` - Upgrade script

### 4. Run the Upgrade Script

Execute the upgrade script to switch from the basic caching system to the enhanced version:

```bash
cd /Users/achi/swiss-asset-manager
./upgrade_cache.py
```

The script will:
1. Initialize the enhanced cache system
2. Transfer data from the basic cache
3. Update references in dependent modules
4. Test the enhanced cache functionality

### 5. Run Tests

Verify that the enhanced cache system is working correctly:

```bash
cd /Users/achi/swiss-asset-manager
./test_cache_enhancements.py
```

The test script will check:
- Compression functionality
- LRU eviction policy
- Dynamic TTL adjustment
- Memory monitoring
- Cache metrics collection

### 6. Configure Environment Variables (Optional)

To fine-tune the enhanced cache system, you can set the following environment variables:

```bash
# Cache TTL settings
export DEFAULT_CACHE_TTL=900           # Default TTL (15 minutes)
export MARKET_DATA_TTL=600             # Market data TTL (10 minutes)
export PORTFOLIO_DATA_TTL=3600         # Portfolio data TTL (1 hour)
export NEWS_DATA_TTL=1800              # News TTL (30 minutes)
export FINANCIAL_DATA_TTL=86400        # Financial data TTL (24 hours)

# Enhanced cache settings
export CACHE_COMPRESSION_THRESHOLD=10240  # 10KB - min size for compression
export CACHE_MEMORY_LIMIT=104857600       # 100MB - memory limit
export CACHE_SIZE_LIMIT=10000             # Maximum number of cache items
export USE_ENHANCED_CACHE=true            # Enable enhanced cache
```

You can add these to your `.env` file or set them before starting the application.

### 7. Restart Your Application

For the changes to take full effect, restart your application:

```bash
# If using the scheduler process manager
cd /Users/achi/swiss-asset-manager
python scheduler_standalone.py restart

# If using the Flask application
cd /Users/achi/swiss-asset-manager
# Kill the current process and restart
pkill -f "python app.py" 
python app.py
```

### 8. Monitor Cache Performance

The enhanced cache system provides detailed metrics. You can view them:

1. In the Scheduler Dashboard UI under the "Cache Metrics" section
2. Through the API endpoint at `/scheduler/stats`
3. By checking the logs at `logs/cache_enhancements.log`

## Rollback Process

If you need to revert to the basic cache system:

```bash
# Restore original files
cp ~/swiss-asset-manager-backup/cache_manager.py /Users/achi/swiss-asset-manager/
cp ~/swiss-asset-manager-backup/scheduler_cache_integration.py /Users/achi/swiss-asset-manager/

# Set environment variable to disable enhanced cache
export USE_ENHANCED_CACHE=false

# Restart the application
# (Follow step 7 above)
```

## Troubleshooting

### Cache Not Using Compression

If compression isn't being applied to large objects:

- Check that the `psutil` package is installed
- Verify the `CACHE_COMPRESSION_THRESHOLD` isn't set too high
- Check the logs for compression-related errors

### Memory Usage Still High

If memory usage remains high despite the enhanced cache:

- Lower the `CACHE_MEMORY_LIMIT` setting
- Reduce the `CACHE_SIZE_LIMIT`
- Increase the compression threshold to compress more objects

### TTL Adjustments Not Working

If TTL adjustments for market/non-market hours aren't working:

- Check that the time zone settings on your server match the market hours configuration
- Verify in the logs that the TTL adjuster thread is running

## Need Help?

If you encounter any issues:

- Check the logs in the `logs/` directory
- Run the test script with verbose logging: `LOG_LEVEL=DEBUG ./test_cache_enhancements.py`
- Contact your system administrator or the development team