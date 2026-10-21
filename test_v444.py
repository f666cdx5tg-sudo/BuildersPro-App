"""BuildersPro v4.44 (colour logic: yellow = waiting/pending on Ordered items, purple = change orders).
Run from repo root: python3 test_v444.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs=[{id:'j1',name:'Smith Kitchen',status:'Active'}];
DB.shopping=[{id:'s1',jobId:'j1',text:'PEX',qty:4,price:50,status:'ordered',bought:false,created:'2026-10-01'},
{id:'s2',jobId:'j1',text:'Elbows',qty:10,price:2,bought:false,created:'2026-10-02'}];
DB.expenses=[];DB.budgets={};save();renderAll();})()"""
def rgb(c): return [int(float(x)) for x in c[c.index('(')+1:c.index(')')].replace('/',',').replace(' ',',').split(',') if x.strip()][:3]
async def run(w, h, theme):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8797/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h} {theme}'
        ok(await pg.evaluate("APP_VERSION==='4.44'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("document.documentElement.setAttribute('data-theme','%s')" % theme)
        await pg.evaluate(SEED); await pg.evaluate("bpOpenShop('j1')"); await pg.wait_for_timeout(500)
        pill = await pg.evaluate("(()=>{var e=document.querySelector('#bp-shop [data-shop-id=\"s1\"] [data-shop-status]');var c=getComputedStyle(e);return [c.color,c.backgroundColor,e.innerText]})()")
        r, g, bl = rgb(pill[0])
        ok(r > 100 and g > 80 and bl < 60, f'{t}: Ordered pill not yellow {pill}')
        ok('Ordered' in pill[2], f'{t}: pill text {pill[2]}')
        need = await pg.evaluate("getComputedStyle(document.querySelector('#bp-shop [data-shop-id=\"s2\"] [data-shop-status]')).color")
        ok(not (rgb(need)[0] > 200 and rgb(need)[2] < 60), f'{t}: Need pill should stay grey {need}')
        lbl = await pg.evaluate("getComputedStyle(document.getElementById('bp-shop-ordered')).color")
        ok(rgb(lbl)[2] < 60, f'{t}: Ordered label not yellow {lbl}')
        # tap still toggles
        await pg.evaluate("document.querySelector('#bp-shop [data-shop-id=\"s1\"] [data-shop-status]').click()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("DB.shopping.find(x=>x.id==='s1').status")=='need', f'{t}: undo ordered')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8797','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        for th in ('dark','light'):
            await run(390, 844, th); await run(834, 1194, th)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
