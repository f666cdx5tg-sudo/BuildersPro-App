import subprocess, time, asyncio, sys
from playwright.async_api import async_playwright
import os; S=os.path.dirname(os.path.abspath(__file__))  # needs web.json + nat.json (made by the v6.1.4 session)
fails=[]
def ok(c,m):
    print('  ok  ' if c else '  FAIL', m); 
    if not c: fails.append(m)
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8808','--directory','.'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch(); pg=await (await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)).new_page()
            errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            msgs=[]
            async def dlg(d): msgs.append(d.message); await d.accept()
            pg.on('dialog', lambda d: asyncio.ensure_future(dlg(d)))
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')) else r.continue_())
            await pg.goto('http://localhost:8808/index.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            ok(await pg.evaluate("APP_VERSION")=='6.1.4','version 6.1.4')
            for f in ('web.json','nat.json'):
                async with pg.expect_file_chooser() as fc:
                    await pg.evaluate("bpRestoreFromICloud()")
                await (await fc.value).set_files(S+'/'+f)
                for i in range(20):
                    await pg.wait_for_timeout(500)
                    if any('read back' in m or 'NOT save' in m for m in msgs[-1:]): break
            q=[m for m in msgs if m.startswith('Restore this backup?')]
            ok(len(q)==2 and 'records match' in q[1],'second restore question says how many match: '+(q[1].split('\n')[-1] if len(q)>1 else str(q)))
            r=await pg.evaluate("""({jobs:DB.jobs.map(j=>j.name).sort(), rooms:DB.rooms.filter(r=>r.jobId==='w1').map(r=>r.name).sort(),
               punch:DB.punchlist.filter(p=>p.jobId==='w1').map(p=>p.text+':'+p.done).sort(), photos:DB.photos.filter(p=>p.jobId==='w1').length,
               appts:DB.appointments.filter(a=>a.jobId==='w1').length, job:DB.jobs.find(j=>j.id==='w1'),
               orphan:DB.punchlist.filter(p=>p.jobId && !DB.jobs.some(j=>j.id===p.jobId)).length,
               badRoom:DB.punchlist.filter(p=>p.roomId && !DB.rooms.some(r=>r.id===p.roomId)).length})""")
            print(r['jobs'], r['rooms'], r['punch'])
            ok(r['jobs']==['N. Peach St','Shedwick','Web Only Job'],'jobs not doubled, both sides kept')
            ok(r['rooms']==['Bath','Kitchen','Stairs'],'spaces not doubled (Stairs once), Bath + Kitchen kept')
            ok(r['punch']==['Install handrail:true','Native only item:false','Web only item:false'],'punch merged: native tick wins, both-only items kept')
            ok(r['photos']==2,'same picture not doubled: '+str(r['photos']))
            ok(r['appts']==1,'appointment not doubled')
            j=r['job']; ok(j['city']=='Philadelphia' and j['address']=='1536 N. Peach St' and j['clientEmail']=='sw@x.com','job keeps web split address + email when native has blanks')
            ok(r['orphan']==0 and r['badRoom']==0,'every punch item points at a real job and space')
            ok(await pg.evaluate("(DB.contacts||[]).some(c=>c.type==='Client'&&c.name==='Shelden Washington') && (DB.contacts||[]).some(c=>c.name==='Joe Tile')"),'client + phone book contact present')
            await pg.reload(); await pg.wait_for_timeout(3500); await pg.evaluate("document.getElementById('bp-lock')?.remove()")
            ok(await pg.evaluate("DB.jobs.length")==3,'all still there after reopen')
            # normal sync merge is not reconciled
            await pg.evaluate("mergeIncomingDB({pushedAt:'x',db:{jobs:[{id:'nxj_zz',name:'N. Peach St',client:'Shelden Washington'}]}})")
            ok(await pg.evaluate("DB.jobs.length")==4,'normal sync untouched by restore matching')
            ok(not errs,'no page errors '+str(errs[:3]))
            await b.close()
    finally: srv.terminate()
    print(len(fails),'failed')
asyncio.run(main())
