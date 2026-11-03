"""v6.9.10 — the Command Center top bar always gets the room it needs (no spilling over the page),
even when the page's grid row is wrongly one row tall (what Apple's WebKit does at 110% text).
Run from repo root: python3 test_v6910_topbar_room.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 9012
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
CHECK = """() => { var tb=document.querySelector('.topbar'), r=tb.getBoundingClientRect(), b=r.top;
  [].forEach.call(tb.children, function(c){ var q=c.getBoundingClientRect(); if (q.height && getComputedStyle(c).display!=='none') b=Math.max(b,q.bottom); });
  var sb=document.querySelector('.sidebar').getBoundingClientRect(), mn=document.querySelector('.main').getBoundingClientRect();
  return { barBottom: Math.round(r.bottom), contentBottom: Math.round(b), sidebarTop: Math.round(sb.top), mainTop: Math.round(mn.top) }; }"""
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for w, h, zoom, theme, ipad in ((1000, 574, '110', 'light', False), (1000, 574, '110', 'light', True), (1440, 900, '100', 'dark', False), (820, 1180, '120', 'light', True)):
                name = '%dx%d %s%% %s %s' % (w, h, zoom, theme, 'iPad' if ipad else 'Mac')
                print('\n' + name)
                ctx = await b.new_context(viewport={'width': w, 'height': h}, has_touch=ipad)
                init = "try{localStorage.setItem('bp_zoom_d','%s');localStorage.setItem('pb2d_theme','%s');}catch(e){}" % (zoom, theme)
                if ipad: init += "Object.defineProperty(navigator,'maxTouchPoints',{get:function(){return 5}});window.BPShell={version:'t',caps:{ai:true}};"
                await ctx.add_init_script(init)
                pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
                ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
                await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(2500)
                await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
                await pg.wait_for_timeout(600)
                r = await pg.evaluate(CHECK)
                ok(r['barBottom'] >= r['contentBottom'] - 1 and r['sidebarTop'] >= r['contentBottom'] - 1 and r['mainTop'] >= r['contentBottom'] - 1, 'top bar holds all its rows; page starts below it %s' % r)
                # what WebKit does: the grid row stays one row tall
                await pg.evaluate("var s=document.createElement('style'); s.textContent='.topbar{height:60px !important}'; document.head.appendChild(s); document.querySelector('.shell').style.removeProperty('grid-template-rows'); document.querySelector('.topbar').style.removeProperty('min-height'); s2=document.createElement('style'); s2.textContent='.shell{grid-template-rows:60px 1fr}'; document.head.appendChild(s2); window.dispatchEvent(new Event('resize'));")
                await pg.wait_for_timeout(400)
                r = await pg.evaluate(CHECK)
                ok(r['barBottom'] >= r['contentBottom'] - 1 and r['mainTop'] >= r['contentBottom'] - 1, 'even with the row squeezed to one line (WebKit), nothing spills over %s' % r)
                await pg.evaluate("localStorage.setItem('bp_zoom_d','150'); document.body.style.zoom='1.5'"); await pg.wait_for_timeout(500)
                r = await pg.evaluate(CHECK)
                ok(r['barBottom'] >= r['contentBottom'] - 1 and r['mainTop'] >= r['contentBottom'] - 1, 'text size changed to 150 percent: still fits %s' % r)
                ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
