"""BuildersPro v3.79: photos of QR codes / barcodes on a job's Security entries.
Run from repo root: python3 test_v379.py /path/to/test.png (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); IMG = sys.argv[1] if len(sys.argv) > 1 else '/tmp/fakeqr.png'
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
async def run(w, h):
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await (await b.new_context(viewport={'width':w,'height':h})).new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto('http://localhost:8799/index.html'); await pg.wait_for_timeout(2500); t = f'{w}x{h}'
        ok(await pg.evaluate("parseFloat(APP_VERSION)>=3.79"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("(()=>{DB.jobs=[{id:'j1',name:'Shedwick',status:'Active'},{id:'j2',name:'Peach',status:'Active'}];DB.photos=[];save();renderAll();openJobDetail('j1');})()")
        await pg.wait_for_timeout(300)
        await pg.evaluate("document.querySelector('#jd-security-section > div').click()")
        await pg.evaluate("bpSecAdd('j1')"); await pg.wait_for_timeout(200)
        await pg.evaluate("document.getElementById('bpsec-label').value='Gate keypad QR'")
        await pg.set_input_files('#bp-sec-modal input[type=file]', [IMG, IMG]); await pg.wait_for_timeout(1500)
        ok(await pg.evaluate("document.querySelectorAll('#bpsec-ph img').length")==2, f'{t}: two thumbnails in form')
        await pg.evaluate("bpSecDropPhoto(1)")
        ok(await pg.evaluate("document.querySelectorAll('#bpsec-ph img').length")==1, f'{t}: remove photo')
        await pg.evaluate("bpSecSave()"); await pg.wait_for_timeout(400)   # photo-only entry (no code) must save
        sec = await pg.evaluate("DB.jobs.find(j=>j.id==='j1').security")
        ok(len(sec)==1 and len(sec[0]['photos'])==1 and sec[0]['photos'][0].startswith('data:image'), f'{t}: saved photo on entry')
        ok(await pg.evaluate("DB.photos.length")==0, f'{t}: NOT added to the Photos gallery')
        ok(await pg.evaluate("!document.querySelector('[data-sec-val]')"), f'{t}: no empty code row for photo-only entry')
        ok(await pg.evaluate("document.querySelectorAll('#jd-security-section img').length")==1, f'{t}: thumbnail on card')
        await pg.evaluate("document.querySelector('#jd-security-section img').click()"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("!!document.querySelector('#bp-sec-view img')"), f'{t}: viewer opens')
        ok(await pg.evaluate("getComputedStyle(document.getElementById('bp-sec-view')).backgroundColor")=='rgb(255, 255, 255)', f'{t}: white scan background')
        await pg.evaluate("bpSecViewClose()")
        ok(await pg.evaluate("!document.getElementById('bp-sec-view')"), f'{t}: viewer closes')
        # edit keeps photos; add a second entry with code + photo
        await pg.evaluate("bpSecEdit('j1', DB.jobs.find(j=>j.id==='j1').security[0].id)"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("document.querySelectorAll('#bpsec-ph img').length")==1, f'{t}: edit loads existing photo')
        await pg.evaluate("bpSecClose()")
        # sync split/join round-trips nested photo
        ok(await pg.evaluate("(()=>{var bl={};var lean=bpSplitBlobs(DB,bl);var back=bpJoinBlobs(JSON.parse(JSON.stringify(lean)),bl);return back.jobs[0].security[0].photos[0]===DB.jobs[0].security[0].photos[0]&&JSON.stringify(lean).indexOf('data:image')<0})()"), f'{t}: sync split/join keeps photo')
        # isolation + duplicate
        await pg.evaluate("openJobDetail('j2')"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("document.querySelectorAll('#s-job-detail #jd-security-section img').length")==0, f'{t}: other job has none')
        await pg.evaluate("duplicateJob('j1')"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("!DB.jobs.find(j=>/Copy/.test(j.name)).security"), f'{t}: duplicate drops photos')
        ok(await pg.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"), f'{t}: no horizontal scroll')
        ok(not errs, f'{t}: page errors {errs}')
        await b.close()
srv = subprocess.Popen([sys.executable,'-m','http.server','8799','--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
    for w,h in [(390,844),(1024,768)]: asyncio.run(run(w,h))
finally: srv.terminate()
print(f'{checks} checks, {len(fails)} failed'); sys.exit(1 if fails else 0)
