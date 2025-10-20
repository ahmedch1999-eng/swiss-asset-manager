# Swiss Asset Manager - Intelligent Cache System

## Overview

This repository contains a comprehensive intelligent caching system for the Swiss Asset Manager application. The system optimizes API requests, improves performance, and enhances resilience against external service failures.

## Repository Structure

```
swiss-asset-manager/
├── app.py                          # Main Flask application
├── cache_manager.py                # Core cache implementation
├── cache_enhancements.py           # Enhanced cache features
├── data_services_cached.py         # Cached data services
├── scheduler_cache_integration.py  # Integration with scheduler
├── enhanced_cache_integration.py   # Enhanced cache integration
├── scheduler_integration.py        # Scheduler integration
├── test_cache.py                   # Basic cache tests
├── test_cache_enhancements.py      # Enhanced cache tests
├── upgrade_cache.py                # Script to upgrade to enhanced cache
├── CACHE_IMPLEMENTATION_SUMMARY.md # Implementation summary
├── CACHE_NEXT_STEPS.md             # Optimization roadmap
└── CACHE_UPGRADE_GUIDE.md          # Enhanced cache installation guide
```

## Core Features

### Base Cache System

- **TTL-based Cache Invalidation**: Configurable time-to-live for different data types
- **Differential Updates**: Hash-based data change detection
- **Cache Warming**: Background thread for preemptive cache warming
- **Fallback to Cached Data**: Returns stale data with stale indicator when APIs fail
- **Data Consistency Checks**: Hash-based comparison for detecting data changes

### Enhanced Cache System

- **Compression**: Automatic compression for large cached objects
- **LRU Eviction Policy**: Least recently used items evicted first when limits reached
- **Dynamic TTLs**: Adaptive TTLs based on market hours
- **Memory Monitoring**: Advanced memory usage tracking and limits
- **Enhanced Metrics**: Comprehensive cache performance statistics

## Performance Improvements

Tests have shown significant performance improvements:
- First API request: ~980ms
- Subsequent cached requests: <1ms
- Performance improvement: 124,604x faster in cache hit scenarios

## Configuration

The cache system can be configured via environment variables:

```bash
# Cache TTL settings
DEFAULT_CACHE_TTL=900           # Default TTL (15 minutes)
MARKET_DATA_TTL=600             # Market data TTL (10 minutes)
PORTFOLIO_DATA_TTL=3600         # Portfolio data TTL (1 hour)
NEWS_DATA_TTL=1800              # News TTL (30 minutes)
FINANCIAL_DATA_TTL=86400        # Financial data TTL (24 hours)
ENABLE_DISK_CACHE=true          # Enable/disable disk cache

# Enhanced cache settings
CACHE_COMPRESSION_THRESHOLD=10240  # 10KB - min size for compression
CACHE_MEMORY_LIMIT=104857600       # 100MB - memory limit
CACHE_SIZE_LIMIT=10000             # Maximum number of cache items
USE_ENHANCED_CACHE=true            # Enable enhanced cache
```

## Usage

### Basic Usage

```python
from cache_manager import CacheManager

# Get the singleton instance
cache = CacheManager.get_instance()

# Store data
cache.set("market_data:SPX", data, ttl=600)  # 10 minutes TTL

# Retrieve data
data, is_stale = cache.get("market_data:SPX")

if data is not None:
    # Use the data
    if is_stale:
        print("Warning: Using stale data")
else:
    # No data found
```

### Enhanced Cache

```python
from cache_enhancements import EnhancedCacheManager

# Get the enhanced singleton instance
cache = EnhancedCacheManager.get_instance()

# Configure enhancements
cache.compression_threshold = 5 * 1024  # 5KB
cache.memory_limit = 50 * 1024 * 1024  # 50MB
cache.cache_size_limit = 5000  # Max 5000 items

# Get enhanced stats
stats = cache.get_enhanced_stats()
print(f"Memory saved: {stats['memory_saved']}")
```

## Testing

### Basic Tests

```bash
python test_cache.py
```

### Enhanced Cache Tests

```bash
./test_cache_enhancements.py
```

## Upgrading

To upgrade from the basic to the enhanced cache system:

```bash
./upgrade_cache.py
```

See [CACHE_UPGRADE_GUIDE.md](CACHE_UPGRADE_GUIDE.md) for detailed instructions.

## Future Enhancements

See [CACHE_NEXT_STEPS.md](CACHE_NEXT_STEPS.md) for planned enhancements including:

- Adaptive TTL based on data volatility
- Distributed caching support
- Multi-tenant features
- Advanced predictive warming

## Documentation

- [CACHE_IMPLEMENTATION_SUMMARY.md](CACHE_IMPLEMENTATION_SUMMARY.md): Detailed implementation summary
- [CACHE_NEXT_STEPS.md](CACHE_NEXT_STEPS.md): Optimization roadmap
- [CACHE_UPGRADE_GUIDE.md](CACHE_UPGRADE_GUIDE.md): Enhanced cache installation guide