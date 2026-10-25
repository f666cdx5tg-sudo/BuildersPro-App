"""BuildersPro v6.1.6 safety net. Needs web.json + nat.json beside it (made by the v6.1.4 session)."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
fails=[]
def ok(c,m):
    print('  ok  ' if c else '  FAIL', m)
    if not c: fails.append(m)
async def restore(pg, f):
    async with pg.expect_file_chooser() as fc:
        await pg.evaluate("bpRestoreFromICloud()")
    await (await fc.value).set_files(f); await pg.wait_for_timeout(3500)
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8809','--directory','.'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch(); pg=await (await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)).new_page()
            errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')) else r.continue_())
            async def boot():
                await pg.wait_for_timeout(3000); await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            await pg.goto('http://localhost:8809/index.html'); await boot()
            ok(await pg.evaluate("APP_VERSION")>='6.1.6','version 6.1.6+')
            # an OLD delete marker for w1 already on the phone (like the web app's history)
            await pg.evaluate("DB.tombstones=DB.tombstones||{}; DB.tombstones['jobs:w1']='2026-10-20T00:00:00.000Z'; DB.deletedJobIds={w1:'2026-10-20T00:00:00.000Z'}; save()")
            await pg.wait_for_timeout(800)
            await restore(pg,'web.json'); await restore(pg,'nat.json')
            ok(await pg.evaluate("DB.jobs.some(j=>j.id==='w1')"),'restored job comes in despite an old delete marker')
            await pg.reload(); await boot()
            ok(await pg.evaluate("DB.jobs.some(j=>j.id==='w1') && DB.jobs.length===3"),'and survives reopen (old marker can no longer purge it)')
            # an iCloud sync arriving with an OLD delete marker for w1
            await pg.evaluate("mergeIncomingDB({pushedAt:'x',db:{tombstones:{'jobs:w1':'2026-10-21T00:00:00.000Z','punchlist:p1':'2026-10-21T00:00:00.000Z'}}}); purgeTombstonedLocally(); purgeDeletedJobsLocally()")
            ok(await pg.evaluate("DB.jobs.some(j=>j.id==='w1') && DB.punchlist.some(p=>p.id==='p1')"),'a synced OLD delete cannot remove restored records')
            # a NEW delete after the restore still works
            await pg.evaluate("bpRemoveFrom('punchlist', x=>x.id!=='pw'); save()"); await pg.wait_for_timeout(600)
            await pg.reload(); await boot()
            ok(await pg.evaluate("!DB.punchlist.some(p=>p.id==='pw')"),'a NEW delete after the restore still sticks')
            # safety copy exists
            ok(await pg.evaluate("new Promise(r=>idbGet('bp_safety_index',l=>r(Array.isArray(l)&&l.some(x=>x.jobs>0))))"),'daily safety copy saved')
            # missing-job alarm: wipe jobs behind the app's back, reopen
            await pg.evaluate("new Promise(r=>idbGet('bp_db_meta',m=>{m.jobs=m.jobs.slice(0,1);idbSet('bp_db_meta',m,r)}))")
            await pg.reload(); await boot()
            txt=await pg.evaluate("(document.getElementById('bp-safety-banner')||{}).textContent||''")
            ok('missing since last time' in txt,'missing-job alarm shows: '+txt[:80])
            await pg.evaluate("document.getElementById('bp-safety-banner').click()"); await pg.wait_for_timeout(2500)
            ok(await pg.evaluate("DB.jobs.length")==3,'one tap brings back the safety copy: '+str(await pg.evaluate("DB.jobs.length")))
            ok(await pg.evaluate("DB.photos.filter(p=>p.jobId==='w1'&&String(p.src).startsWith('data:')).length")>=2,'safety copy photos intact')
            ok(not errs,'no page errors '+str(errs[:3]))
            await b.close()
    finally: srv.terminate()
    print(len(fails),'failed'); sys.exit(1 if fails else 0)
asyncio.run(main())
