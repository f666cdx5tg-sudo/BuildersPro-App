"""v6.1.22 — bring back what a duplicate-job delete took. Runs on a COPY of Stan's real records
(scratch realdb.json, no pictures) in both apps: right counts, nothing doubled, nothing from earlier
deletes, everything pointed at live jobs/spaces/subs, survives a sync to another device, runs once."""
import subprocess, time, asyncio, json, sys, os
from playwright.async_api import async_playwright
REAL=sys.argv[1] if len(sys.argv)>1 else '/tmp/claude-0/-home-claude/178513a2-bf1c-5424-835f-72accc1c0b2b/scratchpad/realdb.json'
BLOCK=('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')
fails=[]
def ok(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
async def main():
    real=open(REAL).read()
    srv=subprocess.Popen(['python3','-m','http.server','8826'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch()
            for page,vp,tag in (('desktop.html',{'width':1280,'height':820},'desk'),('index.html',{'width':390,'height':844},'field')):
                ctx=await b.new_context(viewport=vp)
                pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
                await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
                await pg.goto('http://localhost:8826/'+page); await pg.wait_for_timeout(2500)
                await pg.evaluate("document.getElementById('bp-lock')?.remove()")
                await pg.evaluate("(s)=>{ window.__orig=s; DB=JSON.parse(s); window.bpICloudSync=undefined; }", real)
                plan=await pg.evaluate("(function(){var p=bpRecoverPlan();return {total:p.total,counts:p.counts,jobMap:p.jobMap}})()")
                print('   plan',plan)
                c=plan['counts']
                ok(c.get('photos')==193,tag+': 193 gallery photos to bring back')
                ok(c.get('payments')==29,tag+': all 29 sub payments')
                ok(plan['jobMap']=={'pb6_d9a5':'nxj_pb6_d9a5','pb401_0a0vt':'nxj_pb401_0a0vt'},tag+': old jobs map to live N. Peach St / Shedwick; Test Kitchen left out')
                before=await pg.evaluate("({photos:DB.photos.length,payments:(DB.payments||[]).length,punch:DB.punchlist.length,rooms:DB.rooms.length,bin:DB.recycle.length,expenses:DB.expenses.length,jobs:DB.jobs.length})")
                r=await pg.evaluate("bpRecoverFromDeletedJobs(true)")
                print('   result',r)
                after=await pg.evaluate("""(function(){
                  var low=s=>String(s==null?'':s).trim().toLowerCase().replace(/\\s+/g,' ');
                  var live=new Set(DB.jobs.map(j=>j.id)), rooms=new Set(DB.rooms.map(r=>r.id)), cons=new Set(DB.contractors.map(c=>c.id));
                  var ph=DB.photos.filter(p=>p.restoredAt);
                  var punchTexts={}; DB.punchlist.forEach(x=>{var k=x.jobId+'|'+low(x.text); punchTexts[k]=(punchTexts[k]||0)+1;});
                  var origPunch={}; JSON.parse(__orig).punchlist.forEach(x=>{var k=x.jobId+'|'+low(x.text); origPunch[k]=(origPunch[k]||0)+1;});
                  var doubled=Object.keys(punchTexts).filter(k=>origPunch[k] && punchTexts[k]>origPunch[k]).length;
                  var srcs={}; DB.photos.forEach(p=>srcs[p.jobId+'|'+p.src]=(srcs[p.jobId+'|'+p.src]||0)+1);
                  var restored=[].concat(...Object.keys(DB).filter(k=>Array.isArray(DB[k])&&k!=='recycle').map(k=>DB[k].filter(x=>x&&x.restoredAt)));
                  return {photos:DB.photos.length, payments:(DB.payments||[]).length, punch:DB.punchlist.length, rooms:DB.rooms.length, bin:DB.recycle.length, expenses:DB.expenses.length, jobs:DB.jobs.length,
                    photosOnLiveJob: ph.filter(p=>live.has(p.jobId)).length, photosOnLiveSpace: ph.filter(p=>p.roomId&&rooms.has(p.roomId)).length, photosUnfiled: ph.filter(p=>!p.roomId).length,
                    photosBrokenSpace: ph.filter(p=>p.roomId&&!rooms.has(p.roomId)).length,
                    payOnLiveSub: DB.payments.filter(p=>cons.has(p.contractorId)).length, punchDoubled: doubled, photoDoubles: Object.values(srcs).filter(n=>n>1).length,
                    newIdsOnly: restored.every(x=>/^pb\\d+_/.test(x.id) && x.restoredFrom && x.id!==x.restoredFrom),
                    anyTombstoned: restored.filter(x=>DB.tombstones && Object.keys(DB.tombstones).some(t=>t.endsWith(':'+x.id))).length,
                    spacesBack: DB.rooms.filter(r=>r.restoredAt).map(r=>r.name)}; })()""")
                print('   after',after)
                ok(after['photos']==193 and after['photosOnLiveJob']==193,tag+': 193 photos now on the live job')
                ok(after['photosBrokenSpace']==0,tag+': no photo points at a missing space ('+str(after['photosOnLiveSpace'])+' filed, '+str(after['photosUnfiled'])+' unfiled as before)')
                ok(after['payments']==29 and after['payOnLiveSub']==29,tag+': 29 payments, every one on a current sub')
                ok(after['punchDoubled']==0,tag+': no punch item doubled')
                ok(after['photoDoubles']==7,tag+': no NEW photo doubles (the 7 pictures saved twice in the original stay as they were)')
                ok(after['expenses']==before['expenses'] and after['jobs']==before['jobs'],tag+': expenses and jobs unchanged (nothing doubled)')
                ok(after['newIdsOnly'],tag+': every restored record has a fresh id')
                ok(after['anyTombstoned']==0,tag+': no restored record is under a delete mark')
                ok(after['bin']==before['bin']-r['restored'],tag+': restored items left Recently Deleted')
                again=await pg.evaluate("bpRecoverPlan().total")
                ok(again==0,tag+': running it again finds nothing (no doubling on a second tap)')
                # the restored data survives a sync into another device that still has the old state
                surv=await pg.evaluate("""(function(){ var mine=JSON.parse(JSON.stringify(DB)); DB=JSON.parse(__orig); mergeIncomingDB({pushedAt:'x', db:mine});
                  return {photos:DB.photos.length, payments:(DB.payments||[]).length}; })()""")
                ok(surv['photos']==193 and surv['payments']==29,tag+': other device gets them after sync '+str(surv))
                ok(not errs,tag+': no page errors '+str(errs[:2]))
                await ctx.close()
            # UI card shows on Recently Deleted (desk)
            ctx=await b.new_context(viewport={'width':1280,'height':820}); pg=await ctx.new_page()
            await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
            await pg.goto('http://localhost:8826/desktop.html'); await pg.wait_for_timeout(2500)
            await pg.evaluate("(s)=>{ document.getElementById('bp-lock')?.remove(); DB=JSON.parse(s); window.bpICloudSync=undefined; }", real)
            await pg.evaluate("showView('sync'); try{bpRenderRecycle()}catch(e){}"); await pg.wait_for_timeout(2000)
            t=await pg.evaluate("(function(){var c=document.getElementById('bp-recover-card');return c?c.innerText:'NO CARD; recycle visible='+!!(document.getElementById('recycle-wrap')||{}).offsetParent})()")
            ok('Bring back' in t,'desk: card on Recently Deleted: '+t.replace('\n',' | ')[:160])
            await pg.screenshot(path='/tmp/claude-0/-home-claude/178513a2-bf1c-5424-835f-72accc1c0b2b/scratchpad/recover_card.png')
            await b.close()
    finally: srv.terminate()
    print('\n%d failures'%len(fails))
asyncio.run(main())
