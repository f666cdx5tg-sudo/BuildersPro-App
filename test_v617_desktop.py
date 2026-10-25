"""BuildersPro v6.1.7: data-safety layers on the Mac Command Center (desktop.html). Needs web.json + nat.json."""
import subprocess, time, asyncio, sys
from playwright.async_api import async_playwright
fails=[]
def ok(c,m):
    print('  ok  ' if c else '  FAIL', m)
    if not c: fails.append(m)
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8810','--directory','.'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch(); pg=await (await b.new_context(viewport={'width':1400,'height':900})).new_page()
            errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            msgs=[]
            async def dlg(d): msgs.append(d.message); await d.accept()
            pg.on('dialog', lambda d: asyncio.ensure_future(dlg(d)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')) else r.continue_())
            async def boot():
                await pg.wait_for_timeout(3500); await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            await pg.goto('http://localhost:8810/desktop.html'); await boot()
            ok(await pg.evaluate("APP_VERSION")=='6.1.7','Command Center is 6.1.7')
            await pg.evaluate("DB.tombstones=DB.tombstones||{}; DB.tombstones['jobs:w1']='2026-10-20T00:00:00.000Z'; saveDB()"); await pg.wait_for_timeout(600)
            for f in ('web.json','nat.json'):
                async with pg.expect_file_chooser() as fc:
                    await pg.evaluate("bpRestoreFromICloud()")
                await (await fc.value).set_files(f); await pg.wait_for_timeout(3500)
            ok(any('read back' in m for m in msgs),'restore reports the read-back: '+next((m.split('\n')[-1] for m in msgs if 'read back' in m),'none'))
            ok(any('records match' in m for m in msgs),'second restore matches instead of doubling')
            await pg.reload(); await boot()
            r=await pg.evaluate("[DB.jobs.length, DB.rooms.filter(x=>x.jobId==='w1').length, DB.photos.filter(x=>x.jobId==='w1').length]")
            ok(r==[3,3,2],'after reopen: 3 jobs, spaces + photos not doubled, old delete ignored: '+str(r))
            ok(await pg.evaluate("new Promise(r=>idbGet('bp_blob_index',v=>r(Array.isArray(v))))"),'photos stored one per record on the Mac too')
            await pg.evaluate("new Promise(r=>idbGet('bp_db_meta',m=>{m.jobs=m.jobs.slice(0,1);idbSet('bp_db_meta',m,r)}))")
            await pg.reload(); await boot()
            ok('missing since last time' in await pg.evaluate("(document.getElementById('bp-safety-banner')||{}).textContent||''"),'missing-job alarm on the Mac')
            await pg.evaluate("document.getElementById('bp-safety-banner').click()"); await pg.wait_for_timeout(2500)
            ok(await pg.evaluate("DB.jobs.length")==3,'one click brings the safety copy back')
            ok(not errs,'no page errors '+str(errs[:3]))
            await b.close()
    finally: srv.terminate()
    print(len(fails),'failed'); sys.exit(1 if fails else 0)
asyncio.run(main())
