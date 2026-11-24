/* Service worker: caches the app shell so the home-screen app opens instantly.
   API calls, uploads and outputs always go to the network (never cached). */
const CACHE = "albasmah-shell-v2";
const SHELL = ["/", "/index.html", "/style.css", "/app.js", "/login.html", "/offline.html", "/manifest.webmanifest",
  "/icons/icon-192.png", "/icons/apple-touch-icon.png",
  "/fonts/cairo-arabic-400-normal.woff2", "/fonts/cairo-arabic-700-normal.woff2",
  "/fonts/cairo-latin-400-normal.woff2", "/fonts/cairo-latin-700-normal.woff2"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(SHELL.map(u => c.add(new Request(u, { credentials: "same-origin" })).catch(() => null)))));
  self.skipWaiting();
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/outputs/")) return; // always live
  // network first (fresh code after updates), cache as offline fallback
  e.respondWith(fetch(e.request).then(r => {
    if (r.ok && r.type === "basic" && !r.redirected) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(e.request, cp)); }
    return r;
  }).catch(() => caches.match(e.request).then(m => m || (e.request.mode === "navigate" ? caches.match("/offline.html") : undefined))));
});
