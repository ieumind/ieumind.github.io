/* 생각이음 · 알림 받기 (Web Push). 화면 파일을 따로 저장해 두지는 않는다(늘 최신 화면) */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data ? e.data.text() : "" }; }
  const scope = self.registration.scope;
  e.waitUntil(self.registration.showNotification(d.title || "생각이음", {
    body: d.body || "", icon: scope + "icons/icon-192.png?v=2", badge: scope + "icons/icon-192.png?v=2",
    tag: d.tag || undefined, renotify: !!d.tag, data: { url: scope + (d.url || "") }
  }));
});
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || self.registration.scope;
  e.waitUntil((async () => {
    const list = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of list) {
      if (c.url.startsWith(self.registration.scope)) { await c.focus(); try { await c.navigate(url); } catch (_) { c.postMessage({ open: url }); } return; }
    }
    await self.clients.openWindow(url);
  })());
});
