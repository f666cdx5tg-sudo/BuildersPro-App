"""v6.9.12 — the Command Center side menu reaches the bottom of the iPad screen at every Text Size,
so its last items (Sync, Archived Jobs…) can always be scrolled into view.
Run from repo root: python3 test_v6912_sidebar_scroll.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8982
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};Object.defineProperty(navigator,'maxTouchPoints',{get:function(){return 5;}});"
IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 BuildersProShell'
M = """(()=>{var s=document.querySelector('aside.sidebar');var it=s.querySelectorAll('.ni');var last=it[it.length-1];
 s.scrollTop=99999;var r=s.getBoundingClientRect(),lr=last.getBoundingClientRect();
 return {bottom:r.bottom,vh:innerHeight,lastBottom:lr.bottom,scrolls:s.scrollHeight>s.clientHeight||lr.bottom<=innerHeight}})()"""
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for w, h in ((1180, 820), (1366, 1024), (1024, 1366)):
                for z in (100, 115, 130, 160):
                    ctx = await b.new_context(viewport={'width': w, 'height': h}, user_agent=IPAD, has_touch=True)
                    await ctx.add_init_script(SHELL); await ctx.add_init_script("localStorage.setItem('bp_zoom_d','%d')" % z)
                    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
                    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
                    await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(5000)
                    r = await pg.evaluate(M)
                    ok(r['bottom'] <= r['vh'] + 1 and r['lastBottom'] <= r['vh'], 'iPad %dx%d text %d%%: last menu item reachable (menu bottom %d, item bottom %d, screen %d)' % (w, h, z, r['bottom'], r['lastBottom'], r['vh']))
                    if z == 100 and w == 1180:
                        await pg.evaluate("document.body.style.zoom='1.3'"); await pg.wait_for_timeout(600)
                        r = await pg.evaluate(M)
                        ok(r['bottom'] <= r['vh'] + 1 and r['lastBottom'] <= r['vh'], 'changing Text Size live re-fits the menu (bottom %d, screen %d)' % (r['bottom'], r['vh']))
                    ok(not errs, 'no page errors %s' % errs[:1])
                    await ctx.close()
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
