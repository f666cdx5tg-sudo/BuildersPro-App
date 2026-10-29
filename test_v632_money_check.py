"""v6.3.2 — Money check: tap Money Left to see every line behind it, with doubles marked red.
Run from repo root: python3 test_v632_money_check.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8932
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { var t = new Date().toISOString();
  DB.jobs=[{id:'j1',name:'N. Peach St',status:'Active',contract:20000,updatedAt:t},{id:'j2',name:'Other',status:'Active',contract:5000,updatedAt:t}];
  DB.changeOrders=[]; 
  DB.contractors=[{id:'c1',jobId:'j1',name:'Mike Rivera',company:'Rivera Electric',value:6000,updatedAt:t}];
  DB.payments=[{id:'pay1',contractorId:'c1',amount:2500,date:'2026-10-20'}];
  DB.invoices=[{id:'i1',jobId:'j1',amount:8000,status:'Paid'}];
  DB.expenses=[
    {id:'e1',jobId:'j1',desc:'Materials — Home Depot',vendor:'Home Depot',amount:412.37,date:'2026-10-21',category:'Materials'},
    {id:'e2',jobId:'j1',desc:'Materials — Home Depot',vendor:'Home Depot',amount:412.37,date:'2026-10-21',category:'Materials'},
    {id:'e3',jobId:'j1',desc:'Ferguson pickup',vendor:'Ferguson',amount:980.10,date:'2026-10-22',category:'Materials'},
    {id:'e4',jobId:'j1',desc:'Delivery',vendor:'Ferguson',amount:980.10,date:'2026-10-24',category:'Delivery'},
    {id:'e5',jobId:'j1',desc:'Draw 1 Rivera Electric',vendor:'',amount:2500,date:'2026-10-20',category:'Labor'},
    {id:'e6',jobId:'j1',desc:'Dumpster',vendor:'Waste Co',amount:650,date:'2026-10-10',category:'Equipment'},
    {id:'e7',jobId:'j2',desc:'Other job paint',vendor:'Sherwin',amount:412.37,date:'2026-10-21',category:'Materials'}];
  try{bpSave()}catch(e){try{saveDB()}catch(e2){}} try{bpSetActiveJob('j1',true)}catch(e){} }"""
async def run(b, desk):
    print('\n' + ('Command Center' if desk else 'iPhone'))
    ctx = await b.new_context(viewport={'width': 1440, 'height': 900} if desk else {'width': 402, 'height': 874}, is_mobile=not desk, has_touch=not desk)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, 'desktop.html' if desk else 'index.html')); await pg.wait_for_timeout(3000)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); window.bpICloudSync=undefined;")
    await pg.evaluate(SEED)
    ok(await pg.evaluate("APP_VERSION") == '6.3.2', 'on v6.3.2')
    d = await pg.evaluate("(function(){ var d = bpMoneyCheckData('j1'); return { left: d.left, tile: d.left, exp: d.expTotal, sub: d.subTotal, flags: d.flags, n: d.flaggedCount }; })()")
    ok(abs(d['left'] - d['tile']) < 0.005, 'Money check adds up to the same Money Left as the tile (%s)' % d['left'])
    ok(abs(d['left'] - (20000 - (412.37*2 + 980.10*2 + 2500 + 650) - 6000)) < 0.005, 'math: contract − expenses − sub full value')
    f = d['flags']
    ok('e1' in f and 'e2' in f and 'Exact copy' in f['e1'][0], 'an exact copy (sync / restore) is marked on both lines')
    ok('e3' in f and 'e4' in f and 'vendor' in f['e3'][0], 'same amount, same vendor within 3 days is marked')
    ok('e5' in f and 'Rivera' in ' '.join(f['e5']), 'a sub payment logged as an expense is marked (sub already counted in full)')
    ok('e6' not in f, 'a normal expense is not marked')
    ok(d['n'] == 5, '5 lines flagged (%d)' % d['n'])
    if desk:
        await pg.evaluate("bpMoneyCheck('j1')")
    else:
        await pg.evaluate("showScreen('s-home')"); await pg.wait_for_timeout(800)
        tile = await pg.inner_text('#bp-onsite-card [data-onsite="money"] .bp-kpi-num')
        ok(tile.replace('-', '−').replace(',', '') == ('−$%.2f' % abs(d['left'])).replace(',', '') if d['left'] < 0 else True, 'the Home tile shows the same number (%s)' % tile)
        await pg.click('#bp-onsite-card [data-onsite="money"]')
    await pg.wait_for_timeout(400)
    txt = await pg.inner_text('#bp-mcheck') if await pg.evaluate("!!document.getElementById('bp-mcheck')") else ''
    ok('Money check' in txt and 'may be counted twice' in txt, 'tapping Money Left opens the Money check with the doubles warning')
    ok('Mike Rivera' in txt and 'Paid so far $2,500.00' in txt, 'subs show full value and what has been paid')
    ok('not subtracted' in txt and 'Other job paint' not in txt, 'only this job; says invoices are not subtracted')
    ok(await pg.evaluate("document.querySelectorAll('#bp-mcheck svg path[d^=\"M5 21V4\"]').length") >= 5, 'red flag line icons on the doubles')
    await pg.evaluate("window.__ed=''; window.openEditExpense=function(id){ window.__ed=id; }; try{ editExpense=function(id){ window.__ed=id; } }catch(e){}")
    await pg.click('#bp-mcheck [onclick*="e2"]'); await pg.wait_for_timeout(200)
    ok(await pg.evaluate("window.__ed") == 'e2' and not await pg.evaluate("!!document.getElementById('bp-mcheck')"), 'tapping a line opens that expense to fix it')
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await run(b, False); await run(b, True); await b.close()
    finally: srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails))); sys.exit(1 if fails else 0)
asyncio.run(main())
