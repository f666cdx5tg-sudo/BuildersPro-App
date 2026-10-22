"""BuildersPro v4.36 (shopping list: compact footer, no Bought total, no Materials-this-job strip).
Run from repo root: python3 test_v436.py (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs=[{id:'j1',name:'Smith Kitchen',status:'Active'}];
DB.shopping=[{id:'s1',jobId:'j1',text:'PEX 1/2 coil',qty:4,price:50,store:'Ferguson',bought:false,created:'2026-10-01'},
{id:'s3',jobId:'j1',text:'Old valve',qty:1,price:30,store:'Ferguson',bought:true,boughtAt:'2026-10-03T10:00:00Z',created:'2026-10-01'}];
DB.expenses=[{id:'e1',jobId:'j1',desc:'Pipe',amount:100,date:'2026-10-05',category:'Materials'}];
DB.budgets={};save();renderAll();})()"""
async def run(w, h):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8798/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h}'
        ok(await pg.evaluate("APP_VERSION==='4.49'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.evaluate(SEED)
        await pg.evaluate("bpOpenShop('j1')"); await pg.wait_for_timeout(500)
        txt = await pg.evaluate("document.getElementById('bp-shop').innerText")
        ok(not await pg.evaluate("!!document.getElementById('bp-shop-strip')"), f'{t}: materials strip should be gone')
        ok('MATERIALS' not in txt.upper() and 'SET A MATERIALS BUDGET' not in txt.upper(), f'{t}: materials text still on screen {txt!r}')
        tot = await pg.evaluate("document.getElementById('bp-shop-totals').innerText")
        ok('BOUGHT' not in tot.upper(), f'{t}: Bought total still in footer {tot!r}')
        ok('STILL TO BUY' in tot.upper() and '$200.00' in tot and 'tax' in tot, f'{t}: still-to-buy lost {tot!r}')
        # sizes: slim but glove-friendly
        # the app zooms text+buttons (Text & Button Size), so measure in CSS px = rect / zoom
        z = float(await pg.evaluate("getComputedStyle(document.body).zoom") or 1)
        add = await pg.evaluate("(()=>{var r=document.getElementById('bp-shop-add').getBoundingClientRect();return [r.height,r.width]})()")
        ok(43.5 <= add[0] / z <= 52, f'{t}: add bar height {add[0] / z} css px')
        calc = await pg.evaluate("(()=>{var r=document.querySelector('#bp-shop-totals button').getBoundingClientRect();return [r.height,r.width]})()")
        ok(calc[0] / z >= 43.5 and calc[1] / z >= 43.5, f'{t}: calculator tap target {calc}')
        foot = await pg.evaluate("document.getElementById('bp-shop-add').parentElement.getBoundingClientRect().height")
        ok(foot / z <= 125, f'{t}: footer still too tall {foot / z} css px (was ~147)')
        # still works
        ok(await pg.evaluate("document.querySelectorAll('#bp-shop [data-shop-id]').length")==2, f'{t}: rows')
        await pg.evaluate("document.getElementById('bp-shop-add').click()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("!!document.getElementById('bp-sa-text')"), f'{t}: add item page opens')
        await pg.evaluate("document.getElementById('bp-shop-new').remove()")
        await pg.evaluate("document.querySelector('#bp-shop-totals button').click()"); await pg.wait_for_timeout(300)
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8798','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run(390, 844); await run(834, 1194)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
