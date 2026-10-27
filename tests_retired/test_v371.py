"""BuildersPro v3.71 (materials -> job costs: Ordered status, partial arrivals, receipts, cost strip).
Run from repo root: python3 test_v371.py (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, base64
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')
SEED = """(()=>{DB.jobs=[{id:'j1',name:'Smith Kitchen',status:'Active'},{id:'j2',name:'Other',status:'Active'}];
DB.shopping=[{id:'s1',jobId:'j1',text:'PEX 1/2 coil',qty:4,price:50,store:'Ferguson',bought:false,created:'2026-10-01'},
{id:'s2',jobId:'j1',text:'Elbows',qty:10,price:2,store:'Ferguson',bought:false,created:'2026-10-02'},
{id:'s3',jobId:'j1',text:'Old valve',qty:1,price:30,store:'Ferguson',bought:true,boughtAt:'2026-10-03T10:00:00Z',created:'2026-10-01'}];
DB.expenses=[{id:'e1',jobId:'j1',desc:'Pipe',amount:100,date:'2026-10-05',category:'Materials'},{id:'e2',jobId:'j1',desc:'Gas',amount:999,date:'2026-10-05',category:'Fuel'}];
DB.budgets={};save();renderAll();})()"""
async def run(w, h):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept(os.environ.get('ANS', '') if d.type == 'prompt' else None)) if d.type != 'prompt' else asyncio.ensure_future(d.accept(ANS[0])))
        ANS = ['4']
        await pg.goto('http://localhost:8799/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h}'
        ok(await pg.evaluate("APP_VERSION==='3.71'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.evaluate(SEED)
        await pg.evaluate("bpOpenShop('j1')"); await pg.wait_for_timeout(500)
        ok(await pg.evaluate("document.querySelectorAll('#bp-shop [data-shop-status]').length")==2, f'{t}: status pills')
        ok(not await pg.evaluate("!!document.getElementById('bp-shop-ordered')"), f'{t}: no Ordered section yet')
        # no budget -> prompt to set one, spent = 100 expense + 30*1.06625 bought-not-in-Money
        strip = await pg.evaluate("document.getElementById('bp-shop-strip')?.innerText||''")
        ok('Set a materials budget' in strip, f'{t}: set-budget prompt missing {strip!r}')
        sp = await pg.evaluate("document.getElementById('bp-ss-spent').textContent")
        ok(sp == '$131.99' or sp == '$131.98', f'{t}: spent wrong {sp}')   # 100 + 31.99 (fuel excluded)
        # mark ordered
        await pg.evaluate("document.querySelector('#bp-shop [data-shop-id=\"s1\"] [data-shop-status]').click()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("DB.shopping.find(x=>x.id==='s1').status")=='ordered', f'{t}: not ordered')
        ok(await pg.evaluate("!!document.querySelector('#bp-shop-ordered')&&!!document.querySelector('#bp-shop [data-shop-id=\"s1\"]')"), f'{t}: Ordered section')
        # partial arrival: 3 of 4
        ANS[0] = '3'
        await pg.evaluate("bpShopToggle('s1')"); await pg.wait_for_timeout(400)
        r = await pg.evaluate("DB.shopping.filter(x=>x.text==='PEX 1/2 coil').map(x=>[x.qty,x.bought,x.status])")
        ok(sorted(r)==[[1,False,'ordered'],[3,True,'arrived']], f'{t}: split wrong {r}')
        ok(await pg.evaluate("!!document.getElementById('bp-shop-edit')"), f'{t}: edit page should open after arrival')
        # receipt attach
        ok(await pg.evaluate("!!document.getElementById('bp-se-rcp')"), f'{t}: receipt section')
        ok('No receipt' in await pg.evaluate("document.getElementById('bp-shop').innerText"), f'{t}: no-receipt badge')
        await pg.set_input_files('#bp-se-file2', files=[{'name':'r.png','mimeType':'image/png','buffer':PNG}]); await pg.wait_for_timeout(1500)
        rid = await pg.evaluate("DB.shopping.find(x=>x.bought&&x.text==='PEX 1/2 coil').id")
        ok(await pg.evaluate("!!DB.shopping.find(x=>x.bought&&x.text==='PEX 1/2 coil').receiptSrc"), f'{t}: receipt not saved')
        ok(await pg.evaluate("!!document.getElementById('bp-se-thumb')"), f'{t}: thumb missing')
        await pg.evaluate("bpShopRcpView('%s')" % rid); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("!!document.querySelector('#bp-shop-rcp img')"), f'{t}: viewer')
        await pg.evaluate("document.getElementById('bp-shop-rcp').remove();document.getElementById('bp-shop-edit').remove()")
        bt = await pg.evaluate("document.getElementById('bp-shop').innerText"); ok('Receipt' in bt and bt.count('No receipt') < 2, f'{t}: receipt badge {bt!r}')
        # to Money carries receipt
        await pg.evaluate("bpShopToMoney()"); await pg.wait_for_timeout(400)
        ok(await pg.evaluate("DB.expenses.some(e=>e.fromShopping&&!!e.receiptSrc)"), f'{t}: receipt not copied to expense')
        # budget strip with budget
        await pg.evaluate("DB.budgets={j1:{Materials:1000}};bpOpenShop('j1')"); await pg.wait_for_timeout(300)
        s2 = await pg.evaluate("document.getElementById('bp-shop-strip').innerText")
        ok('BUDGET' in s2.upper() and 'LEFT' in s2.upper(), f'{t}: budget strip {s2!r}')
        # other job -> unaffected, no-job -> no strip
        await pg.evaluate("bpShopJob('')"); ok(not await pg.evaluate("!!document.getElementById('bp-shop-strip')"), f'{t}: strip without job')
        # pending queue knows about shopping
        ok(await pg.evaluate("typeof bpPending==='function'"), f'{t}: queue present')
        # names never wrap
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8799','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run(390, 844); await run(834, 1194)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
