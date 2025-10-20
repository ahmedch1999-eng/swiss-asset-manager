const CACHE_NAME = 'swiss-asset-pro-v1.1.0';
const STATIC_CACHE = 'static-v1.1.0';
const DYNAMIC_CACHE = 'dynamic-v1.1.0';
const API_CACHE = 'api-v1.1.0';

// Critical resources to cache immediately
const CRITICAL_RESOURCES = [
  '/',
  '/static/getting-started-custom.css',
  '/static/performance.js',
  '/static/quick-performance.js',
  '/static/nav-actions.js',
  '/static/app-bootstrap.js',
  '/static/login-init.js',
  '/static/sw-register.js',
  '/static/icon-192x192.png',
  '/static/icon-512x512.png',
  '/manifest.json'
];

// API endpoints to cache
const API_ENDPOINTS = [
  '/get_benchmark_data',
  '/get_news',
  '/refresh_all_markets'
];

// Install event - cache critical resources
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Service Worker: Caching critical resources');
        return cache.addAll(CRITICAL_RESOURCES);
      })
      .then(() => {
        console.log('Service Worker: Installation complete');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('Service Worker: Installation failed', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
            if (cacheName !== STATIC_CACHE && 
                cacheName !== DYNAMIC_CACHE && 
                cacheName !== API_CACHE) {
              console.log('Service Worker: Deleting old cache', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
      })
      .then(() => {
        console.log('Service Worker: Activation complete');
        return self.clients.claim();
      })
  );
});

// Fetch event - serve from cache with network fallback
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Handle API requests
  if (url.pathname.startsWith('/api/') || API_ENDPOINTS.includes(url.pathname)) {
    event.respondWith(
      caches.open(API_CACHE)
        .then(cache => {
          return cache.match(request)
            .then(response => {
              if (response) {
                // Return cached response and update in background
                fetch(request)
                  .then(fetchResponse => {
                    if (fetchResponse.ok) {
                      cache.put(request, fetchResponse.clone());
                    }
                  })
                  .catch(() => {}); // Ignore network errors for background update
                return response;
              }
              
              // No cache, fetch from network
              return fetch(request)
                .then(fetchResponse => {
                  if (fetchResponse.ok) {
                    cache.put(request, fetchResponse.clone());
                  }
                  return fetchResponse;
                })
                .catch(() => {
                  // Return offline fallback for API requests
                  return new Response(
                    JSON.stringify({ 
                      error: 'Offline', 
                      message: 'Keine Internetverbindung. Bitte versuchen Sie es später erneut.' 
                    }),
                    { 
                      status: 503, 
                      headers: { 'Content-Type': 'application/json' } 
                    }
                  );
                });
            });
        })
    );
    return;
  }

  // Handle static resources
  event.respondWith(
    caches.match(request)
      .then(response => {
        if (response) {
          return response;
        }

        // Not in cache, fetch from network
        return fetch(request)
          .then(fetchResponse => {
            // Don't cache non-successful responses
            if (!fetchResponse || fetchResponse.status !== 200 || fetchResponse.type !== 'basic') {
              return fetchResponse;
            }

            // Clone the response
            const responseToCache = fetchResponse.clone();

            // Cache the response
            caches.open(DYNAMIC_CACHE)
              .then(cache => {
                cache.put(request, responseToCache);
              });

            return fetchResponse;
          })
          .catch(() => {
            // Return offline fallback page for navigation requests
            if (request.mode === 'navigate') {
              return caches.match('/offline.html') || new Response(
                `
                <!DOCTYPE html>
                <html>
                <head>
                  <title>Offline - Swiss Asset Pro</title>
                  <meta name="viewport" content="width=device-width, initial-scale=1">
                  <style>
                    body { 
                      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                      background: #0A0A0A; color: #E0E0E0; margin: 0; padding: 20px;
                      display: flex; flex-direction: column; align-items: center; justify-content: center;
                      min-height: 100vh; text-align: center;
                    }
                    .offline-icon { font-size: 64px; color: #8A2BE2; margin-bottom: 20px; }
                    h1 { color: #8A2BE2; margin-bottom: 10px; }
                    p { color: #B0B0B0; margin-bottom: 20px; }
                    .retry-btn { 
                      background: #8A2BE2; color: white; border: none; padding: 12px 24px;
                      border-radius: 8px; cursor: pointer; font-size: 16px;
                    }
                  </style>
                </head>
                <body>
                  <div class="offline-icon">📱</div>
                  <h1>Offline</h1>
                  <p>Sie sind offline. Bitte überprüfen Sie Ihre Internetverbindung.</p>
                  <button class="retry-btn" onclick="window.location.reload()">Erneut versuchen</button>
                </body>
                </html>
                `,
                { 
                  status: 200, 
                  headers: { 'Content-Type': 'text/html' } 
                }
              );
            }
      });
    })
  );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

// Push notifications
self.addEventListener('push', event => {
  const options = {
    body: event.data ? event.data.text() : 'Neue Updates verfügbar',
    icon: '/static/icon-192x192.png',
    badge: '/static/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Öffnen',
        icon: '/static/icon-192x192.png'
      },
      {
        action: 'close',
        title: 'Schließen',
        icon: '/static/icon-192x192.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('Swiss Asset Pro', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Background sync function
async function doBackgroundSync() {
  try {
    // Sync any pending data when back online
    console.log('Service Worker: Background sync completed');
  } catch (error) {
    console.error('Service Worker: Background sync failed', error);
  }
}

// Performance monitoring
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'PERFORMANCE_METRIC') {
    // Send performance metrics to analytics
    console.log('Performance metric:', event.data.metric);
  }
});