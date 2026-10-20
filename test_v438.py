"""BuildersPro v4.38 (Edit item: no calculators, Unit dropdown (Add item sheet is covered by test_v440.py)).
Run from repo root: python3 test_v438.py (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs=[{id:'j1',name:'N. Peach St',status:'Active'}];
DB.shopping=[{id:'s1',jobId:'j1',text:'Mail boxes',qty:2,price:0,unit:'',store:'LOWES',bought:false,created:'2026-10-01'},
{id:'s2',jobId:'j1',text:'Odd thing',qty:1,price:5,unit:'lengths',store:'',bought:false,created:'2026-10-02'}];
DB.expenses=[];DB.budgets={};save();renderAll();})()"""
async def run(w, h):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8796/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h}'
        ok(await pg.evaluate("APP_VERSION==='4.40'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.evaluate(SEED)
        await pg.evaluate("bpOpenShop('j1')"); await pg.wait_for_timeout(500)

        # ---- Edit item ----
        await pg.evaluate("bpShopEdit('s1')"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("document.querySelectorAll('#bp-shop-edit button[aria-label=\"Calculator\"], #bp-shop-edit [onclick*=\"bpOpenCalc\"]').length")==0, f'{t}: calculator buttons still on Edit item')
        ok(await pg.evaluate("document.getElementById('bp-se-unit').tagName")=='SELECT', f'{t}: unit is not a dropdown')
        opts = await pg.evaluate("[...document.getElementById('bp-se-unit').options].map(o=>o.value)")
        ok(all(u in opts for u in ['ea','ft','box','bag','sheet','gal','roll','pc']), f'{t}: unit list {opts}')
        ok(await pg.evaluate("!!document.getElementById('bp-se-qty')&&!!document.getElementById('bp-se-price')"), f'{t}: qty/price inputs')
        await pg.select_option('#bp-se-unit', 'box')
        await pg.fill('#bp-se-qty', '3'); await pg.fill('#bp-se-price', '12.5')
        await pg.evaluate("bpShopSaveEdit('s1')"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("(x=>x.unit==='box'&&x.qty===3&&x.price===12.5)(DB.shopping.find(x=>x.id==='s1'))"), f'{t}: edit save')
        # a custom/old unit already on an item stays selectable and survives a save
        await pg.evaluate("bpShopEdit('s2')"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("document.getElementById('bp-se-unit').value")=='lengths', f'{t}: existing custom unit lost')
        await pg.evaluate("bpShopSaveEdit('s2')"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("DB.shopping.find(x=>x.id==='s2').unit")=='lengths', f'{t}: custom unit not kept on save')
        # clear back to none
        await pg.evaluate("bpShopEdit('s1')"); await pg.wait_for_timeout(300)
        await pg.select_option('#bp-se-unit', '')
        await pg.evaluate("bpShopSaveEdit('s1')"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("DB.shopping.find(x=>x.id==='s1').unit")=='', f'{t}: unit not clearable')

        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8796','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run(390, 844); await run(834, 1194)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
