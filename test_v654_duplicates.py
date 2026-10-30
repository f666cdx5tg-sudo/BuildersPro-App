"""v6.5.4 — Find duplicates (every job, no AI needed).
Seeds a job with: an expense entered 3 times, a same-day look-alike, a payment entered twice, an invoice twice,
a punch item twice (one done), a photo twice, and the whole job made twice (one empty copy, one with a record).
Checks: exact copies ticked, look-alike unticked, job copy with records can't be ticked, Remove sends them to the
Recycle Bin and totals drop; menu entry on phone and Mac. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8954
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => { var t = '2026-10-01T10:00:00Z', d = '2026-10-01';
  DB.jobs = [{id:'j1',name:'N. Peach St',address:'1536 N. Peach St',contract:49000,status:'Active',createdAt:'2026-09-01'},
             {id:'j2',name:'N. Peach St',address:'1536 N. Peach St',status:'Active',createdAt:'2026-09-05'},
             {id:'j3',name:'n. peach st',address:'1536 N. Peach St',status:'Active',createdAt:'2026-09-06'},
             {id:'j4',name:'Other',address:'2 St',status:'Active'}];
  DB.expenses = [
    {id:'e1',jobId:'j1',desc:'Pipe',vendor:'Home Depot',amount:412.37,date:d,category:'Materials',createdAt:'2026-10-01T10:00'},
    {id:'e2',jobId:'j1',desc:'Pipe',vendor:'Home Depot',amount:412.37,date:d,category:'Materials',createdAt:'2026-10-01T11:00'},
    {id:'e3',jobId:'j1',desc:'pipe ',vendor:'home depot',amount:412.37,date:d,category:'Materials',createdAt:'2026-10-01T12:00'},
    {id:'e4',jobId:'j1',desc:'Fittings',vendor:'Ferguson',amount:88,date:'2026-10-02',category:'Materials'},
    {id:'e5',jobId:'j1',desc:'Fittings run 2',vendor:'Ferguson',amount:88,date:'2026-10-02',category:'Materials'},
    {id:'e6',jobId:'j4',desc:'Pipe',vendor:'Home Depot',amount:412.37,date:d,category:'Materials'}];
  DB.contractors = [{id:'c1',jobId:'j1',name:'Mike',value:6000}];
  DB.payments = [{id:'p1',contractorId:'c1',amount:2500,date:d},{id:'p2',contractorId:'c1',amount:2500,date:d}];
  DB.invoices = [{id:'i1',jobId:'j1',number:'INV-1',amount:10000,date:d},{id:'i2',jobId:'j1',number:'INV-1',amount:10000,date:d}];
  DB.changeOrders = [];
  DB.punchlist = [{id:'k1',jobId:'j1',roomId:'r1',text:'Set flange',trade:'Plumbing',done:false,created:'2026-09-02'},{id:'k2',jobId:'j1',roomId:'r1',text:'Set flange',trade:'Plumbing',done:true,created:'2026-09-03'}];
  DB.photos = [{id:'f1',jobId:'j1',src:'data:image/png;base64,AAAA',date:d},{id:'f2',jobId:'j1',src:'data:image/png;base64,AAAA',date:d}];
  DB.rooms = [{id:'r1',jobId:'j1',name:'Bath'},{id:'r9',jobId:'j3',name:'Kitchen'}];
  try { bpSave(); } catch(e){ try { saveDB(); } catch(e2){} }
}"""
async def run(b, file, w, h, mobile):
    ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=mobile, has_touch=mobile)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
    await pg.evaluate(SEED)
    menu = '#nav-dups' if mobile else '#ni-dups'
    ok(await pg.evaluate("!!document.querySelector('%s')" % menu), 'Find duplicates is in the side menu')
    await pg.evaluate("document.querySelector('%s').click()" % menu); await pg.wait_for_timeout(400)
    ok(await pg.evaluate("!!document.getElementById('bp-dups')"), 'the sheet opens')
    ticked = await pg.evaluate("[].map.call(document.querySelectorAll('#bp-dups input[data-dup]:checked'), function(i){ return i.getAttribute('data-dup'); }).sort()")
    want = sorted(['expenses|e2','expenses|e3','payments|p2','invoices|i2','punchlist|k1','photos|f2','jobs|j2'])
    ok(ticked == want, 'exact copies ticked, oldest kept, done punch kept, empty job copy ticked %s' % ticked)
    ok(await pg.evaluate("!document.querySelector('#bp-dups input[data-dup=\"expenses|e5\"]:checked') && !!document.querySelector('#bp-dups input[data-dup=\"expenses|e5\"]')"), 'same-day look-alike listed but NOT ticked')
    ok(await pg.evaluate("document.querySelector('#bp-dups input[data-dup=\"jobs|j3\"]').disabled"), 'a job copy with records in it cannot be removed here')
    ok(not await pg.evaluate("!!document.querySelector('#bp-dups input[data-dup=\"expenses|e6\"]')"), 'same expense on a different job is not a duplicate')
    ok('7' in await pg.inner_text('#bp-dup-go'), 'button says Remove 7 ticked')
    await pg.click('#bp-dup-go'); await pg.wait_for_timeout(400)
    left = await pg.evaluate("({e: DB.expenses.map(function(x){return x.id}).sort(), p: DB.payments.length, i: DB.invoices.length, k: DB.punchlist.map(function(x){return x.id}), f: DB.photos.length, j: DB.jobs.map(function(x){return x.id}).sort()})")
    ok(left['e'] == ['e1','e4','e5','e6'] and left['p'] == 1 and left['i'] == 1 and left['k'] == ['k2'] and left['f'] == 1 and left['j'] == ['j1','j3','j4'], 'removed exactly the ticked ones %s' % left)
    ok(await pg.evaluate("(DB.recycleBin || DB._recycle || DB.recycle || []).length >= 7 || JSON.stringify(localStorage).indexOf('e3') >= 0"), 'removed records are in the Recycle Bin')
    ok(not await pg.evaluate("!!document.getElementById('bp-dups')"), 'sheet closes')
    await pg.evaluate("bpFindDuplicates()"); await pg.wait_for_timeout(300)
    ok(await pg.evaluate("document.querySelectorAll('#bp-dups input[data-dup]:checked').length") == 0, 'second scan: nothing exact left')
    ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            print('\niPhone'); await run(b, 'index.html', 402, 874, True)
            print('\nMac'); await run(b, 'desktop.html', 1440, 900, False)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
