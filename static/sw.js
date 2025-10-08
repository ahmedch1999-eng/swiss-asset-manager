// Service Worker für Swiss Asset Pro
const CACHE_NAME = 'swiss-asset-pro-v1';
const urlsToCache = [
  '/',
  '/static/icon-192x192.png',
  '/static/icon-512x512.png'
];

// Installation des Service Workers
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache geöffnet');
        return cache.addAll(urlsToCache);
      })
  );
});

// Aktivierung des Service Workers
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Abfangen von Netzwerkanfragen
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - Rückgabe der Antwort aus dem Cache
        if (response) {
          return response;
        }
        
        // Klonen der Anfrage, da sie nur einmal verwendet werden kann
        const fetchRequest = event.request.clone();
        
        return fetch(fetchRequest).then(
          response => {
            // Prüfen, ob wir eine gültige Antwort erhalten haben
            if(!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // Klonen der Antwort, da sie nur einmal verwendet werden kann
            const responseToCache = response.clone();
            
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
              
            return response;
          }
        );
      })
  );
});