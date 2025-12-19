// sw.js - Service Worker for Sustain News
const CACHE_NAME = 'sustain-news-v2';
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

// Replace the entire 'install' event listener with this:
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        // Cache the core local files first, which are critical
        const criticalResources = [
          './',
          './index.html',
          './news.json',
          './favicon.ico'
        ];
        // Try to add all critical resources, but don't fail the whole install
        return cache.addAll(criticalResources)
          .then(() => {
            console.log('All critical resources cached');
            // For external URLs, use cache.put() to handle failures individually
            const externalResources = [
              'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
              'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
              'https://code.jquery.com/jquery-3.6.0.min.js',
              'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js'
            ];
            
            // Cache each external resource individually, ignoring failures
            const cachePromises = externalResources.map(url => {
              return fetch(url)
                .then(response => {
                  // Only cache valid responses
                  if (response.ok) {
                    return cache.put(url, response);
                  }
                  console.log('Failed to cache:', url);
                })
                .catch(err => {
                  console.log('Error fetching for cache:', url, err);
                });
            });
            
            return Promise.all(cachePromises);
          });
      })
  );
  self.skipWaiting();
});

// Fetch event - serve from cache if available
self.addEventListener('fetch', event => {
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin) && 
      !event.request.url.startsWith('https://www.google.com/s2/favicons')) {
    return;
  }
  
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request)
          .then(response => {
            // Don't cache if not a valid response
            if(!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // Clone the response
            const responseToCache = response.clone();
            
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
              
            return response;
          });
      })
  );
});

// Activate event - clean up old caches
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
  self.clients.claim();
});
