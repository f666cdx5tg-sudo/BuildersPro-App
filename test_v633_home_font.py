"""v6.3.3 — opens on Home (launch, or back after 10+ min) + bigger Needs-your-attention text that shows in full.
Run from repo root: python3 test_v633_home_font.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8933
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { var t = new Date().toISOString();
  DB.jobs=[{id:'j1',name:'N. Peach St',status:'Active',contract:20000,updatedAt:t}];
  DB.expenses=[{id:'e1',jobId:'j1',desc:'x',amount:84263.31,date:'2026-10-20',category:'Materials'}];
  DB.rooms=[{id:'r1',jobId:'j1',name:'(F) Bathroom',type:'Bathroom',updatedAt:t}];
  try{bpSave()}catch(e){} try{bpSetActiveJob('j1',true)}catch(e){} }"""
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={'width': 402, 'height': 874}, is_mobile=True, has_touch=True)
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/index.html' % PORT); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); window.bpICloudSync=undefined; localStorage.setItem('bp_zoom','1.3'); try{bpApplyZoom()}catch(e){}")
            await pg.evaluate(SEED)
            ok(await pg.evaluate("APP_VERSION") >= '6.3.3', 'on v6.3.3')
            ok(await pg.evaluate("document.querySelector('#s-home').classList.contains('active')"), 'app opens on Home')
            await pg.evaluate("showScreen('s-home'); bpRenderAttention()"); await pg.wait_for_timeout(500)
            r = await pg.evaluate("""() => { var s = document.querySelector('#home-attention [data-attn="over"] span[data-bp-wrap]'); if (!s) return null; var c = getComputedStyle(s);
                return { fs: parseFloat(c.fontSize), ws: c.whiteSpace, full: s.scrollWidth <= s.clientWidth + 1, text: s.textContent }; }""")
            ok(r and r['fs'] >= 17, 'attention text is 17px or larger (%s)' % (r and r['fs']))
            ok(r and r['ws'] == 'normal' and r['full'] and 'over budget' in r['text'], 'the whole alert shows, wrapping if needed (%s)' % (r and r['text']))
            # away 11 minutes inside a space -> Home
            await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(500)
            async def away(ms):
                await pg.evaluate("""(ms) => { var real = Date.now; Object.defineProperty(document, 'hidden', { configurable: true, get: function(){ return true; } }); document.dispatchEvent(new Event('visibilitychange'));
                    Date.now = function(){ return real() + ms; }; Object.defineProperty(document, 'hidden', { configurable: true, get: function(){ return false; } }); document.dispatchEvent(new Event('visibilitychange')); Date.now = real; }""", ms)
                await pg.wait_for_timeout(300)
            await away(2 * 60 * 1000)
            ok(await pg.evaluate("document.querySelector('#s-room-detail').classList.contains('active')"), 'a 2-minute hop out and back stays in the space')
            await away(11 * 60 * 1000)
            ok(await pg.evaluate("document.querySelector('#s-room-detail').classList.contains('active')"), 'v6.6.4 (Stan, Oct 30: "come back where i left off"): back after 11 minutes stays in the space')
            await pg.evaluate("openRoomDetail('r1')"); await pg.wait_for_timeout(300)
            await pg.evaluate("var i=document.createElement('input'); i.id='tt'; document.getElementById('s-room-detail').appendChild(i); i.value='half typed'; i.focus();")
            await away(11 * 60 * 1000)
            ok(await pg.evaluate("document.querySelector('#s-room-detail').classList.contains('active')"), 'never jumps away while you are in the middle of typing')
            ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(3000)
            ok(await pg.evaluate("APP_VERSION") >= '6.3.3', 'Command Center is v6.3.3')
            ok(not errs, 'Command Center: no page errors %s' % errs[:2]); await ctx.close()
            await b.close()
    finally: srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails))); sys.exit(1 if fails else 0)
asyncio.run(main())
