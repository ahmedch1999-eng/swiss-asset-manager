// Quick Performance Fix for Swiss Asset Manager

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
