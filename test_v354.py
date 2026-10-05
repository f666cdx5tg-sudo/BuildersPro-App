"""BuildersPro v3.54: Command Center catches up to the field app (Spaces wording, Shopping List easy add, one Punchlist Filter button).
Run from the repo root: python3 test_v354.py  (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
async def run(page_name, w, h, body):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8798/' + page_name); await pg.wait_for_timeout(2500)
        await body(pg, errs); await b.close()
async def desk(pg, errs):
    ok(await pg.evaluate("APP_VERSION==='3.55'"), 'desktop version is not 3.55')
    ok(await pg.evaluate("document.getElementById('app-version-display').textContent==='3.55'"), 'version label not showing 3.55')
    # wording
    t = await pg.evaluate("document.body.innerText")
    ok('New Space' in await pg.evaluate("document.getElementById('view-rooms').innerText"), 'Spaces view lacks + New Space')
    side = await pg.evaluate("[...document.querySelectorAll('.ni')].map(e=>e.innerText.trim())")
    ok('Spaces' in side and 'Areas' not in side, f'sidebar not renamed: {side}')
    # seed
    await pg.evaluate("""(()=>{DB.jobs=[{id:'j1',name:'Test Job',status:'Active'}];DB.rooms=[{id:'r1',jobId:'j1',name:'Kitchen',type:'Kitchen'},{id:'r2',jobId:'j1',name:'Bath',type:'Bathroom'}];
      DB.punchlist=[{id:'p1',jobId:'j1',roomId:'r1',text:'Fix sink',done:false,trade:'Plumbing'},{id:'p2',jobId:'j1',roomId:'r1',text:'Paint wall',done:true,trade:'Paint'},{id:'p3',jobId:'j1',roomId:'r2',text:'Caulk tub',done:false,trade:'Plumbing'}];
      populateJobSelects();showView('punchlist');})()"""); await pg.wait_for_timeout(500)
    sel = await pg.evaluate("(()=>{const s=document.getElementById('punch-job-filter');s.value='j1';s.dispatchEvent(new Event('change'));return s.value})()"); await pg.wait_for_timeout(400)
    ok(await pg.evaluate("!!document.getElementById('punch-filter-btn')"), 'Filter button missing')
    rows = lambda: pg.evaluate("document.getElementById('punchlist-table-wrap').innerText")
    r = await rows(); ok('Kitchen' in r and 'Bath' in r, 'unfiltered grid should show both spaces')
    await pg.evaluate("bpDeskFilterToggle()"); await pg.wait_for_timeout(200)
    pan = await pg.evaluate("document.getElementById('punch-filter-panel').innerText")
    ok('STATUS' in pan and 'Open' in pan and 'Complete' in pan and 'SPACE' in pan and 'Kitchen' in pan and 'SEARCH' in pan, f'panel missing choices: {pan!r}')
    await pg.evaluate("bpDeskFilterSet('space','r2')"); await pg.wait_for_timeout(200)
    r = await rows(); ok('Bath' in r and 'Kitchen' not in r, 'Space filter should leave only Bath')
    ok('(1)' in await pg.evaluate("document.getElementById('punch-filter-btn').innerText"), 'button should show a count')
    await pg.evaluate("bpDeskFilterClear()"); await pg.wait_for_timeout(200)
    await pg.evaluate("DB.punchlist.forEach(x=>{if(x.roomId==='r2')x.done=true});bpDeskFilterSet('show','open')"); await pg.wait_for_timeout(200)
    r = await rows(); ok('Kitchen' in r and 'Bath' not in r, 'Open filter should hide the finished Bath')
    await pg.evaluate("bpDeskFilterClear()"); await pg.wait_for_timeout(100)
    await pg.evaluate("bpOpenPunchArea('r1')"); await pg.wait_for_timeout(400)
    r = await rows(); ok('Fix sink' in r and 'Paint wall' in r, 'inside Kitchen should list both items')
    await pg.evaluate("bpDeskFilterSet('show','open')"); await pg.wait_for_timeout(200)
    r = await rows(); ok('Fix sink' in r and 'Paint wall' not in r, 'Open filter inside a space wrong')
    await pg.evaluate("bpDeskFilterSet('show','done')"); await pg.wait_for_timeout(200)
    r = await rows(); ok('Paint wall' in r and 'Fix sink' not in r, 'Complete filter inside a space wrong')
    await pg.evaluate("bpDeskFilterSet('show','all');bpDeskFilterSet('q','paint')"); await pg.wait_for_timeout(200)
    r = await rows(); ok('Paint wall' in r and 'Fix sink' not in r, 'Search inside a space wrong')
    await pg.evaluate("bpDeskFilterClear();bpClosePunchArea()"); await pg.wait_for_timeout(200)
    # shopping easy add
    await pg.evaluate("bpOpenShop()"); await pg.wait_for_timeout(500)
    ok(await pg.evaluate("!!document.getElementById('bp-shop')"), 'shopping list did not open')
    ok(await pg.evaluate("!document.getElementById('bp-shop-text')"), 'old inline add form is still there')
    await pg.evaluate("document.getElementById('bp-shop-add').click()"); await pg.wait_for_timeout(400)
    ok(await pg.evaluate("!!document.getElementById('bp-sa-text')"), 'Add item dialog did not open')
    await pg.fill('#bp-sa-qty', '10'); await pg.fill('#bp-sa-text', 'PEX elbow'); await pg.fill('#bp-sa-price', '2.5')
    await pg.evaluate("bpShopSaveNew(false)"); await pg.wait_for_timeout(400)
    ok(await pg.evaluate("(DB.shopping||[]).some(x=>x.text==='PEX elbow'&&x.qty===10&&x.price===2.5)"), 'item not saved with qty/price')
    ok(await pg.evaluate("!document.getElementById('bp-shop-new')"), 'dialog should close after Add item')
    ok('PEX elbow' in await pg.evaluate("document.getElementById('bp-shop').innerText"), 'item not in list')
    await pg.evaluate("bpShopOpenAdd()"); await pg.fill('#bp-sa-text', 'Tape'); await pg.evaluate("bpShopSaveNew(true)"); await pg.wait_for_timeout(500)
    ok(await pg.evaluate("!!document.getElementById('bp-sa-text')"), 'Add + next should reopen the dialog')
    ok(len(errs) == 0, f'console errors: {errs[:3]}')
async def field(pg, errs):
    ok(await pg.evaluate("APP_VERSION==='3.55'"), 'field version is not 3.55')
    ok(len(errs) == 0, f'field console errors: {errs[:3]}')
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', '8798', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        await run('desktop.html', 1440, 900, desk)
        await run('index.html', 390, 844, field)
    finally: srv.terminate()
    print(f'{checks - len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
