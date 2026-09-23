// sw.js - Service Worker for Sustainability News Hub
// Strategy:
//   - news.json and page navigations  -> network-first (fresh news, offline fallback)
//   - static assets and CDN libraries -> cache-first (fast, offline-capable)
const CACHE_VERSION = 'v1790166291';
const STATIC_CACHE = `sustain-news-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `sustain-news-dynamic-${CACHE_VERSION}`;

const urlsToCache = [
  './',
  './index.html',
  './manifest.json',
  './news.json',
  './favicon.ico',
  './favicon-96x96.png',
  './apple-touch-icon.png',
  './web-app-manifest-192x192.png',
  './web-app-manifest-512x512.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://code.jquery.com/jquery-3.6.0.min.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js'
];

// Install: pre-cache the shell, tolerating individual failures.
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache =>
      Promise.all(
        urlsToCache.map(url =>
          fetch(url, { cache: 'reload' })
            .then(response => (response.ok ? cache.put(url, response) : null))
            .catch(() => console.warn('[SW] Skipped during install:', url))
        )
      )
    )
  );
  self.skipWaiting();
});

// Activate: drop every cache that is not the current version.
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(names =>
      Promise.all(
        names
          .filter(name => name !== STATIC_CACHE && name !== DYNAMIC_CACHE)
          .map(name => caches.delete(name))
      )
    )
  );
  self.clients.claim();
});

// Allow the page to trigger an immediate update.
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});

function isNewsRequest(url) {
  return url.pathname.endsWith('/news.json');
}

// Network-first: always try the network, fall back to the last good copy.
async function networkFirst(request, cacheName, fallbackUrl) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response && response.ok) {
      cache.put(fallbackUrl || request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await cache.match(fallbackUrl || request);
    if (cached) return cached;
    if (fallbackUrl) {
      const staticCache = await caches.open(STATIC_CACHE);
      const shell = await staticCache.match(fallbackUrl);
      if (shell) return shell;
    }
    throw err;
  }
}

// Cache-first: serve from cache, refresh in the background.
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response && response.ok && request.method === 'GET') {
    const cache = await caches.open(DYNAMIC_CACHE);
    cache.put(request, response.clone());
  }
  return response;
}

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Fresh news every time the app can reach the network.
  if (isNewsRequest(url)) {
    event.respondWith(networkFirst(request, DYNAMIC_CACHE, './news.json'));
    return;
  }

  // Never serve a stale app shell to an installed user.
  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, DYNAMIC_CACHE, './index.html'));
    return;
  }

  // Do not cache analytics or other beacons.
  if (url.hostname.includes('googletagmanager.com') || url.hostname.includes('google-analytics.com')) {
    return;
  }

  event.respondWith(cacheFirst(request).catch(() => caches.match('./index.html')));
});
