import Foundation

/// JavaScript the app slips into the web page so the web code's normal calls
/// (navigator.share, download links, window.print) reach the native iPhone/Mac features.
/// The web app itself needs no changes — it just sees a browser that can share, save and print.
enum Bridge {
    static let handlerName = "bp"

    /// Runs before the page's own scripts.
    static let startScript = #"""
    (function(){
      if (window.BPShell) return;
      window.BPShell = { version: '__VERSION__', caps: __CAPS__ };

      /* Face ID is handled by the app before the page is shown, so the web passcode screen is skipped. */
      try {
        var st = document.createElement('style');
        st.textContent = '#bp-lock{display:none!important}';
        document.documentElement.appendChild(st);
      } catch(e){}

      /* Full-screen like the Home Screen app — the web layout code checks this. */
      try { Object.defineProperty(navigator, 'standalone', { get: function(){ return true; }, configurable: true }); } catch(e){}

      function post(m){ try { window.webkit.messageHandlers.bp.postMessage(m); } catch(e){} }
      function toB64(blob){
        return new Promise(function(res, rej){
          var r = new FileReader();
          r.onload = function(){ var s = String(r.result); res(s.slice(s.indexOf(',') + 1)); };
          r.onerror = function(){ rej(r.error); };
          r.readAsDataURL(blob);
        });
      }
      async function send(kind, files, text, title){
        var out = [];
        for (var i = 0; i < files.length; i++) {
          var f = files[i];
          out.push({ name: f.name || 'file', type: f.type || 'application/octet-stream', b64: await toB64(f) });
        }
        post({ kind: kind, files: out, text: text || '', title: title || '' });
      }

      /* Share sheet */
      navigator.canShare = function(d){ return !!(d && ((d.files && d.files.length) || d.text || d.url || d.title)); };
      navigator.share = function(d){
        d = d || {};
        var files = d.files ? Array.prototype.slice.call(d.files) : [];
        var text = [d.text, d.url].filter(Boolean).join('\n');
        return send('share', files, text, d.title);
      };

      /* Download links (CSV, backups, PDFs) -> Save / share sheet */
      function grab(a){
        var h = a.href || '', dl = a.getAttribute('download');
        if (dl === null) return false;
        if (h.indexOf('blob:') !== 0 && h.indexOf('data:') !== 0) return false;
        var name = dl || 'download';
        fetch(h).then(function(r){ return r.blob(); })
          .then(function(b){ return send('save', [new File([b], name, { type: b.type })], '', name); })
          .catch(function(){});
        return true;
      }
      var origClick = HTMLAnchorElement.prototype.click;
      HTMLAnchorElement.prototype.click = function(){
        if (grab(this)) return;
        return origClick.apply(this, arguments);
      };
      document.addEventListener('click', function(e){
        var a = e.target && e.target.closest ? e.target.closest('a[download]') : null;
        if (a && grab(a)) { e.preventDefault(); e.stopPropagation(); }
      }, true);

      /* Print / Save as PDF */
      window.print = function(){ post({ kind: 'print' }); };

      /* Drop the hidden web lock screen once the page is built. */
      document.addEventListener('DOMContentLoaded', function(){
        var l = document.getElementById('bp-lock');
        if (l) { l.remove(); if (typeof window.bpForceRepaintNudge === 'function') { try { window.bpForceRepaintNudge(); } catch(e){} } }
      });
    })();
    """#
}
