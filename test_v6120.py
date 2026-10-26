"""v6.1.20 — Sync check reads the iCloud copy (fake CloudKit) and explains photo gaps, changing nothing."""
import subprocess, time, asyncio, json
from playwright.async_api import async_playwright
BLOCK=('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit')
META=json.dumps({'db':{'jobs':[{'id':'j1','name':'N. Peach St'}],'photos':[{'id':'p1','jobId':'j1','src':'bpb:aa'},{'id':'p2','jobId':'j1','src':'bpb:bb'},{'id':'p3','jobId':'j1','src':'bpb:cc'}],'tombstones':{}},'blobPieces':{'bpb:aa':1,'bpb:bb':1},'pushedAt':'2026-10-26T19:35:00Z','app':'6.1.19'})
FAKE="""window.BPShell={version:'t'};localStorage.setItem('bp_ck_on','1');window.__writes=0;
window.CloudKit={configure:function(){},getDefaultContainer:function(){return {setUpAuth:async function(){return {userRecordName:'u'}},whenUserSignsIn:function(){return new Promise(function(){})},
 privateCloudDatabase:{fetchRecords:async function(names){names=[].concat(names);var M=%s;return {records:names.map(function(n){ if(n==='bp_state')return {recordName:n,recordChangeTag:'t',fields:{pushId:{value:'x'},pieces:{value:1},pushedAt:{value:'2026-10-26T19:35:00Z'}}}; if(n==='m_x_0')return {recordName:n,fields:{data:{value:M}}}; return null;}).filter(Boolean)}},
 saveRecords:async function(){__writes++;return {}},deleteRecords:async function(){__writes++;return {}}}}}};""" % json.dumps(META)
fails=[]
def ok(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
async def main():
    srv=subprocess.Popen(['python3','-m','http.server','8825'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch()
            for page,vp,tag in (('index.html',{'width':390,'height':844},'field'),('desktop.html',{'width':1280,'height':820},'desk')):
                ctx=await b.new_context(viewport=vp); await ctx.add_init_script(FAKE)
                pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
                await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
                await pg.goto('http://localhost:8825/'+page); await pg.wait_for_timeout(2500)
                await pg.evaluate("document.getElementById('bp-lock')?.remove(); window.bpICloudSync=async function(){}; DB.jobs=[{id:'j1',name:'N. Peach St'}]; DB.photos=[]; DB.tombstones={'photos:p2':'2026-10-01T00:00:00Z'}")
                await pg.evaluate("IS_DESK_=!!document.getElementById('modal-new-room'); IS_DESK_?showView('sync'):openSync()"); await pg.wait_for_timeout(1500)
                ok(await pg.is_visible('#bp-scheck button'),tag+': Sync check button under iCloud card')
                before=await pg.evaluate("JSON.stringify({p:DB.photos,t:DB.tombstones})")
                await pg.click('#bp-scheck button'); await pg.wait_for_timeout(800)
                r=await pg.evaluate("__bpLastSyncCheck"); txt=await pg.inner_text('#bp-scheck-out')
                print('   ',txt.replace('\n',' | '))
                ok(r.get('cloudPhotos')==3 and r.get('devicePhotos')==0,tag+': counts iCloud 3 / device 0')
                ok(r.get('missingHere')==3,tag+': 3 missing here')
                ok(r.get('blockedByTombstone')==1,tag+': 1 blocked by deleted mark')
                ok(r.get('noPictureData')==1,tag+': 1 record with no uploaded picture')
                ok(r.get('cloudByJob',{}).get('N. Peach St')==3,tag+': by job')
                ok('held back by a "deleted" mark' in txt,tag+': plain-words reason shown')
                ok(await pg.evaluate("__writes")==0,tag+': nothing written to iCloud')
                ok(await pg.evaluate("JSON.stringify({p:DB.photos,t:DB.tombstones})")==before,tag+': nothing changed on device')
                await pg.screenshot(path='/tmp/claude-0/-home-claude/178513a2-bf1c-5424-835f-72accc1c0b2b/scratchpad/check_'+tag+'.png')
                ok(not errs,tag+': no page errors '+str(errs[:2]))
                await ctx.close()
            await b.close()
    finally: srv.terminate()
    print('\n%d failures'%len(fails))
asyncio.run(main())
