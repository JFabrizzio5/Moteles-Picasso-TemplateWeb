// Service worker de Picasso.
// - La app (HTML, JS, CSS, fotos de sucursales) se guarda para abrir sin señal.
// - La API nunca se guarda: un checklist viejo servido de caché sería peor que
//   un error. Lo que no se pudo subir lo guarda la pantalla en una cola propia.
const VERSION = 'picasso-v1'
const BASE = ['/', '/manifest.webmanifest', '/icono-192.png', '/marca/picasso-logo-blanco.svg']

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(BASE)))
  self.skipWaiting()
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((llaves) => Promise.all(llaves.filter((k) => k !== VERSION).map((k) => caches.delete(k)))),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (e.request.method !== 'GET' || url.origin !== self.location.origin) return
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/storage/')) return

  // Páginas: primero la red (para tener siempre la versión nueva), si no, caché.
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then((r) => {
          const copia = r.clone()
          caches.open(VERSION).then((c) => c.put('/', copia))
          return r
        })
        .catch(() => caches.match('/')),
    )
    return
  }

  // Archivos con huella (assets/*) y fotos: caché primero.
  e.respondWith(
    caches.match(e.request).then(
      (guardado) =>
        guardado ||
        fetch(e.request).then((r) => {
          if (r.ok) {
            const copia = r.clone()
            caches.open(VERSION).then((c) => c.put(e.request, copia))
          }
          return r
        }),
    ),
  )
})
