import subprocess, time, asyncio, sys
from playwright.async_api import async_playwright
import os; S=os.path.dirname(os.path.abspath(__file__))  # needs big.json + exp.json beside it
fails=[]
def ok(c,m):
    print('  ok  ' if c else '  FAIL', m)
    if not c: fails.append(m)
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8806','--directory','.'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); pg=await ctx.new_page()
            errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            alerts=[]
            async def dlg(d):
                alerts.append(d.message); await d.accept()
            pg.on('dialog', lambda d: asyncio.ensure_future(dlg(d)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')) else r.continue_())
            # old format first: simulate an existing phone with legacy bp_blobs
            await pg.goto('http://localhost:8806/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            ok(await pg.evaluate("APP_VERSION")=='6.1.2','version 6.1.2')
            await pg.evaluate("""new Promise(r=>{DB.jobs.push({id:'old1',name:'Old Job'});DB.photos.push({id:'op1',jobId:'old1',src:'data:image/jpeg;base64,'+'A'.repeat(5000)});
               var blobs={},meta=bpSplitBlobs(DB,blobs); idbDel('bp_blob_index',()=>idbDel('bp_db_meta',()=>{ var tx=_idbHandle.transaction('kv','readwrite');tx.objectStore('kv').put(blobs,'bp_blobs');tx.objectStore('kv').put(meta,'bp_db_meta');tx.oncomplete=r;}));})""")
            await pg.reload(); await pg.wait_for_timeout(3000); await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            ok(await pg.evaluate("DB.jobs.some(j=>j.id==='old1') && DB.photos.find(p=>p.id==='op1').src.startsWith('data:')"),'old-format phone loads (job + photo)')
            await pg.wait_for_timeout(1500)
            ok(await pg.evaluate("new Promise(r=>idbGet('bp_blob_index',v=>r(Array.isArray(v)&&v.length===1)))"),'converted to per-photo storage')
            ok(await pg.evaluate("new Promise(r=>idbGet('bp_blobs',v=>r(!v)))"),'old giant record removed after conversion')
            # big restore
            async with pg.expect_file_chooser() as fc:
                await pg.evaluate("bpRestoreFromICloud()")
            await (await fc.value).set_files(S+'/big.json')
            for i in range(60):
                await pg.wait_for_timeout(1000)
                if any('Saved on this phone' in a or 'did NOT save' in a for a in alerts): break
            ok(any('Saved on this phone and read back: 2 jobs, 185 photos' in a for a in alerts) or any('read back: 2 jobs' in a for a in alerts),'restore waits for phone save and reports read-back: '+(alerts[-1][-90:] if alerts else 'none'))
            await pg.reload(); await pg.wait_for_timeout(4000); await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            n=await pg.evaluate("[DB.jobs.length,DB.punchlist.length,DB.photos.length,DB.photos.filter(p=>String(p.src).startsWith('data:')).length]")
            ok(n[0]==2 and n[1]==2 and n[2]==182 and n[3]==182,'after reopen everything is still there: '+str(n))
            await pg.evaluate("openSync()"); await pg.wait_for_timeout(800)
            card=await pg.evaluate("document.getElementById('bp-save-diag')?.innerText||''")
            ok('Saved on this phone' in card and 'jobs' in card,'Sync shows the phone-save card: '+card.replace('\n',' | ')[:160])
            # failure path: force an aborting write
            await pg.evaluate("closeSheet('sheet-sync'); window._realOpen=idbOpen; window.idbOpen=function(cb){cb(null)}; DB.jobs[0].name='X'; save()")
            await pg.wait_for_timeout(1000)
            ok(await pg.evaluate("!!document.getElementById('bp-save-banner') && document.getElementById('bp-save-banner').textContent.indexOf('NOT saved')>-1"),'a failed save shows a red banner')
            await pg.evaluate("window.idbOpen=window._realOpen; document.getElementById('bp-save-banner').click()")
            await pg.wait_for_timeout(1500)
            ok(await pg.evaluate("!document.getElementById('bp-save-banner')"),'tapping the banner retries and it clears when the save works')
            # tick a punch item and reopen — small saves still work
            await pg.evaluate("DB.punchlist[0].done=!DB.punchlist[0].done; window._t=DB.punchlist[0].done; save()"); await pg.wait_for_timeout(1200)
            t=await pg.evaluate("window._t")
            await pg.reload(); await pg.wait_for_timeout(3500); await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            ok(await pg.evaluate("DB.punchlist[0].done")==t,'a single tick survives reopen')
            ok(not errs,'no page errors '+str(errs[:3]))
            await b.close()
    finally: srv.terminate()
    print(len(fails),'failed'); sys.exit(1 if fails else 0)
asyncio.run(main())
