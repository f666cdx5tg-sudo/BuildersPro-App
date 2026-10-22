"""BuildersPro v4.40 (Add item: 1 Item, 2 Qty, 3 Units picker, 4 Price — plain underlined lines, no boxed cells).
Run from repo root: python3 test_v440.py (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = "(()=>{DB.jobs=[{id:'j1',name:'N. Peach St',status:'Active'}];DB.shopping=[];DB.expenses=[];DB.budgets={};save();renderAll();})()"
async def add(pg, item='', qty='', unit='', price='', nxt=False):
    await pg.evaluate("bpShopOpenAdd()"); await pg.wait_for_timeout(250)
    if item: await pg.fill('#bp-sa-text', item)
    if qty: await pg.fill('#bp-sa-qty', qty)
    if unit: await pg.select_option('#bp-sa-unit', unit)
    if price: await pg.fill('#bp-sa-price', price)
    await pg.evaluate("bpShopSaveNew(%s)" % ('true' if nxt else 'false')); await pg.wait_for_timeout(300)
async def run(w, h):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8794/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h}'
        ok(await pg.evaluate("APP_VERSION==='4.51'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.evaluate(SEED)
        await pg.evaluate("bpOpenShop('j1')"); await pg.wait_for_timeout(500)
        await pg.evaluate("bpShopOpenAdd()"); await pg.wait_for_timeout(300)
        # order + labels
        order = await pg.evaluate("[...document.querySelectorAll('#bp-shop-new input, #bp-shop-new select')].map(e=>e.id)")
        ok(order==['bp-sa-text','bp-sa-qty','bp-sa-unit','bp-sa-price'], f'{t}: field order {order}')
        sheet = (await pg.evaluate("document.getElementById('bp-shop-new').innerText")).upper()
        pos = [sheet.find(x) for x in ['1 · ITEM','2 · QTY','3 · UNITS','4 · PRICE']]
        ok(all(i>=0 for i in pos) and pos==sorted(pos), f'{t}: section labels/order {pos}')
        ok(await pg.evaluate("document.getElementById('bp-sa-unit').tagName")=='SELECT', f'{t}: units not a picker')
        # no boxed cells: every field is transparent with an underline only
        flat = await pg.evaluate("[...document.querySelectorAll('#bp-shop-new input, #bp-shop-new select')].every(e=>{var c=getComputedStyle(e);return c.backgroundColor==='rgba(0, 0, 0, 0)'&&c.borderTopWidth==='0px'&&parseFloat(c.borderBottomWidth)>0})")
        ok(flat, f'{t}: fields should be plain underlined lines, not cells')
        z = float(await pg.evaluate("getComputedStyle(document.body).zoom") or 1)
        hs = await pg.evaluate("[...document.querySelectorAll('#bp-shop-new input, #bp-shop-new select')].map(e=>e.getBoundingClientRect().height)")
        ok(all(x/z>=43.5 for x in hs), f'{t}: tap targets {[x/z for x in hs]}')
        ok(await pg.evaluate("document.getElementById('bp-sa-text').getAttribute('placeholder')")!='' , f'{t}: placeholder')
        await pg.evaluate("document.getElementById('bp-shop-new').remove()")
        # saving
        await add(pg, '1/2" PEX elbow', '10', 'box', '2.5')
        ok(await pg.evaluate("DB.shopping.some(x=>x.text==='1/2\" PEX elbow'&&x.qty===10&&x.unit==='box'&&x.price===2.5&&x.jobId==='j1')"), f'{t}: full add')
        await add(pg, 'mail boxes')
        ok(await pg.evaluate("DB.shopping.some(x=>x.text==='Mail boxes'&&x.qty===1&&x.unit===''&&x.price===0)"), f'{t}: item only -> qty 1, no unit, no price')
        await add(pg, '2 x 4 stud', '8', 'ea')
        ok(await pg.evaluate("DB.shopping.some(x=>x.text==='2 x 4 stud'&&x.qty===8&&x.unit==='ea')"), f'{t}: name starting with a number is kept literally')
        await add(pg, 'Solder', '', 'roll', '18')
        ok(await pg.evaluate("DB.shopping.some(x=>x.text==='Solder'&&x.qty===1&&x.unit==='roll'&&x.price===18)"), f'{t}: no qty -> 1')
        ok(await pg.evaluate("!document.getElementById('bp-shop-new')"), f'{t}: sheet closes after Add item')
        # validation
        n = await pg.evaluate("DB.shopping.length"); await add(pg, '   ', '3')
        ok(await pg.evaluate("DB.shopping.length")==n and await pg.evaluate("!!document.getElementById('bp-shop-new')"), f'{t}: empty item must not save')
        await pg.fill('#bp-sa-text', 'Bad'); await pg.fill('#bp-sa-qty', 'abc'); await pg.evaluate("bpShopSaveNew(false)"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("DB.shopping.length")==n and await pg.evaluate("!!document.getElementById('bp-shop-new')"), f'{t}: bad number must not save')
        await pg.evaluate("document.getElementById('bp-shop-new').remove()")
        # Enter: item -> qty -> price -> save
        await pg.evaluate("bpShopOpenAdd()"); await pg.wait_for_timeout(250)
        await pg.fill('#bp-sa-text', 'P-trap'); await pg.press('#bp-sa-text', 'Enter')
        ok(await pg.evaluate("document.activeElement.id")=='bp-sa-qty', f'{t}: Enter on item should go to Qty')
        await pg.fill('#bp-sa-qty', '2'); await pg.press('#bp-sa-qty', 'Enter')
        ok(await pg.evaluate("document.activeElement.id")=='bp-sa-price', f'{t}: Enter on qty should go to Price')
        await pg.fill('#bp-sa-price', '7'); await pg.press('#bp-sa-price', 'Enter'); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("DB.shopping.some(x=>x.text==='P-trap'&&x.qty===2&&x.price===7)"), f'{t}: Enter on price saves')
        # Add + next reopens clean
        await add(pg, 'Tape', '1', 'roll', '3', nxt=True)
        ok(await pg.evaluate("['text','qty','unit','price'].every(k=>document.getElementById('bp-sa-'+k).value==='')"), f'{t}: Add + next reopens clean')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await pg.evaluate("bpShopOpenAdd()"); await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.environ.get('SHOT_DIR','/tmp') + f'/add_{w}.png')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8794','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run(390, 844); await run(834, 1194)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
