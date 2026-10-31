"""v6.9.7 — the 9 Zelle progress payments on N. Peach St ($14,532.39) move from Expenses to paid invoices.
Run from repo root: python3 test_v697_zelle_income.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8997
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """(extra) => { var t='2026-10-01T00:00:00.000Z';
  DB.jobs=[{id:'jP',name:'N. Peach St',status:'Active',value:45000,updatedAt:t},{id:'jS',name:'Shedwick',status:'Active',updatedAt:t}];
  var z=[['ZELLE 8/20/26',62.07],['ZELLE 8/24/26',261.28],['ZELLE 8/27/26',2059.04],['ZELLE 8/31/26',1500],['zelle',2900],['ZELLE',750],['ZELLE',3000],['ZELLE',3000],['ZELLE',1000]];
  DB.expenses=z.map(function(x,i){ return {id:'z'+i,jobId:'jP',desc:x[0],amount:x[1],date:'2026-09-20',category:'Materials',vendor:'STM',updatedAt:t}; });
  DB.expenses.push({id:'m1',jobId:'jP',desc:'LOWES PO # 29093',amount:3731.69,date:'2026-09-20',category:'Materials',vendor:'LOWES',updatedAt:t});
  if (extra) DB.expenses.push({id:'zx',jobId:'jP',desc:'ZELLE extra',amount:5,updatedAt:t});
  DB.invoices=[{id:'i1',jobId:'jP',desc:'Deposit',amount:5000,status:'Paid',date:'2026-08-15'}]; DB.migrations={}; bpSave(); }"""
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for file, w, h in (('index.html', 402, 874), ('desktop.html', 1440, 900)):
                print('\n' + file)
                pg = await b.new_page(viewport={'width': w, 'height': h}); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
                await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(2500)
                await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
                await pg.evaluate(SEED, True)
                r = await pg.evaluate("bpZelleToIncome()")
                ok(r['done'] == 0 and 'found 10' in r['why'], 'safety: a 10th Zelle entry → nothing changed (%s)' % r['why'])
                await pg.evaluate(SEED, False)
                r = await pg.evaluate("bpZelleToIncome()")
                ok(r['done'] == 9 and abs(r['amount'] - 14532.39) < 0.001, 'moved 9 payments, $14,532.39')
                s = await pg.evaluate("({exp: DB.expenses.map(function(e){return e.id}), paid: Math.round(DB.invoices.filter(function(i){return i.status==='Paid' && i.jobId==='jP'}).reduce(function(s,i){return s+i.amount},0)*100)/100, n: DB.invoices.length, bin: (DB.recycle||[]).filter(function(e){return e.coll==='expenses'}).length, d: (DB.invoices.find(function(i){return i.id==='inv-zelle-z0'})||{}).date})")
                ok(s['exp'] == ['m1'], 'only the real material purchase stays in Expenses %s' % s['exp'])
                ok(s['paid'] == 19532.39 and s['n'] == 10, 'collected = $5,000 deposit + $14,532.39 = $19,532.39')
                ok(s['bin'] == 9, 'the 9 expenses are in the Recycle Bin (can be put back)')
                ok(s['d'] == '2026-08-20', 'date taken from "ZELLE 8/20/26"')
                r = await pg.evaluate("bpZelleToIncome()")
                ok(r['done'] == 0 and r['why'] == 'already done', 'runs once')
                ok(not errs, 'no page errors %s' % errs[:2]); await pg.close()
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
