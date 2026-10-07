/* BuildersPro service worker (v3.64)
   Network first, saved copy as fallback: when you have signal you always get the
   newest app (so updates behave exactly as before); with no signal — a basement,
   a crawlspace — the last copy you opened still launches. Only this app's own
   files are touched; sync (GitHub), weather and other sites go straight through. */
var CACHE = 'bp-app-v1';
var CORE = ['./', './index.html', './manifest.webmanifest'];
self.addEventListener('install', function(e){
  e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(CORE).catch(function(){}); }).then(function(){ return self.skipWaiting(); }));
});
self.addEventListener('activate', function(e){
  e.waitUntil(caches.keys().then(function(ks){ return Promise.all(ks.filter(function(k){ return k !== CACHE; }).map(function(k){ return caches.delete(k); })); }).then(function(){ return self.clients.claim(); }));
});
function keyFor(req){ var u = new URL(req.url); u.search = ''; return u.toString(); }
self.addEventListener('fetch', function(e){
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  e.respondWith(
    fetch(req).then(function(res){
      if (res && res.ok && res.type === 'basic') { var copy = res.clone(); caches.open(CACHE).then(function(c){ c.put(keyFor(req), copy); }); }
      return res;
    }).catch(function(){
      return caches.match(keyFor(req)).then(function(hit){
        return hit || (req.mode === 'navigate' ? caches.match('./index.html') : undefined) || Response.error();
      });
    })
  );
});
