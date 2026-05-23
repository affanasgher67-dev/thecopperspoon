const CACHE_NAME = "copper-spoon-v3";

const PRECACHE_URLS = [
  "/static/app.css",
  "/static/app.js",
  "/static/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 1. Network-first for Navigation (HTML pages) and dynamic routes
  // We want to ensure /menu, /cart, /reservations, etc. are always fresh.
  const isNav = request.mode === "navigate" || request.headers.get("accept").includes("text/html");
  const isDynamic = url.pathname.startsWith("/api/") || url.pathname.startsWith("/admin/");

  if (isNav || isDynamic) {
    event.respondWith(
      fetch(request)
        .then((response) => response)
        .catch(() => {
          if (request.url.includes("/api/")) {
            return new Response(JSON.stringify({ error: "You appear to be offline." }), {
              headers: { "Content-Type": "application/json" },
              status: 503,
            });
          }
          // Fallback for offline pages if we had one (for now just 503)
          return new Response("This feature requires an active connection.", { status: 503 });
        })
    );
    return;
  }

  // 2. Cache-first with background revalidation for static assets (images, css, js)
  // This applies only to /static/ or CDN assets.
  const isStatic = url.pathname.startsWith("/static/") || 
                   url.hostname.includes("cdn") || 
                   url.hostname.includes("gstatic") || 
                   url.hostname.includes("googleapis");

  if (isStatic) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) {
          // Revalidate in the background
          fetch(request).then((response) => {
            if (response.ok) {
              caches.open(CACHE_NAME).then((cache) => cache.put(request, response));
            }
          }).catch(() => {});
          return cached;
        }
        return fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }
});
