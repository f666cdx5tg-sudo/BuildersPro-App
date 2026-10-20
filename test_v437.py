"""BuildersPro v4.37 (Add item sheet: one plain line instead of Qty / Item / Cost cells).
Run from repo root: python3 test_v437.py (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = "(()=>{DB.jobs=[{id:'j1',name:'Smith Kitchen',status:'Active'}];DB.shopping=[];DB.expenses=[];DB.budgets={};save();renderAll();})()"
async def add(pg, txt, nxt=False):
    await pg.evaluate("bpShopOpenAdd()"); await pg.wait_for_timeout(250)
    await pg.fill('#bp-sa-text', txt)
    await pg.evaluate("bpShopSaveNew(%s)" % ('true' if nxt else 'false')); await pg.wait_for_timeout(300)
async def run(w, h):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8797/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h}'
        ok(await pg.evaluate("APP_VERSION==='4.39'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.evaluate(SEED)
        await pg.evaluate("bpOpenShop('j1')"); await pg.wait_for_timeout(500)
        await pg.evaluate("bpShopOpenAdd()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("document.querySelectorAll('#bp-shop-new input').length")==1, f'{t}: should be exactly one input, no cells')
        ok(not await pg.evaluate("!!document.getElementById('bp-sa-qty')||!!document.getElementById('bp-sa-price')"), f'{t}: qty/cost cells still present')
        ok(await pg.evaluate("getComputedStyle(document.getElementById('bp-sa-text')).backgroundColor")=='rgba(0, 0, 0, 0)', f'{t}: field should not be a filled cell')
        z = float(await pg.evaluate("getComputedStyle(document.body).zoom") or 1)
        hh = await pg.evaluate("document.getElementById('bp-sa-text').getBoundingClientRect().height")
        ok(hh / z >= 43.5, f'{t}: tap target {hh / z}')
        await pg.evaluate("document.getElementById('bp-shop-new').remove()")
        await add(pg, '10 1/2" PEX elbows @2')
        await add(pg, 'PEX elbow')
        await add(pg, '4 shutoff valves @2.50')
        await add(pg, 'three 3/4 inch copper tees at 3')
        got = await pg.evaluate("DB.shopping.map(x=>[x.text,x.qty,x.price])")
        ok(['1/2" PEX elbows',10,2] in got, f'{t}: parse 1 {got}')
        ok(['PEX elbow',1,0] in got, f'{t}: parse 2 {got}')
        ok(['Shutoff valves',4,2.5] in got, f'{t}: parse 3 {got}')
        ok(['3/4" copper tees',3,3] in got, f'{t}: parse 4 {got}')
        ok(await pg.evaluate("!document.getElementById('bp-shop-new')"), f'{t}: sheet closes after Add item')
        # empty does not save
        n = await pg.evaluate("DB.shopping.length"); await add(pg, '   ')
        ok(await pg.evaluate("DB.shopping.length")==n and await pg.evaluate("!!document.getElementById('bp-shop-new')"), f'{t}: empty should not save')
        await pg.evaluate("document.getElementById('bp-shop-new').remove()")
        # Enter key saves
        await pg.evaluate("bpShopOpenAdd()"); await pg.wait_for_timeout(250); await pg.fill('#bp-sa-text', '2 P-traps @7'); await pg.press('#bp-sa-text', 'Enter'); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("DB.shopping.some(x=>x.qty===2&&x.price===7)"), f'{t}: Enter did not save')
        # Add + next reopens
        await add(pg, 'Tape', True)
        ok(await pg.evaluate("!!document.getElementById('bp-sa-text')&&document.getElementById('bp-sa-text').value===''"), f'{t}: Add + next should reopen empty')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8797','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run(390, 844); await run(834, 1194)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
