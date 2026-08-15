/**
 * sw.js — Veridict Service Worker
 *
 * Strategy, deliberately conservative to avoid ever showing stale data:
 *   - HTML pages: network-first (always get the latest page if online,
 *     fall back to cache only if offline)
 *   - CSS/JS/icons: cache-first (these rarely change and load instantly)
 *   - /api/* requests: NEVER cached — always go straight to network,
 *     since scan results, user data, and auth must always be fresh
 *
 * Cache version bump (CACHE_NAME) forces old caches to clear on deploy.
 */

const CACHE_NAME = 'veridict-cache-v1';

const STATIC_ASSETS = [
  '/main.css',
  '/dashboard.css',
  '/landing.css',
  '/scanner.css',
  '/pages.css',
  '/auth.js',
  '/utils.js',
  '/dashboard.js',
  '/scanner.js',
  '/settings.js',
  '/landing.js',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
];

// ── INSTALL — pre-cache static assets ──
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        // Don't let one missing file block install — cache what we can
        console.warn('Service worker: some assets failed to pre-cache', err);
      });
    })
  );
  self.skipWaiting();
});

// ── ACTIVATE — clean up old cache versions ──
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    )
  );
  self.clients.claim();
});

// ── FETCH — routing logic ──
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Never touch API requests — always network, always fresh
  if (url.pathname.startsWith('/api/')) {
    return; // let the browser handle it normally, no interception
  }

  // Only handle GET requests — never cache POST/PUT/DELETE
  if (event.request.method !== 'GET') {
    return;
  }

  const isStaticAsset = STATIC_ASSETS.some((asset) => url.pathname === asset);

  if (isStaticAsset) {
    // Cache-first for static assets
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        });
      })
    );
  } else {
    // Network-first for HTML pages and everything else
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
  }
});