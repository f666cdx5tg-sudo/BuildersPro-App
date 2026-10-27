"""BuildersPro v4.53 (Phone book shortcut in the side menu).
Run from repo root: python3 test_v451.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs=[{id:'j1',name:'N. Peach St',status:'Active'}];
DB.contractors=[{id:'c1',name:'Joe Rossi',jobId:'j1',trade:'Plumbing',value:5000,status:'Active'}];
DB.contacts=[];DB.expenses=[];DB.invoices=[];DB.payments=[];save();renderAll();})()"""
async def run(w, h, theme):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8787/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h} {theme}'
        ok(await pg.evaluate("APP_VERSION==='4.53'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("document.documentElement.setAttribute('data-theme','%s')" % theme)
        await pg.evaluate(SEED)
        ok('Phone book' in await pg.evaluate("document.getElementById('nav-phonebook').textContent"), f'{t}: menu item')
        # from a different screen, with another Finance tab and a leftover search
        await pg.evaluate("showScreen('s-jobs');setFinanceTab('expenses')")
        await pg.evaluate("toggleNavDrawer()"); await pg.wait_for_timeout(400)
        await pg.evaluate("document.getElementById('nav-phonebook').click()"); await pg.wait_for_timeout(500)
        ok(await pg.evaluate("document.getElementById('s-finance').classList.contains('active')"), f'{t}: opens Finance')
        ok(await pg.evaluate("!!document.getElementById('bp-sb-list')"), f'{t}: lands on the merged list')
        ok('Joe Rossi' in await pg.evaluate("document.getElementById('bp-sb-list').innerText"), f'{t}: shows the sub')
        ok(not await pg.evaluate("document.getElementById('bp-drawer').classList.contains('open')"), f'{t}: menu closed')
        # + button adds a contractor from here
        await pg.evaluate("openFinanceAdd()"); await pg.wait_for_timeout(250)
        ok(await pg.evaluate("document.getElementById('sheet-add-contractor').classList.contains('open')||document.getElementById('sheet-add-contractor').classList.contains('active')||getComputedStyle(document.getElementById('sheet-add-contractor')).display!='none'"), f'{t}: + opens Add contractor')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8787','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        for th in ('dark','light'):
            await run(390, 844, th); await run(834, 1194, th)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
