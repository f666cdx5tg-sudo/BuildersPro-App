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
             {id:'j4',name:'Other',address:'2 St',status:'Active'},
             {id:'j5',name:'Shedwick',address:'9 Elm',contract:500,status:'Active',createdAt:'2026-09-01'},
             {id:'j6',name:'Shedwick',address:'9 Elm',contract:500,status:'Active',createdAt:'2026-09-02'},
             {id:'j7',name:'Kingdom Hall',address:'5 Oak',status:'Active',createdAt:'2026-09-01'},
             {id:'j8',name:'Kingdom Hall',address:'5 Oak',status:'Active',createdAt:'2026-09-02'}];
  DB.expenses = [
    {id:'e1',jobId:'j1',desc:'Pipe',vendor:'Home Depot',amount:412.37,date:d,category:'Materials',createdAt:'2026-10-01T10:00'},
    {id:'e2',jobId:'j1',desc:'Pipe',vendor:'Home Depot',amount:412.37,date:d,category:'Materials',createdAt:'2026-10-01T11:00'},
    {id:'e3',jobId:'j1',desc:'pipe ',vendor:'home depot',amount:412.37,date:d,category:'Materials',createdAt:'2026-10-01T12:00'},
    {id:'e4',jobId:'j1',desc:'Fittings',vendor:'Ferguson',amount:88,date:'2026-10-02',category:'Materials'},
    {id:'e5',jobId:'j1',desc:'Fittings run 2',vendor:'Ferguson',amount:88,date:'2026-10-02',category:'Materials'},
    {id:'e6',jobId:'j4',desc:'Pipe',vendor:'Home Depot',amount:412.37,date:d,category:'Materials'},
    {id:'e7',jobId:'j5',desc:'Wire',vendor:'HD',amount:50,date:d},{id:'e8',jobId:'j6',desc:'Wire',vendor:'HD',amount:50,date:d,createdAt:'x'}];
  DB.contractors = [{id:'c1',jobId:'j1',name:'Mike',value:6000},{id:'c2',jobId:'j1',name:'Mike',value:6000},{id:'c5',jobId:'j5',name:'Raheem',value:900},{id:'c6',jobId:'j6',name:'Raheem',value:900}];
  DB.appointments = [{id:'a1',jobId:'j1',title:'Inspection',date:d,time:'09:00'},{id:'a2',jobId:'j1',title:'Inspection',date:d,time:'09:00'}];
  DB.payments = [{id:'p1',contractorId:'c1',amount:2500,date:d},{id:'p2',contractorId:'c1',amount:2500,date:d}];
  DB.invoices = [{id:'i1',jobId:'j1',number:'INV-1',amount:10000,date:d},{id:'i2',jobId:'j1',number:'INV-1',amount:10000,date:d}];
  DB.changeOrders = [];
  DB.punchlist = [{id:'k1',jobId:'j1',roomId:'r1',text:'Set flange',trade:'Plumbing',done:false,created:'2026-09-02'},{id:'k2',jobId:'j1',roomId:'r1',text:'Set flange',trade:'Plumbing',done:true,created:'2026-09-03'}];
  DB.photos = [{id:'f1',jobId:'j1',src:'data:image/png;base64,AAAA',date:d},{id:'f2',jobId:'j1',src:'data:image/png;base64,AAAA',date:d}];
  DB.rooms = [{id:'r1',jobId:'j1',name:'Bath'},{id:'r9',jobId:'j3',name:'Kitchen'},
    {id:'r71',jobId:'j7',name:'Hall',level:'L1'},{id:'r72',jobId:'j7',name:'Office',level:'L1'},
    {id:'r81',jobId:'j8',name:'Hall',level:'L1'},{id:'r83',jobId:'j8',name:'Lobby',level:'L1'}];
  DB.punchlist.push({id:'k71',jobId:'j7',roomId:'r71',text:'Paint',trade:'Paint',done:true,status:'Done',caption:'x',updatedAt:'2026-10-20'},{id:'k72',jobId:'j7',roomId:'r72',text:'Door',trade:'Carp'},
    {id:'k81',jobId:'j8',roomId:'r81',text:'Paint',trade:'Paint'},{id:'k82',jobId:'j8',roomId:'r81',text:'Security cam',trade:'Elec'},{id:'k83',jobId:'j8',roomId:'r83',text:'Sign',trade:'Gen'});
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
    want = sorted(['expenses|e2','expenses|e3','payments|p2','invoices|i2','punchlist|k1','photos|f2','jobs|j2','contractors|c2','appointments|a2','jobs|j6','merge|j7','merge|j3'])
    ok(ticked == want, 'exact copies ticked, oldest kept, done punch kept, empty job copy ticked %s' % ticked)
    ok(await pg.evaluate("!document.querySelector('#bp-dups input[data-dup=\"expenses|e5\"]:checked') && !!document.querySelector('#bp-dups input[data-dup=\"expenses|e5\"]')"), 'same-day look-alike listed but NOT ticked')
    ok('moved into the kept job' in await pg.inner_text('#bp-dups'), 'a job copy with its own records is merged, not thrown away')
    ok(not await pg.evaluate("!!document.querySelector('#bp-dups input[data-dup=\"expenses|e6\"]')"), 'same expense on a different job is not a duplicate')
    ok('12' in await pg.inner_text('#bp-dup-go'), 'button says Remove 12 ticked')
    ok('full copy' in await pg.inner_text('#bp-dups'), 'a job copied with all its records is marked full copy')
    await pg.click('#bp-dup-go'); await pg.wait_for_timeout(400)
    left = await pg.evaluate("({e: DB.expenses.map(function(x){return x.id}).sort(), p: DB.payments.length, i: DB.invoices.length, k: DB.punchlist.filter(function(x){return x.jobId==='j1'}).map(function(x){return x.id}), f: DB.photos.length, j: DB.jobs.map(function(x){return x.id}).sort(), c: DB.contractors.map(function(x){return x.id}).sort(), a: DB.appointments.length})")
    ok(left['e'] == ['e1','e4','e5','e6','e7'] and left['p'] == 1 and left['i'] == 1 and left['k'] == ['k2'] and left['f'] == 1 and left['j'] == ['j1','j4','j5','j8'] and left['c'] == ['c1','c5'] and left['a'] == 1, 'removed exactly the ticked ones %s' % left)
    ok(await pg.evaluate("(DB.recycleBin || DB._recycle || DB.recycle || []).length >= 7 || JSON.stringify(localStorage).indexOf('e3') >= 0"), 'removed records are in the Recycle Bin')
    ok(not await pg.evaluate("!!document.getElementById('bp-dups')"), 'sheet closes')
    await pg.wait_for_timeout(200)
    ok(not await pg.evaluate("!!(document.getElementById('bp-safety-banner') && /missing/.test(document.getElementById('bp-safety-banner').textContent))"), 'no "jobs missing" alarm after removing job copies on purpose')
    m = await pg.evaluate("({jobs: DB.jobs.filter(function(j){return /Kingdom/.test(j.name)}).map(function(j){return j.id}), rooms: DB.rooms.filter(function(r){return r.jobId==='j8'}).map(function(r){return r.name}).sort(), punch: DB.punchlist.filter(function(k){return k.jobId==='j8'}).map(function(k){return k.text+'@'+k.roomId}).sort(), stray: DB.punchlist.concat(DB.rooms).filter(function(x){return x.jobId==='j7'||x.jobId==='j3'}).length, kitchen: DB.rooms.filter(function(r){return r.name==='Kitchen'}).map(function(r){return r.jobId}), paintDone: !!DB.punchlist.find(function(k){return k.id==='k81'}).done})")
    ok(m['jobs'] == ['j8'] and m['rooms'] == ['Hall','Lobby','Office'] and m['punch'] == ['Door@r72','Paint@r81','Security cam@r81','Sign@r83'] and m['stray'] == 0 and m['kitchen'] == ['j1'] and m['paintDone'], 'drifted job copy merged: matching records removed, new ones moved into the kept job and its spaces %s' % m)
    alarm = "!!(document.getElementById('bp-safety-banner') && /missing/.test(document.getElementById('bp-safety-banner').textContent))"
    await pg.evaluate("var ids = DB.jobs.map(function(j){return j.id}); localStorage.setItem('bp_last_jobs', String(ids.length + 1)); localStorage.setItem('bp_last_job_ids', JSON.stringify(ids.concat(['ghost']))); bpTombstone('jobs','ghost'); try { mergeIncomingDB({ db: { jobs: [] } }); } catch(e){}"); await pg.wait_for_timeout(300)
    ok(not await pg.evaluate(alarm), 'a job deleted on another device (tombstoned) does not raise the missing alarm')
    await pg.evaluate("var ids = DB.jobs.map(function(j){return j.id}); localStorage.setItem('bp_last_jobs', String(ids.length + 1)); localStorage.setItem('bp_last_job_ids', JSON.stringify(ids.concat(['lost1']))); try { mergeIncomingDB({ db: { jobs: [] } }); } catch(e){}"); await pg.wait_for_timeout(300)
    ok(await pg.evaluate(alarm) or not await pg.evaluate("typeof mergeIncomingDB === 'function'"), 'a job that vanished with no delete still raises the alarm')
    await pg.evaluate("var b=document.getElementById('bp-safety-banner'); b&&b.remove()")
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
