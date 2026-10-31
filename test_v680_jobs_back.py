"""v6.8.0 — the jobs 6.7.9 removed come back by themselves; deleted stays deleted.
1. Jobs gone from the device (old delete markers, keep stamps cleared by 6.7.9) come back from the
   device's safety copy with their punch items and photos — but not a job you deleted yourself, nor a
   duplicate you merged.
2. They stay after reopening and when another device sends its old delete marker.
3. A NEWER delete from another device still removes the job (deleted stays deleted).
4. Reopening the app (even 3 days later) opens the job you were on.
Run from repo root: python3 test_v680_jobs_back.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8980
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
PHOTO = 'data:image/png;base64,' + 'A' * 4000
SEED = """(photo) => new Promise(function(done){
  var t0 = '2026-10-20T10:00:00.000Z';
  var full = { jobs: [{id:'jA',name:'N. Peach St',status:'Active',updatedAt:t0},{id:'jB',name:'Shedwick',status:'Active',updatedAt:t0},
                      {id:'jD',name:'Deleted by me',status:'Active',updatedAt:t0},{id:'jM',name:'Merged dup',status:'Active',updatedAt:t0}],
               punchlist: [{id:'kA',jobId:'jA',text:'peach punch',done:false},{id:'kB',jobId:'jB',text:'shed punch',done:false},{id:'kD',jobId:'jD',text:'x',done:false}],
               photos: [{id:'pA',jobId:'jA',data:photo}] };
  var blobs = {}, meta = bpSplitBlobs(full, blobs);
  var refs = Object.keys(blobs), n = refs.length;
  function rest(){
    idbSet('bp_safety_2026-10-31T11-00', { at:'2026-10-31T11:00:00.000Z', why:'daily', jobs:4, meta: meta }, function(){
      idbSet('bp_safety_index', [{ key:'bp_safety_2026-10-31T11-00', at:'2026-10-31T11:00:00.000Z', why:'daily', jobs:4 }], function(){
        /* what 6.7.9 left behind: no jobs, old delete markers, no keep stamps */
        DB.jobs = []; DB.punchlist = []; DB.photos = [];
        DB.tombstones = {'jobs:jA':t0,'jobs:jB':t0,'jobs:jD':'2026-10-29T10:00:00.000Z','punchlist:kB':t0};
        DB.keepStamps = {}; DB.jobMerges = {jM:'jA'};
        DB.recycle = [{id:'rc_jobs_jD',coll:'jobs',rec:{id:'jD',name:'Deleted by me'},label:'x',deletedAt:'2026-10-29T10:00:00.000Z'}];
        try { localStorage.removeItem('bp_v680_recovered'); } catch(e){}
        bpSave(); done();
      });
    });
  }
  if (!n) rest(); else refs.forEach(function(r){ idbSet('bpb1:' + r, blobs[r], function(){ if (--n === 0) rest(); }); });
})"""
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
                await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(2500)
                await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove()")
                ok('6.8.0' == await pg.evaluate("APP_VERSION"), 'version 6.8.0')
                await pg.evaluate(SEED, PHOTO)
                ok(await pg.evaluate(JOBS) == [], 'setup: jobs missing (2 → 0), like the iPhone')
                r = await pg.evaluate("bpRecoverJobs680()")
                ok(r.get('back') == 2, 'two jobs brought back %s' % r)
                ok(await pg.evaluate(JOBS) == ['jA','jB'], 'N. Peach St and Shedwick are back; the one I deleted and the merged duplicate are not')
                ok(await pg.evaluate("DB.punchlist.map(function(x){return x.id}).sort()") == ['kA','kB'], 'their punch items came back')
                ok(await pg.evaluate("(DB.photos[0]||{}).data") == PHOTO, 'the photo came back with its picture')
                ok(await pg.evaluate("new Set(Object.values(DB.keepStamps)).size === Object.keys(DB.keepStamps).length"), 'each record has its own keep stamp')
                await pg.reload(); await pg.wait_for_timeout(2500)
                ok(await pg.evaluate(JOBS) == ['jA','jB'], 'still there after reopening the app')
                await pg.evaluate("mergeIncomingDB({ db: { jobs: [], tombstones: {'jobs:jA':'2026-10-20T10:00:00.000Z','jobs:jB':'2026-10-20T10:00:00.000Z'} } })")
                ok(await pg.evaluate(JOBS) == ['jA','jB'], "another device's old delete marker can't remove them")
                r2 = await pg.evaluate("bpRecoverJobs680()")
                ok(r2.get('back') == 0, 'runs once only %s' % r2)
                await pg.evaluate("mergeIncomingDB({ db: { tombstones: {'jobs:jB': new Date(Date.now() + 60000).toISOString()} } })")
                ok(await pg.evaluate(JOBS) == ['jA'], 'deleting a job on another device later still removes it here')
                if file == 'index.html':
                    await pg.evaluate("document.getElementById('bp-lock')&&document.getElementById('bp-lock').remove(); openJobDetail('jA')"); await pg.wait_for_timeout(500)
                    await pg.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:function(){return true}}); document.dispatchEvent(new Event('visibilitychange'));"); await pg.wait_for_timeout(500)
                    await pg.close()
                    await ctx.add_init_script("try { if (!sessionStorage.getItem('aged')) { sessionStorage.setItem('aged','1'); var r=JSON.parse(localStorage.getItem('bp_resume_v1')); r.at -= 3*864e5; localStorage.setItem('bp_resume_v1', JSON.stringify(r)); } } catch(e){}")
                    pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
                    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
                    await pg.goto('http://localhost:%d/%s' % (PORT, file)); await pg.wait_for_timeout(3000)
                    ok(await pg.evaluate("document.querySelector('.screen.active').id") == 's-job-detail' and await pg.evaluate("currentJobId") == 'jA', 'opened 3 days later: back on the job you were on')
                ok(not errs, 'no page errors %s' % errs[:2]); await ctx.close()
            await b.close()
    finally:
        srv.terminate()
    print('\n%d/%d checks passed' % (checks - len(fails), checks))
    sys.exit(1 if fails else 0)
asyncio.run(main())
