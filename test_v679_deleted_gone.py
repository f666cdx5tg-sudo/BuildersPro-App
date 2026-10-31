"""v6.7.9 — deleted means gone; the app opens where you left off.
1. A job deleted earlier but brought back by an old mass "keep" stamp (from a backup restore) is removed again,
   with its punch items; a single item restored on purpose from the Recycle Bin stays.
2. Another device sending the deleted job (with its old mass stamps) can't bring it back.
3. Reopening the app (even 3 days later) opens the job you were on.
Run from repo root: python3 test_v679_deleted_gone.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8979
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
SEED = """() => {
  var t1 = '2026-10-20T10:00:00.000Z', t2 = '2026-10-25T10:00:00.000Z', t3 = '2026-10-28T10:00:00.000Z';
  DB.jobs = [{id:'jA',name:'Keep me',status:'Active',updatedAt:t1},{id:'jB',name:'Deleted job',status:'Active',updatedAt:t1}];
  DB.punchlist = [{id:'kA',jobId:'jA',text:'stays',done:false},{id:'kB1',jobId:'jB',text:'of deleted job',done:false},{id:'kR',jobId:'jA',text:'restored on purpose',done:false}];
  DB.tombstones = {'jobs:jB':t1,'punchlist:kR':t1};
  DB.keepStamps = {'jobs:jB':t2,'punchlist:kB1':t2,'jobs:jA':t2,'punchlist:kA':t2,'photos:x':t2,'punchlist:kR':t3};
  DB.recycle = [];
  bpSave();
}"""
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
                await pg.evaluate(SEED)
                ok(await pg.evaluate("DB.jobs.length") == 2, 'setup: the deleted job is back (old mass keep-stamp)')
                await pg.evaluate("bpEnforceDeletes()")
                r = await pg.evaluate("({j: DB.jobs.map(function(x){return x.id}), k: DB.punchlist.map(function(x){return x.id}).sort()})")
                ok(r['j'] == ['jA'], 'the deleted job is gone again %s' % r['j'])
                ok(r['k'] == ['kA','kR'], 'its punch items went with it; the one restored on purpose stays %s' % r['k'])
                await pg.evaluate("""mergeIncomingDB({ db: { jobs: [{id:'jB',name:'Deleted job',updatedAt:'2026-10-30T00:00:00Z'}], punchlist: [{id:'kB1',jobId:'jB',text:'x'}],
                   keepStamps: {'jobs:jB':'2026-10-29T00:00:00Z','punchlist:kB1':'2026-10-29T00:00:00Z','a:1':'2026-10-29T00:00:00Z','a:2':'2026-10-29T00:00:00Z','a:3':'2026-10-29T00:00:00Z'} } })""")
                ok(await pg.evaluate("DB.jobs.map(function(x){return x.id})") == ['jA'], 'another device sending the deleted job cannot bring it back')
                await pg.reload(); await pg.wait_for_timeout(2500)
                ok(await pg.evaluate("DB.jobs.map(function(x){return x.id})") == ['jA'], 'and after reopening the app it is still gone')
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
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
