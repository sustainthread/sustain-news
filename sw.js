const CACHE_NAME = 'sustain-news-v2';
const BASE_PATH = self.location.pathname.replace(/\/sw\.js$/, ''); // Dynamically gets /sustain-news/

// Core app shell files to cache on install
const APP_SHELL_FILES = [
  BASE_PATH + '/',
  BASE_PATH + '/index.html',
  BASE_PATH + '/manifest.json',
  BASE_PATH + '/site.webmanifest',
  BASE_PATH + '/sw.js'
];

// Install: Cache the app shell
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing with base path:', BASE_PATH);
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL_FILES))
      .then(() => self.skipWaiting()) // Activate immediately
  );
});

// Activate: Clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log('[Service Worker] Deleting old cache:', cache);
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim()) // Take control of all open pages
  );
});

// Fetch: Serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const requestUrl = new URL(event.request.url);

  // Only handle requests from our origin (same site)
  if (requestUrl.origin !== location.origin) return;

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      // Return cached version if found
      if (cachedResponse) {
        // IMPORTANT: Always fetch and update news.json in the background
        if (event.request.url.includes('news.json')) {
          fetchAndCacheNews(event.request);
        }
        return cachedResponse;
      }

      // Not in cache? Fetch from network.
      return fetch(event.request).then((networkResponse) => {
        // Check if we received a valid response
        if (!networkResponse || networkResponse.status !== 200) {
          return networkResponse;
        }

        // Clone the response and cache it for future visits
        const responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });

        return networkResponse;
      }).catch(() => {
        // If both cache and network fail, provide a fallback for HTML
        if (event.request.headers.get('accept').includes('text/html')) {
          return caches.match(BASE_PATH + '/index.html');
        }
        // Could return an offline page here in the future
      });
    })
  );
});

// Helper function to update news cache in the background
function fetchAndCacheNews(newsRequest) {
  fetch(newsRequest).then((response) => {
    if (response.ok) {
      caches.open(CACHE_NAME).then((cache) => {
        cache.put(newsRequest, response);
        console.log('[Service Worker] News data updated in cache.');
      });
    }
  });
}
