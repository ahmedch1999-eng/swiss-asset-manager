"""
Quick Performance Fix for Swiss Asset Manager

This module provides immediate performance improvements by:
1. Implementing aggressive caching for API calls
2. Reducing concurrent API requests 
3. Adding fallback mechanisms for failed requests
4. Prioritizing critical data loading
"""

import logging
import functools
import time
import threading
from typing import Dict, Any, Callable

# Configure logging
logger = logging.getLogger('quick_performance')
logger.setLevel(logging.INFO)

# In-memory cache for API responses
API_CACHE = {}
API_CACHE_LOCK = threading.RLock()
CACHE_TTL = {
    'default': 300,        # 5 minutes
    'market_data': 60,     # 1 minute
    'news': 300,           # 5 minutes
    'benchmarks': 300,     # 5 minutes
    'portfolios': 600,     # 10 minutes
    'market_cycles': 600,  # 10 minutes
}

# API request limiter
MAX_CONCURRENT_REQUESTS = 3
ACTIVE_REQUESTS = 0
REQUEST_LOCK = threading.RLock()

def cache_api_response(ttl_category='default'):
    """
    Decorator for caching API responses
    
    Args:
        ttl_category: Category name to determine TTL from CACHE_TTL dict
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check cache first
            with API_CACHE_LOCK:
                if key in API_CACHE:
                    timestamp, value = API_CACHE[key]
                    ttl = CACHE_TTL.get(ttl_category, CACHE_TTL['default'])
                    if time.time() - timestamp < ttl:
                        logger.debug(f"Cache hit for {key}")
                        return value
            
            # Handle API request limiting
            global ACTIVE_REQUESTS
            with REQUEST_LOCK:
                # If too many active requests, return cached value even if expired
                if ACTIVE_REQUESTS >= MAX_CONCURRENT_REQUESTS:
                    with API_CACHE_LOCK:
                        if key in API_CACHE:
                            logger.info(f"Using expired cache due to request limit for {key}")
                            return API_CACHE[key][1]
                    
                    # If no cached value, wait briefly and check again
                    time.sleep(0.5)
                    with API_CACHE_LOCK:
                        if key in API_CACHE:
                            return API_CACHE[key][1]
                
                # Increment active requests
                ACTIVE_REQUESTS += 1
            
            try:
                # Call original function
                result = func(*args, **kwargs)
                
                # Cache the result
                with API_CACHE_LOCK:
                    API_CACHE[key] = (time.time(), result)
                
                return result
            except Exception as e:
                logger.error(f"Error in API call {func.__name__}: {e}")
                
                # Return cached value as fallback, even if expired
                with API_CACHE_LOCK:
                    if key in API_CACHE:
                        logger.info(f"Using expired cache as fallback for {key}")
                        return API_CACHE[key][1]
                
                # Re-raise if no fallback
                raise
            finally:
                # Always decrement active requests
                with REQUEST_LOCK:
                    ACTIVE_REQUESTS -= 1
        
        return wrapper
    return decorator

def patch_data_services():
    """
    Patch data_services.py functions with caching
    
    This function attempts to add caching to the main data retrieval 
    functions without modifying the original files.
    """
    try:
        import data_services
        
        # Save original functions
        original_get_yahoo_finance_data = data_services.get_yahoo_finance_data
        original_get_alpha_vantage_data = data_services.get_alpha_vantage_data
        original_get_live_data = data_services.get_live_data
        
        # Patch with cached versions
        @cache_api_response('market_data')
        def cached_get_yahoo_finance_data(symbol, swiss_stocks, indices):
            return original_get_yahoo_finance_data(symbol, swiss_stocks, indices)
        
        @cache_api_response('market_data')
        def cached_get_alpha_vantage_data(symbol):
            return original_get_alpha_vantage_data(symbol)
        
        @cache_api_response('market_data')
        def cached_get_live_data(symbol, swiss_stocks, indices):
            return original_get_live_data(symbol, swiss_stocks, indices)
        
        # Replace original functions with cached versions
        data_services.get_yahoo_finance_data = cached_get_yahoo_finance_data
        data_services.get_alpha_vantage_data = cached_get_alpha_vantage_data
        data_services.get_live_data = cached_get_live_data
        
        logger.info("Successfully patched data_services with caching")
        return True
    except Exception as e:
        logger.error(f"Failed to patch data_services: {e}")
        return False

def patch_route_adapter():
    """
    Patch route_adapter.py functions with caching
    """
    try:
        import route_adapter
        
        # Save original functions
        original_route_get_live_data = route_adapter.route_get_live_data
        original_route_refresh_all_markets = route_adapter.route_refresh_all_markets
        original_route_get_news = route_adapter.route_get_news
        original_route_get_benchmark_data = route_adapter.route_get_benchmark_data
        
        # Patch with cached versions
        @cache_api_response('market_data')
        def cached_route_get_live_data(symbol, swiss_stocks, indices):
            return original_route_get_live_data(symbol, swiss_stocks, indices)
        
        @cache_api_response('market_data')
        def cached_route_refresh_all_markets(symbols_to_fetch, swiss_stocks, indices):
            return original_route_refresh_all_markets(symbols_to_fetch, swiss_stocks, indices)
        
        @cache_api_response('news')
        def cached_route_get_news():
            return original_route_get_news()
        
        @cache_api_response('benchmarks')
        def cached_route_get_benchmark_data():
            return original_route_get_benchmark_data()
        
        # Replace original functions with cached versions
        route_adapter.route_get_live_data = cached_route_get_live_data
        route_adapter.route_refresh_all_markets = cached_route_refresh_all_markets
        route_adapter.route_get_news = cached_route_get_news
        route_adapter.route_get_benchmark_data = cached_route_get_benchmark_data
        
        logger.info("Successfully patched route_adapter with caching")
        return True
    except Exception as e:
        logger.error(f"Failed to patch route_adapter: {e}")
        return False

def add_loading_optimization_js():
    """
    Create JS file for optimizing front-end loading
    """
    try:
        import os
        
        # Create static directory if it doesn't exist
        os.makedirs('static', exist_ok=True)
        
        # JavaScript content
        js_content = """// Quick Performance Fix for Swiss Asset Manager

