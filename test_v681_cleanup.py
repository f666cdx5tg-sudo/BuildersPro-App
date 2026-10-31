"""v6.8.1 — the clean-up after 6.8.0: duplicate jobs (same name) become one, records moved into the
kept job; Test Kitchen Remodel removed; another device's 6.8.0 recovery can't bring any of them back.
Run from repo root: python3 test_v681_cleanup.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8981
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => {
  var t0 = '2026-10-01T10:00:00.000Z', t1 = '2026-10-20T10:00:00.000Z';
  DB.jobs = [{id:'jA2',name:'N. Peach St',address:'1536 N. Peach St',createdAt:t0},{id:'jA',name:'N. Peach St',address:'1536 N. Peach St',createdAt:t1},
             {id:'jB',name:'Shedwick',createdAt:t0},{id:'jB2',name:'shedwick ',createdAt:t1},{id:'jT',name:'Test Kitchen Remodel',createdAt:t0}];
  DB.punchlist = [{id:'k1',jobId:'jA',text:'Set toilet',done:false},{id:'k1c',jobId:'jA2',text:'Set toilet',done:true},{id:'k2',jobId:'jA2',text:'Only in the copy',done:false},
                  {id:'k3',jobId:'jB',text:'Shed door'},{id:'kT',jobId:'jT',text:'test item'}];
  DB.expenses = [{id:'e1',jobId:'jB2',amount:120,date:'2026-10-10',vendor:'HD',desc:'pipe'}];
  DB.jobMerges = {jOld:'jA'};   /* an earlier Find duplicates kept jA */
  DB.tombstones = {}; DB.keepStamps = {}; DB.recycle = [];
  try { localStorage.removeItem('bp_v681_clean'); } catch(e){}
  bpSave();
}"""
JOBS = "DB.jobs.map(function(x){return x.id}).sort()"
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for file, w, h in (('index.html', 402, 874), ('desktop.html', 1440, 900)):
                print('\n' + file)
                ctx = await b.new_context(viewport={'width': w, 'height': h})
                pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
                await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(5000)
                await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
                ok(await pg.evaluate("APP_VERSION") >= '6.8.1', 'version 6.8.1 or later')
                await pg.evaluate(SEED)
                r = await pg.evaluate("bpCleanUp681()")
                ok(r.get('merged') == 2 and r.get('removed') == 1, 'two duplicates merged, the test job removed %s' % r)
                ok(await pg.evaluate(JOBS) == ['jA','jB'], 'one N. Peach St (the one kept before) and one Shedwick (the oldest)')
                pl = await pg.evaluate("DB.punchlist.map(function(x){return x.id+':'+x.jobId+':'+!!x.done}).sort()")
                ok(pl == ['k1:jA:true','k2:jA:false','k3:jB:false'], 'punch moved into the kept job, the done tick carried over, the copy twin removed %s' % pl)
                ok(await pg.evaluate("DB.expenses.map(function(x){return x.jobId})") == ['jB'], "the copy's expense moved to the kept Shedwick")
                ok(await pg.evaluate("['jobs:jA2','jobs:jB2','jobs:jT'].every(function(k){return DB.tombstones[k]})"), 'the removed jobs are marked deleted')
                ok(await pg.evaluate("bpCleanUp681().why") == 'already done', 'runs once')
                # another device's 6.8.0 recovery from an older safety copy can't bring them back
                await pg.evaluate("""() => new Promise(function(done){
                  var meta = { jobs:[{id:'jA2',name:'N. Peach St'},{id:'jT',name:'Test Kitchen Remodel'},{id:'jX',name:'Real lost job'},{id:'jX2',name:'Real lost job'}], punchlist:[] };
                  idbSet('bp_safety_t', {at:'2026-10-31T11:00:00.000Z',jobs:4,meta:meta}, function(){
                    idbSet('bp_safety_index', [{key:'bp_safety_t',at:'2026-10-31T11:00:00.000Z',jobs:4}], function(){ localStorage.removeItem('bp_v680_recovered'); done(); }); }); })""")
                r2 = await pg.evaluate("bpRecoverJobs680()")
                ok(await pg.evaluate(JOBS) == ['jA','jB','jX'], 'recovery skips what the clean-up removed, and brings a real lost job back once %s' % r2)
                await pg.reload(); await pg.wait_for_timeout(5000)
                ok(await pg.evaluate(JOBS) == ['jA','jB','jX'], 'same after reopening')
                ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
            await b.close()
    finally:
        srv.terminate()
    print('\n%d/%d checks passed' % (checks - len(fails), checks))
    sys.exit(1 if fails else 0)
asyncio.run(main())
