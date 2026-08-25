/* Lernwerkstatt – Offline-Betrieb.
 *
 * Zwei Regeln:
 *  - Die Seite selbst wird zuerst aus dem Netz geholt (damit Updates
 *    ankommen) und nur bei fehlender Verbindung aus dem Speicher.
 *  - Alles andere kommt zuerst aus dem Speicher (schnell, offline sicher)
 *    und wird im Hintergrund aufgefrischt.
 *
 * Der Lernstand liegt im localStorage und ist davon unberührt.
 */
const CACHE = 'lernwerkstatt-v1';
const SCHATZ = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
  './apple-touch-icon.png'
];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE)
      .then(function (c) { return c.addAll(SCHATZ); })
      .then(function () { return self.skipWaiting(); })
      .catch(function () { /* einzelne Datei fehlt: trotzdem weitermachen */ })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (namen) {
      return Promise.all(namen.map(function (nm) {
        return nm === CACHE ? null : caches.delete(nm);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  const eigen = url.origin === self.location.origin;

  /* Die Seite: erst Netz, dann Speicher. */
  if (req.mode === 'navigate' || (eigen && url.pathname.endsWith('.html'))) {
    e.respondWith(
      fetch(req).then(function (r) {
        const kopie = r.clone();
        caches.open(CACHE).then(function (c) { c.put(req, kopie); });
        return r;
      }).catch(function () {
        return caches.match(req).then(function (t) {
          return t || caches.match('./index.html');
        });
      })
    );
    return;
  }

  /* Alles andere: erst Speicher, im Hintergrund auffrischen. */
  e.respondWith(
    caches.match(req).then(function (treffer) {
      const netz = fetch(req).then(function (r) {
        if (r && (r.status === 200 || r.type === 'opaque')) {
          const kopie = r.clone();
          caches.open(CACHE).then(function (c) { c.put(req, kopie); });
        }
        return r;
      }).catch(function () { return treffer; });
      return treffer || netz;
    })
  );
});