// Configuration
const PERFORMANCE_MODE = true;  // Enable performance mode by default
const MAX_CONCURRENT_REQUESTS = 2;  // Maximum number of concurrent API requests
const API_REQUEST_TIMEOUT = 5000;  // API request timeout (5 seconds)

// Load tracking
let pendingRequests = 0;
let initialLoadComplete = false;

// Show loading indicator
function showLoadingIndicator() {
    // Create or update loading indicator
    let loadingIndicator = document.getElementById('quick-loading-indicator');
    if (!loadingIndicator) {
        loadingIndicator = document.createElement('div');
        loadingIndicator.id = 'quick-loading-indicator';
        loadingIndicator.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">Loading data...</div>
        `;
        loadingIndicator.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background-color: rgba(10, 10, 10, 0.85);
            z-index: 10000;
            transition: opacity 0.5s;
        `;
        
        // Add spinner styles
        const style = document.createElement('style');
        style.textContent = `
            .loading-spinner {
                width: 50px;
                height: 50px;
                border: 5px solid rgba(138, 43, 226, 0.3);
                border-top: 5px solid #8A2BE2;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-bottom: 20px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .loading-text {
                color: white;
                font-family: 'Inter', sans-serif;
                font-size: 16px;
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(loadingIndicator);
    }
    
    // Auto-hide after 10 seconds (fallback)
    setTimeout(() => {
        hideLoadingIndicator();
    }, 10000);
}

// Hide loading indicator
function hideLoadingIndicator() {
    const loadingIndicator = document.getElementById('quick-loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.opacity = '0';
        setTimeout(() => {
            loadingIndicator.remove();
        }, 500);
    }
}

// Update loading status
function updateLoadingStatus(text) {
    const loadingText = document.querySelector('#quick-loading-indicator .loading-text');
    if (loadingText) {
        loadingText.textContent = text;
    }
}

// Override fetch to manage concurrent requests and provide feedback
const originalFetch = window.fetch;
window.fetch = function(url, options) {
    // Check if this is an API request
    const isApiRequest = typeof url === 'string' && (
        url.includes('/get_') || 
        url.includes('/update_') || 
        url.includes('/refresh_')
    );
    
    // For non-API requests, use original fetch
    if (!isApiRequest) {
        return originalFetch(url, options);
    }
    
    // For API requests, manage loading state
    pendingRequests++;
    
    // Show loading indicator if this is the first request
    if (pendingRequests === 1 && !initialLoadComplete) {
        showLoadingIndicator();
    }
    
    // Update loading status
    updateLoadingStatus(`Loading data... (${pendingRequests} pending)`);
    
    // Add timeout to the request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_REQUEST_TIMEOUT);
    
    const fetchOptions = {
        ...options,
        signal: controller.signal
    };
    
    // Make the request
    return originalFetch(url, fetchOptions)
        .then(response => {
            clearTimeout(timeoutId);
            pendingRequests--;
            
            // Update loading status
            if (pendingRequests > 0) {
                updateLoadingStatus(`Loading data... (${pendingRequests} pending)`);
            } else {
                hideLoadingIndicator();
                initialLoadComplete = true;
            }
            
            return response;
        })
        .catch(error => {
            clearTimeout(timeoutId);
            pendingRequests--;
            
            // Update loading status
            if (pendingRequests > 0) {
                updateLoadingStatus(`Loading data... (${pendingRequests} pending)`);
            } else {
                hideLoadingIndicator();
                initialLoadComplete = true;
            }
            
            console.error(`Error fetching ${url}:`, error);
            throw error;
        });
};

// Reduce animation complexity
function reduceAnimations() {
    if (PERFORMANCE_MODE) {
        document.body.classList.add('performance-mode');
        
        // Add performance styles if not already present
        if (!document.getElementById('performance-styles')) {
            const styles = document.createElement('style');
            styles.id = 'performance-styles';
            styles.textContent = `
                .performance-mode .layer {
                    opacity: 0.05 !important;
                    animation-duration: 40s, 50s, 60s !important;
                    filter: blur(30px) !important;
                }
                
                .performance-mode .pulse {
                    opacity: 0.03 !important;
                    animation-duration: 20s !important;
                }
            `;
            document.head.appendChild(styles);
        }
    }
}

// Prioritize essential resources
function prioritizeResources() {
    // Find non-essential scripts and defer them
    document.querySelectorAll('script').forEach(script => {
        if (script.src && 
            (script.src.includes('chart.js') || 
             script.src.includes('adapter') || 
             script.src.includes('font-awesome'))) {
            script.setAttribute('defer', '');
        }
    });
}

// Initialize performance optimizations
function initPerformanceOptimizations() {
    // Show initial loading indicator
    showLoadingIndicator();
    
    // Reduce animations
    reduceAnimations();
    
    // Prioritize resources
    prioritizeResources();
    
    // Mark page as loaded when everything is done
    window.addEventListener('load', () => {
        if (pendingRequests === 0) {
            hideLoadingIndicator();
            initialLoadComplete = true;
        }
    });
}

// Start optimizations immediately
initPerformanceOptimizations();
"""
        
        # Write JavaScript file
        js_path = os.path.join('static', 'quick-performance.js')
        with open(js_path, 'w') as f:
            f.write(js_content)
        
        logger.info(f"Created performance optimization JS at {js_path}")
        return js_path
    except Exception as e:
        logger.error(f"Failed to create performance JS: {e}")
        return None

def inject_js_into_html_template(html_template):
    """
    Inject our performance JS into the HTML template
    
    Args:
        html_template: Original HTML template string
        
    Returns:
        Modified HTML template with JS injection
    """
    try:
        # Find </head> tag
        head_end_pos = html_template.find('</head>')
        if head_end_pos == -1:
            logger.error("Could not find </head> tag in HTML template")
            return html_template
        
        # JS script tag to insert
        js_tag = '<script src="/static/quick-performance.js"></script>'
        
        # Insert JS tag before </head>
        new_template = html_template[:head_end_pos] + js_tag + html_template[head_end_pos:]
        
        # Add performance CSS
        css_pos = html_template.find('<style>')
        if css_pos != -1:
            performance_css = """
        /* Performance optimizations */
        .performance-mode .layer {
            opacity: 0.05 !important;
            animation-duration: 40s, 50s, 60s !important;
            filter: blur(30px) !important;
        }
        
        .performance-mode .pulse {
            opacity: 0.03 !important;
            animation-duration: 20s !important;
        }
        
        /* Loading indicator styles (fallback) */
        #quick-loading-indicator {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background-color: rgba(10, 10, 10, 0.85);
            z-index: 10000;
            transition: opacity 0.5s;
        }
            """
            style_end = html_template.find('</style>')
            if style_end != -1:
                new_template = new_template[:style_end] + performance_css + new_template[style_end:]
        
        logger.info("Successfully injected performance JS into HTML template")
        return new_template
    except Exception as e:
        logger.error(f"Failed to inject JS: {e}")
        return html_template

def apply_quick_performance_fix():
    """
    Apply all quick performance fixes
    """
    results = {
        'data_services_patched': patch_data_services(),
        'route_adapter_patched': patch_route_adapter(),
        'js_created': add_loading_optimization_js() is not None
    }
    
    logger.info(f"Quick performance fix results: {results}")
    return all(results.values())