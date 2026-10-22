"""BuildersPro v4.53 (multi-photo upload no longer crashes: one-at-a-time queue).
Run from repo root: python3 test_v453.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, tempfile, random
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
def make_images(d, n, w=3200, h=2400):
    from PIL import Image
    paths = []
    for i in range(n):
        random.seed(i)
        im = Image.effect_noise((w // 8, h // 8), 60).convert('RGB').resize((w, h))
        p = os.path.join(d, 'big%02d.jpg' % i); im.save(p, 'JPEG', quality=92); paths.append(p)
    return paths
INSTR = """(function(){
  window.__max=0; window.__cur=0; window.__saves=0; window.__renders=0;
  var oc=window.bpCompressFor; window.bpCompressFor=function(k,u,cb){ window.__cur++; window.__max=Math.max(window.__max,window.__cur);
    return oc.call(this,k,u,function(s){ window.__cur--; cb(s); }); };
  var os_=window.save; window.save=function(){ window.__saves++; return os_.apply(this,arguments); };
  var or_=window.renderAll; window.renderAll=function(){ window.__renders++; return or_.apply(this,arguments); };
  window.__input=function(id){ var i=document.createElement('input'); i.type='file'; i.multiple=true; i.id=id; document.body.appendChild(i); return i; };
})()"""
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8787','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    tmp = tempfile.mkdtemp()
    imgs = make_images(tmp, 12)
    bad = os.path.join(tmp, 'broken.jpg'); open(bad, 'wb').write(b'not really a jpeg' * 20)
    try:
      async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho')) else r.continue_())
        await pg.goto('http://localhost:8787/index.html'); await pg.wait_for_timeout(2500)
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        ok(await pg.evaluate("APP_VERSION==='4.53'"), 'version 4.53')
        await pg.evaluate("(function(){ DB.jobs.push({id:'jA',name:'Smith Reno',status:'active'}); DB.rooms=DB.rooms||[]; DB.rooms.push({id:'rA',jobId:'jA',name:'Bath'}); DB.photos=[]; })()")
        await pg.evaluate(INSTR)

        # 1 twelve big photos, stamp ON
        await pg.evaluate("localStorage.setItem('bp_stamp','1')")
        await pg.evaluate("window.__input('in1')")
        await pg.set_input_files('#in1', imgs)
        await pg.evaluate("addPhotos(document.getElementById('in1'),'jA','rA')")
        # roomId must be captured at pick time, even if the app state changes right after
        await pg.evaluate("window.currentRoomId='rWRONG'; window.currentJobId='jWRONG'")
        await pg.wait_for_function("DB.photos.length>=12", timeout=90000)
        await pg.wait_for_timeout(800)
        r = await pg.evaluate("({n:DB.photos.length,max:__max,saves:__saves,renders:__renders,jobs:DB.photos.map(p=>p.jobId),rooms:DB.photos.map(p=>p.roomId),srcs:DB.photos.every(p=>p.src.slice(0,16)==='data:image/jpeg;'),kb:Math.max.apply(null,DB.photos.map(p=>p.src.length*0.75/1024))})")
        ok(r['n'] == 12, 'all 12 photos stored (%s)' % r['n'])
        ok(r['max'] == 1, 'only one photo in the compressor at a time (max %s)' % r['max'])
        ok(r['saves'] <= 5, 'saves batched, not one per photo (%s)' % r['saves'])
        ok(r['renders'] == 1, 'one render for the whole batch (%s)' % r['renders'])
        ok(all(j == 'jA' for j in r['jobs']), 'job captured at pick time')
        ok(all(x == 'rA' for x in r['rooms']), 'room captured at pick time')
        ok(r['srcs'], 'all stored as compressed jpeg data URLs')
        ok(r['kb'] < 900, 'stored photos are small (max %.0f KB)' % r['kb'])
        ok(await pg.evaluate("document.querySelectorAll('[class*=toast], body > div').length>0"), 'page alive')

        # 2 a broken file in the middle does not kill the batch
        await pg.evaluate("window.currentJobId='';window.currentRoomId='';DB.photos=[];window.__max=0;window.__saves=0;window.__renders=0")
        await pg.evaluate("window.__input('in2')")
        await pg.set_input_files('#in2', [imgs[0], bad, imgs[1], imgs[2]])
        await pg.evaluate("addPhotos(document.getElementById('in2'),'jA','')")
        await pg.wait_for_function("DB.photos.length>=3", timeout=60000)
        await pg.wait_for_timeout(1500)
        ok(await pg.evaluate("DB.photos.length")==3, 'broken file skipped, other 3 stored (%s)' % await pg.evaluate("DB.photos.length"))
        ok(await pg.evaluate("__renders")==1, 'broken-file batch still renders once')

        # 3 stamp OFF path works too
        await pg.evaluate("localStorage.setItem('bp_stamp','0');DB.photos=[];window.__max=0")
        await pg.evaluate("window.__input('in3')")
        await pg.set_input_files('#in3', imgs[:5])
        await pg.evaluate("addPhotos(document.getElementById('in3'),'jA','')")
        await pg.wait_for_function("DB.photos.length>=5", timeout=60000)
        ok(await pg.evaluate("__max")==1, 'stamp off: still one at a time')
        ok(await pg.evaluate("DB.photos.every(p=>!p.roomId)"), 'no room when none given')

        # 4 two batches picked back to back both finish, in order, nothing lost
        await pg.evaluate("localStorage.setItem('bp_stamp','1');DB.photos=[];window.__max=0")
        await pg.evaluate("window.__input('in4a');window.__input('in4b')")
        await pg.set_input_files('#in4a', imgs[:3]); await pg.set_input_files('#in4b', imgs[3:6])
        await pg.evaluate("addPhotos(document.getElementById('in4a'),'jA','rA'); addPhotos(document.getElementById('in4b'),'jA','')")
        await pg.wait_for_function("DB.photos.length>=6", timeout=60000)
        ok(await pg.evaluate("__max")==1, 'overlapping batches share one queue')
        ok(await pg.evaluate("DB.photos.filter(p=>p.roomId==='rA').length")==3, 'each batch keeps its own room')

        # 5 persisted: reload keeps the photos
        await pg.wait_for_timeout(800)
        await pg.reload(); await pg.wait_for_timeout(2500)
        ok(await pg.evaluate("DB.photos.length")==6, 'photos survive reload (%s)' % await pg.evaluate("DB.photos.length"))

        # 6 checklist before/after photos: one at a time, one save
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("(function(){ DB.punchlist=DB.punchlist||[]; DB.punchlist.push({id:'pl1',jobId:'jA',text:'Patch wall',done:false,photosBefore:[],photosAfter:[]}); })()")
        await pg.evaluate(INSTR)
        await pg.evaluate("window.__input('in6')")
        await pg.set_input_files('#in6', imgs[:6])
        await pg.evaluate("addChecklistPhoto(document.getElementById('in6'),'pl1','before')")
        await pg.wait_for_function("DB.punchlist.find(x=>x.id==='pl1').photosBefore.length>=6", timeout=60000)
        await pg.wait_for_timeout(500)
        r = await pg.evaluate("({n:DB.punchlist.find(x=>x.id==='pl1').photosBefore.length,max:__max,saves:__saves})")
        ok(r['n']==6, 'checklist: 6 before photos stored (%s)' % r['n'])
        ok(r['max']==1, 'checklist: one at a time (%s)' % r['max'])
        ok(r['saves']==1, 'checklist: single save (%s)' % r['saves'])

        # 7 same-job big batch stays responsive: main thread not frozen (timer ticks during upload)
        await pg.evaluate("DB.photos=[];window.__ticks=0;setInterval(function(){window.__ticks++},50)")
        await pg.evaluate("window.__input('in7')")
        await pg.set_input_files('#in7', imgs)
        await pg.evaluate("addPhotos(document.getElementById('in7'),'jA','')")
        await pg.wait_for_function("DB.photos.length>=12", timeout=90000)
        ok(await pg.evaluate("__ticks")>20, 'UI thread keeps breathing during upload (ticks %s)' % await pg.evaluate("__ticks"))

        ok(not errs, 'no page errors: %s' % errs[:2])
        await b.close()
    finally:
        srv.terminate()
    print('%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
