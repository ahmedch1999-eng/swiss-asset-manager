// Performance optimized loading of data
// This script implements deferred loading and better UI feedback

// Configuration
const PERFORMANCE_MODE = true;  // Set to true to enable performance optimizations
const DEFER_TIMEOUT = 500;      // Time to wait before loading non-essential data (ms)
const MAX_CONCURRENT_REQUESTS = 2; // Maximum number of concurrent API requests
const LOADING_TIMEOUT = 10000;  // Timeout for loading indicator (ms)

// State tracking
let loadingQueue = [];
let activeRequests = 0;
let initialLoadComplete = false;
let pageFullyLoaded = false;

// Activate performance mode - reduces background animations
function activatePerformanceMode() {
    if (PERFORMANCE_MODE) {
        document.body.classList.add('performance-mode');
        console.log("Performance mode activated");
    }
}

// Show loading indicator
function showLoadingIndicator() {
    // Create loading indicator if it doesn't exist
    if (!document.getElementById('loading-indicator')) {
        const loadingIndicator = document.createElement('div');
        loadingIndicator.id = 'loading-indicator';
        loadingIndicator.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">Loading essential data...</div>
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
            color: #e0e0e0;
            font-family: 'Inter', sans-serif;
            transition: opacity 0.5s ease;
        `;
        
        const spinnerStyle = document.createElement('style');
        spinnerStyle.textContent = `
            .loading-spinner {
                width: 50px;
                height: 50px;
                border: 5px solid rgba(138, 43, 226, 0.3);
                border-top: 5px solid #8a2be2;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-bottom: 20px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .loading-text {
                font-size: 16px;
                margin-top: 10px;
            }
        `;
        document.head.appendChild(spinnerStyle);
        document.body.appendChild(loadingIndicator);
        
        // Set timeout to hide the indicator even if loading takes too long
        setTimeout(() => {
            hideLoadingIndicator();
            initialLoadComplete = true;
        }, LOADING_TIMEOUT);
    }
}

// Update loading status
function updateLoadingStatus(message) {
    const textElement = document.querySelector('#loading-indicator .loading-text');
    if (textElement) {
        textElement.textContent = message;
    }
}

// Hide loading indicator
function hideLoadingIndicator() {
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.opacity = '0';
        setTimeout(() => {
            loadingIndicator.remove();
        }, 500);
    }
}

// Enhanced fetch function with queuing
async function fetchWithQueue(url, options = {}) {
    return new Promise((resolve, reject) => {
        // Add to queue
        loadingQueue.push({
            url,
            options,
            resolve,
            reject
        });
        
        // Start processing queue
        processQueue();
    });
}

// Process request queue
function processQueue() {
    // If we're already at max concurrent requests, wait
    if (activeRequests >= MAX_CONCURRENT_REQUESTS) {
        return;
    }
    
    // Get next request from queue
    const request = loadingQueue.shift();
    if (!request) {
        // Queue empty
        if (activeRequests === 0 && !initialLoadComplete) {
            // All initial requests complete
            initialLoadComplete = true;
            hideLoadingIndicator();
        }
        return;
    }
    
    // Process request
    activeRequests++;
    
    fetch(request.url, request.options)
        .then(response => response.json())
        .then(data => {
            activeRequests--;
            request.resolve(data);
            // Process next in queue
            processQueue();
        })
        .catch(error => {
            activeRequests--;
            request.reject(error);
            // Process next in queue
            processQueue();
        });
}

// Prioritize essential data
function loadEssentialData() {
    // Define essential data endpoints
    const essentialEndpoints = [
        '/refresh_all_markets',
        '/get_news'
    ];
    
    // Load each endpoint
    essentialEndpoints.forEach((endpoint, index) => {
        setTimeout(() => {
            updateLoadingStatus(`Loading essential data (${index+1}/${essentialEndpoints.length})...`);
            fetchWithQueue(endpoint)
                .then(data => {
                    console.log(`Loaded essential data from ${endpoint}`);
                })
                .catch(error => {
                    console.error(`Error loading data from ${endpoint}:`, error);
                });
        }, index * 100); // Stagger requests slightly
    });
}

// Defer non-essential data loading
function loadNonEssentialData() {
    // Define non-essential data endpoints
    const nonEssentialEndpoints = [
        '/get_benchmark_data',
        '/update_bank_portfolios',
        '/update_market_cycles'
    ];
    
    // Load each endpoint with a delay
    nonEssentialEndpoints.forEach((endpoint, index) => {
        setTimeout(() => {
            fetchWithQueue(endpoint)
                .then(data => {
                    console.log(`Loaded non-essential data from ${endpoint}`);
                })
                .catch(error => {
                    console.error(`Error loading data from ${endpoint}:`, error);
                });
        }, DEFER_TIMEOUT + (index * 500)); // Staggered loading with initial delay
    });
}

// Initialize performance optimizations
function initPerformanceOptimizations() {
    // Activate performance mode for animations
    activatePerformanceMode();
    
    // Show loading indicator for initial load
    showLoadingIndicator();
    
    // Load essential data immediately
    loadEssentialData();
    
    // Defer non-essential data loading
    setTimeout(loadNonEssentialData, DEFER_TIMEOUT);
    
    // Hook into window load event to mark page as fully loaded
    window.addEventListener('load', () => {
        pageFullyLoaded = true;
        if (!initialLoadComplete) {
            hideLoadingIndicator();
            initialLoadComplete = true;
        }
    });
}

// Call initialization when the script is loaded
initPerformanceOptimizations();