// Performance and Error Monitoring
class SwissAssetProMonitoring {
    constructor() {
        this.init();
    }

    init() {
        this.setupErrorTracking();
        this.setupPerformanceTracking();
        this.setupUserInteractionTracking();
        this.setupOfflineTracking();
    }

    setupErrorTracking() {
        // Global error handler
        window.addEventListener('error', (event) => {
            this.trackError({
                type: 'javascript_error',
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                stack: event.error?.stack,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                url: window.location.href
            });
        });

        // Unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.trackError({
                type: 'unhandled_promise_rejection',
                message: event.reason?.message || 'Unknown promise rejection',
                stack: event.reason?.stack,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                url: window.location.href
            });
        });

        // Service Worker errors
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('error', (event) => {
                this.trackError({
                    type: 'service_worker_error',
                    message: event.message,
                    timestamp: new Date().toISOString(),
                    userAgent: navigator.userAgent,
                    url: window.location.href
                });
            });
        }
    }

    setupPerformanceTracking() {
        // Web Vitals
        this.trackWebVitals();
        
        // Custom performance metrics
        window.addEventListener('load', () => {
            setTimeout(() => {
                this.trackCustomMetrics();
            }, 1000);
        });
    }

    trackWebVitals() {
        // Largest Contentful Paint
        if ('PerformanceObserver' in window) {
            try {
                const lcpObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    const lastEntry = entries[entries.length - 1];
                    this.trackMetric('lcp', lastEntry.startTime);
                });
                lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
            } catch (e) {
                console.warn('LCP tracking not supported');
            }

            // First Input Delay
            try {
                const fidObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    entries.forEach((entry) => {
                        this.trackMetric('fid', entry.processingStart - entry.startTime);
                    });
                });
                fidObserver.observe({ entryTypes: ['first-input'] });
            } catch (e) {
                console.warn('FID tracking not supported');
            }

            // Cumulative Layout Shift
            try {
                const clsObserver = new PerformanceObserver((list) => {
                    let clsValue = 0;
                    list.getEntries().forEach((entry) => {
                        if (!entry.hadRecentInput) {
                            clsValue += entry.value;
                        }
                    });
                    this.trackMetric('cls', clsValue);
                });
                clsObserver.observe({ entryTypes: ['layout-shift'] });
            } catch (e) {
                console.warn('CLS tracking not supported');
            }
        }
    }

    trackCustomMetrics() {
        const navigation = performance.getEntriesByType('navigation')[0];
        if (navigation) {
            this.trackMetric('dom_content_loaded', navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart);
            this.trackMetric('load_complete', navigation.loadEventEnd - navigation.loadEventStart);
            this.trackMetric('time_to_interactive', navigation.domInteractive - navigation.navigationStart);
        }

        // Resource loading times
        const resources = performance.getEntriesByType('resource');
        resources.forEach(resource => {
            if (resource.name.includes('swiss-asset-pro') || resource.name.includes('static/')) {
                this.trackMetric('resource_load_time', resource.duration, {
                    resource: resource.name,
                    size: resource.transferSize
                });
            }
        });
    }

    setupUserInteractionTracking() {
        // Track page views
        this.trackPageView();

        // Track user interactions
        document.addEventListener('click', (event) => {
            if (event.target.matches('.nav-tab, .btn, .structure-item')) {
                this.trackEvent('user_interaction', {
                    type: 'click',
                    element: event.target.className,
                    text: event.target.textContent?.trim().substring(0, 50)
                });
            }
        });

        // Track form submissions
        document.addEventListener('submit', (event) => {
            this.trackEvent('form_submission', {
                form_id: event.target.id,
                form_class: event.target.className
            });
        });
    }

    setupOfflineTracking() {
        window.addEventListener('online', () => {
            this.trackEvent('connection_status', { status: 'online' });
        });

        window.addEventListener('offline', () => {
            this.trackEvent('connection_status', { status: 'offline' });
        });
    }

    trackPageView() {
        this.trackEvent('page_view', {
            page: window.location.pathname,
            referrer: document.referrer,
            timestamp: new Date().toISOString()
        });
    }

    trackError(errorData) {
        console.error('Error tracked:', errorData);
        this.sendToAnalytics('error', errorData);
    }

    trackMetric(name, value, metadata = {}) {
        const metricData = {
            name,
            value,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            ...metadata
        };
        
        console.log('Metric tracked:', metricData);
        this.sendToAnalytics('metric', metricData);
    }

    trackEvent(eventName, eventData) {
        const event = {
            name: eventName,
            data: eventData,
            timestamp: new Date().toISOString(),
            url: window.location.href
        };
        
        console.log('Event tracked:', event);
        this.sendToAnalytics('event', event);
    }

    sendToAnalytics(type, data) {
        // In production, send to your analytics service
        // For now, we'll store locally and send to service worker
        const payload = {
            type: 'ANALYTICS_DATA',
            data: {
                type,
                payload: data,
                sessionId: this.getSessionId(),
                userId: this.getUserId()
            }
        };

        // Send to service worker
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage(payload);
        }

        // Store locally for offline sync
        this.storeOffline(payload);
    }

    getSessionId() {
        let sessionId = sessionStorage.getItem('swiss_asset_pro_session');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('swiss_asset_pro_session', sessionId);
        }
        return sessionId;
    }

    getUserId() {
        return localStorage.getItem('swiss_asset_pro_user_id') || 'anonymous';
    }

    storeOffline(data) {
        try {
            const offlineData = JSON.parse(localStorage.getItem('swiss_asset_pro_offline_data') || '[]');
            offlineData.push(data);
            
            // Keep only last 100 items
            if (offlineData.length > 100) {
                offlineData.splice(0, offlineData.length - 100);
            }
            
            localStorage.setItem('swiss_asset_pro_offline_data', JSON.stringify(offlineData));
        } catch (e) {
            console.warn('Failed to store offline data:', e);
        }
    }

    // Sync offline data when back online
    syncOfflineData() {
        if (!navigator.onLine) return;

        try {
            const offlineData = JSON.parse(localStorage.getItem('swiss_asset_pro_offline_data') || '[]');
            if (offlineData.length > 0) {
                // Send all offline data
                offlineData.forEach(data => {
                    this.sendToAnalytics(data.data.type, data.data.payload);
                });
                
                // Clear offline data
                localStorage.removeItem('swiss_asset_pro_offline_data');
            }
        } catch (e) {
            console.warn('Failed to sync offline data:', e);
        }
    }
}

// Initialize monitoring
const monitoring = new SwissAssetProMonitoring();

// Sync offline data when back online
window.addEventListener('online', () => {
    monitoring.syncOfflineData();
});

// Export for use in other scripts
window.SwissAssetProMonitoring = monitoring;
