"""v6.3.1 — same version everywhere + Money Left fits its tile.
1. Field app, Command Center, native project and service worker agree; the SW never reuses GitHub's cached copy.
2. Inside the app, a newer published version loads by itself (no banner); in a browser the banner still shows.
3. -$9,293.90 shrinks to fit the Money Left tile at every text size, even when Home was drawn while hidden,
   and the Home screen is never pushed sideways.
Run from repo root: python3 test_v631_versions_money.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, re
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8931
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { var t = new Date().toISOString();
  DB.jobs=[{id:'j1',name:'N. Peach St',client:'Shelden Washington',address:'1536 N. Peach St, Philadelphia, PA 19131',status:'Active',contract:20000,updatedAt:t}];
  DB.expenses=[{id:'e1',jobId:'j1',amount:29293.90,category:'Materials',date:'2026-10-28',updatedAt:t}];
  try{bpSave()}catch(e){} try{bpSetActiveJob('j1',true)}catch(e){} }"""

def files():
    print('\nFiles')
    w = re.search(r"var APP_VERSION = '([^']+)'", open(os.path.join(REPO, 'index.html'), encoding='utf-8').read()).group(1)
    d = re.search(r"var APP_VERSION = '([^']+)'", open(os.path.join(REPO, 'desktop.html'), encoding='utf-8').read()).group(1)
    n = re.search(r'MARKETING_VERSION: "([^"]+)"', open(os.path.join(REPO, 'native/project.yml')).read()).group(1)
    ok(w == d == n >= '6.3.1', 'field %s · command center %s · native %s all match' % (w, d, n))
    ok("cache: 'no-cache'" in open(os.path.join(REPO, 'sw.js')).read(), 'service worker always checks GitHub for the newest copy')
    ok('URLQueryItem(name: "t"' in open(os.path.join(REPO, 'native/Sources/ShellModel.swift')).read(), 'app asks for a never-cached page on launch')

async def main():
    files()
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for zoom in ('1.15', '1.3', '1.45'):
                print('\niPhone, text size %s' % zoom)
                ctx = await b.new_context(viewport={'width': 402, 'height': 874}, is_mobile=True, has_touch=True)
                pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
                await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
                await pg.evaluate("(z)=>{document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); window.bpICloudSync=undefined; localStorage.setItem('bp_zoom',z); try{bpApplyZoom()}catch(e){} document.documentElement.setAttribute('data-theme','light'); showScreen('s-punch');}", zoom)
                await pg.evaluate(SEED); await pg.wait_for_timeout(400)     # Home painted while hidden
                await pg.evaluate("showScreen('s-home')"); await pg.wait_for_timeout(900)
                r = await pg.evaluate("""() => { var n = document.querySelector('#bp-onsite-card [data-onsite="money"] .bp-kpi-num'); if (!n) return null;
                    var tile = n.parentElement.getBoundingClientRect(), num = n.getBoundingClientRect(); var h = document.getElementById('s-home');
                    return { text: n.textContent, fits: n.scrollWidth <= n.clientWidth + 1, inside: num.right <= tile.right + 1, sx: h.scrollLeft, docW: document.documentElement.scrollWidth, vw: innerWidth }; }""")
                ok(r and '9,293.90' in r['text'], 'Money Left shows pennies (%s)' % (r and r['text']))
                ok(r and r['fits'] and r['inside'], 'the number fits inside its tile')
                ok(r and r['sx'] == 0 and r['docW'] <= r['vw'], 'Home is not pushed sideways')
                ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()

            print('\nAuto-update')
            for shell in (True, False):
                ctx = await b.new_context(viewport={'width': 402, 'height': 874}, is_mobile=True)
                if shell: await ctx.add_init_script("window.webkit={messageHandlers:{bp:{postMessage:function(){}}}}; window.BPShell={version:'6.3.1',caps:{}};")
                pg = await ctx.new_page()
                await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
                await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
                await pg.evaluate("window.__went=''; window.bpApplyUpdate=function(v){ window.__went=v; }; var b=document.getElementById('bp-update-banner'); if(b) b.remove(); bpShowUpdateBanner('9.9.9')")
                went = await pg.evaluate("window.__went"); banner = await pg.evaluate("!!document.getElementById('bp-update-banner')")
                if shell: ok(went == '9.9.9' and not banner, 'in the app a newer version loads by itself, no banner')
                else: ok(went == '' and banner, 'in a browser the Update banner still shows')
                await ctx.close()
            print('\nCommand Center')
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(3000)
            ok(await pg.evaluate("APP_VERSION") >= '6.3.1', 'Command Center is v6.3.1')
            ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
            await b.close()
    finally: srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails))); sys.exit(1 if fails else 0)
asyncio.run(main())
