// sw.js - Service Worker for Sustain News
const CACHE_NAME = 'sustain-news-v3'; // Incremented version

// Assets to cache
const urlsToCache = [
  './',
  './index.html',
  './news.json',
  './favicon.ico',
  './favicon-96x96.png',
  './favicon.svg',
  './apple-touch-icon.png',
  './android-chrome-192x192.png',
  './android-chrome-512x512.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://code.jquery.com/jquery-3.6.0.min.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js'
];

// Install Event
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('Opened cache');
      // We use map to attempt to cache everything, but allow individual failures
      return Promise.all(
        urlsToCache.map(url => {
          return fetch(url).then(response => {
            if (response.ok) {
              return cache.put(url, response);
            }
          }).catch(err => console.warn('Failed to cache during install:', url));
        })
      );
    })
  );
  self.skipWaiting();
});

// Activate Event
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch Event - Crucial for "Installable" status
self.addEventListener('fetch', event => {
  // Respond with cache, fallback to network
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(event.request).then(response => {
        // Check if we received a valid response
        // REMOVED: response.type !== 'basic' (to allow CDN/CORS caching)
        if (!response || response.status !== 200) {
          return response;
        }

        // Only cache GET requests and safe schemes
        if (event.request.method === 'GET' && event.request.url.startsWith('http')) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
        }

        return response;
      }).catch(() => {
        // Optional: Return a custom offline page here if fetch fails
      });
    })
  );
});
