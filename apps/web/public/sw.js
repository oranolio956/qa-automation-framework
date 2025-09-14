self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('onboarding-cache-v1').then((cache) => cache.addAll(['/']))
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        return cached || fetch(event.request).then((resp) => {
          const copy = resp.clone();
          caches.open('onboarding-cache-v1').then((cache) => cache.put(event.request, copy));
          return resp;
        }).catch(() => cached);
      })
    );
  }
});