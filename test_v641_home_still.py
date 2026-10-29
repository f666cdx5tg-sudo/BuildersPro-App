"""v6.4.1 — Home holds still: no rebuild of an unchanged On Site card, big Money Left drawn wide from the start,
background redraws keep the scroll position, fitting doesn't rerun on clock ticks.
Run from repo root: python3 test_v641_home_still.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8941
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { var t = new Date().toISOString();
  DB.jobs=[{id:'j1',name:'N. Peach St',client:'Shelden Washington',address:'1536 N. Peach St, Philadelphia, PA 19131',status:'Active',contract:20000,updatedAt:t}];
  DB.expenses=[{id:'e1',jobId:'j1',amount:29293.90,category:'Materials',date:'2026-10-20',updatedAt:t}];
  DB.rooms=[]; for (var i=0;i<6;i++) DB.rooms.push({id:'r'+i,jobId:'j1',name:'Room '+i,type:'Bathroom',updatedAt:t});
  DB.punchlist=[]; for (var i=0;i<40;i++) DB.punchlist.push({id:'p'+i,jobId:'j1',roomId:'r'+(i%6),text:'Item '+i,done:i<10,updatedAt:t});
  DB.shopping=[]; for (var i=0;i<9;i++) DB.shopping.push({id:'s'+i,jobId:'j1',text:'thing '+i,qty:1,bought:false});
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
            await pg.evaluate(SEED); await pg.evaluate("showScreen('s-home')"); await pg.wait_for_timeout(800)
            ok(await pg.evaluate("APP_VERSION") >= '6.4.1', 'on v6.4.1')
            ok(await pg.evaluate("document.querySelector('#bp-onsite-card [data-onsite=\"money\"]').classList.contains('bp-kpi-wide')"), 'big Money Left is drawn on its own row from the start')
            html = await pg.evaluate("bpOnSiteCardHtml('j1')")
            ok('class="bp-kpi-wide"' in html, 'the card is built wide (no flip after it shows)')
            await pg.evaluate("window.__card = document.getElementById('bp-onsite-card'); for (var i=0;i<5;i++) { try{ renderAll(); }catch(e){} try{ bpPaintHome286(); }catch(e){} }"); await pg.wait_for_timeout(300)
            ok(await pg.evaluate("window.__card === document.getElementById('bp-onsite-card')"), 'background refreshes do not rebuild an unchanged On Site card')
            await pg.evaluate("DB.expenses[0].amount = 1000; bpPaintHome286()"); await pg.wait_for_timeout(200)
            ok(await pg.evaluate("window.__card !== document.getElementById('bp-onsite-card') && /19,000|\\$19/.test(document.querySelector('#bp-onsite-card [data-onsite=\"money\"]').textContent)"), 'a real change still updates the card')
            await pg.evaluate("var h=document.getElementById('s-home'); h.scrollTop = 300; window.__y = h.scrollTop;")
            await pg.evaluate("for (var i=0;i<3;i++) { try{ renderAll(); }catch(e){} try{ bpRenderAttention(); }catch(e){} }"); await pg.wait_for_timeout(300)
            ok(await pg.evaluate("Math.abs(document.getElementById('s-home').scrollTop - window.__y) <= 1"), 'Home stays where it was through background redraws')
            await pg.evaluate("window.__fits=0; var o=window.bpFitNums; window.bpFitNums=function(){ window.__fits++; (window.__fst=window.__fst||[]).push(new Error().stack.split(String.fromCharCode(10)).slice(2,6).join(String.fromCharCode(32,124,32))); return o.apply(this,arguments); };")
            await pg.evaluate("window.__fits=0; window.__fst=[]")
            await pg.wait_for_timeout(4500)
            ok(await pg.evaluate("window.__fits") == 0, 'number fitting does not rerun on clock ticks (%s)' % await pg.evaluate("window.__fst"))
            ok(await pg.evaluate("getComputedStyle(document.getElementById('s-home')).overflowAnchor") == 'none', 'scroll anchoring is off')
            ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:%d/desktop.html' % PORT); await pg.wait_for_timeout(3000)
            ok(await pg.evaluate("APP_VERSION") >= '6.4.1', 'Command Center is v6.4.1')
            ok(not errs, 'Command Center: no page errors %s' % errs[:2]); await ctx.close()
            await b.close()
    finally: srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails))); sys.exit(1 if fails else 0)
asyncio.run(main())
