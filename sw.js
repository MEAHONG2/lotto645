// 앱 화면은 저장해 두고(오프라인 가능), 당첨번호 데이터는 항상 새로 받아요.
const CACHE = "lotto645-v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "vendor/jsQR.js", "data/draws.json",
  "icons/icon-192.png", "icons/icon-512.png", "icons/maskable-512.png", "icons/favicon.png", "icons/apple-touch-icon.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const isData = url.pathname.endsWith("/data/draws.json");
  const isFont = url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com";
  if (url.origin !== location.origin && !isFont) return;

  if (isData || req.mode === "navigate") {
    // 네트워크 우선: 새 회차와 새 화면을 먼저 받고, 안 되면 저장본
    e.respondWith(fetch(req).then((res) => {
      const copy = res.clone(); caches.open(CACHE).then((c) => c.put(isData ? "data/draws.json" : req, copy));
      return res;
    }).catch(() => caches.match(isData ? "data/draws.json" : req).then((r) => r || caches.match("index.html"))));
    return;
  }
  // 나머지: 저장본 먼저, 뒤에서 갱신
  e.respondWith(caches.match(req).then((hit) => {
    const net = fetch(req).then((res) => {
      if (res.ok || res.type === "opaque") { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => hit);
    return hit || net;
  }));
});
