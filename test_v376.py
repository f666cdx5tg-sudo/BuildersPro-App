"""BuildersPro v3.76: a selected job is isolated — no alerts/tiles from other jobs.
Run from repo root: python3 test_v376.py (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs=[{id:'j1',name:'Shedwick',status:'Active',contract:500},{id:'j2',name:'N. Peach St',status:'Active',contract:1000}];
DB.expenses=[{id:'e2',jobId:'j2',desc:'Pipe',amount:5137,date:'2026-10-05',category:'Materials'}];
DB.invoices=[{id:'i2',jobId:'j2',amount:900,status:'Overdue',date:'2026-08-01',desc:'Peach'}];
DB.permits=[{id:'p2',jobId:'j2',trade:'Plumbing',expirationDate:'2026-01-01'}];
DB.punchlist=[{id:'pl2',jobId:'j2',text:'x',done:false}];
DB.changeOrders=[{id:'c2',jobId:'j2',amount:300,status:'Draft'}];
save();renderAll();})()"""
async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await (await b.new_context(viewport={'width':390,'height':844})).new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8799/index.html'); await pg.wait_for_timeout(2500)
        ok(await pg.evaluate("APP_VERSION==='3.76'"), 'version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()"); await pg.evaluate(SEED)
        # no job selected -> portfolio view still warns about Peach
        await pg.evaluate("localStorage.removeItem('bp_active_job')")
        n_all = await pg.evaluate("bpAttentionItems().map(i=>i.text).join('|')")
        ok('Peach' in n_all or 'permit' in n_all or 'invoice' in n_all.lower(), f'portfolio view should show alerts: {n_all!r}')
        # select Shedwick -> nothing from Peach
        await pg.evaluate("bpSetActiveJob('j1')"); await pg.wait_for_timeout(300)
        items = await pg.evaluate("bpAttentionItems().map(i=>i.text)")
        ok(not any('Peach' in t or 'permit' in t or 'nvoice' in t for t in items), f'Shedwick leaked other-job alerts: {items}')
        tiles = await pg.evaluate("(()=>{var d=document.createElement('div');d.innerHTML=bpHomeTilesHtml();return d.innerText})()")
        ok('900' not in tiles and '300' not in tiles, f'tiles leaked: {tiles!r}')
        ok(await pg.evaluate("permitAlertCounts('j1').expired===0 && permitAlertCounts('j2').expired===1"), 'permitAlertCounts scope')
        # select Peach -> its own over-budget shows
        await pg.evaluate("bpSetActiveJob('j2')"); await pg.wait_for_timeout(300)
        items2 = await pg.evaluate("bpAttentionItems().map(i=>i.text)")
        ok(any('over budget' in t for t in items2), f'own job alert missing: {items2}')
        ok(not errs, f'page errors: {errs}')
        await b.close()
srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8799', '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
try: asyncio.run(run())
finally: srv.terminate()
print(f'{checks} checks, {len(fails)} failed'); sys.exit(1 if fails else 0)
