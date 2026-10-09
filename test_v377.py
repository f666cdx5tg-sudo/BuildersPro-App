"""BuildersPro v3.77: per-job Security section (door codes, Wi-Fi, cameras).
Run from repo root: python3 test_v377.py (needs playwright + chromium). Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
async def run(w, h):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width':w,'height':h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto('http://localhost:8799/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h}'
        ok(await pg.evaluate("APP_VERSION==='3.77'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("(()=>{DB.jobs=[{id:'j1',name:'Shedwick',status:'Active'},{id:'j2',name:'Peach',status:'Active'}];save();renderAll();})()")
        await pg.evaluate("openJobDetail('j1')"); await pg.wait_for_timeout(400)
        ok(await pg.evaluate("!!document.getElementById('jd-security-section')"), f'{t}: section present')
        await pg.evaluate("document.querySelector('#jd-security-section > div').click()"); await pg.wait_for_timeout(200)
        ok('No codes yet' in await pg.evaluate("document.getElementById('jd-security-section').innerText"), f'{t}: empty state')
        # add a door code
        await pg.evaluate("bpSecAdd('j1')"); await pg.wait_for_timeout(200)
        await pg.evaluate("document.getElementById('bpsec-label').value='Front door';document.getElementById('bpsec-secret').value='4821#'")
        await pg.evaluate("bpSecSave()"); await pg.wait_for_timeout(300)
        # add wifi (has network name field)
        await pg.evaluate("bpSecAdd('j1')"); await pg.wait_for_timeout(200)
        await pg.evaluate("var s=document.getElementById('bpsec-kind');s.value='wifi';bpSecKindChange()")
        ok(await pg.evaluate("document.getElementById('bpsec-user-wrap').style.display!=='none'"), f'{t}: wifi shows network field')
        await pg.evaluate("document.getElementById('bpsec-label').value='Router';document.getElementById('bpsec-user').value='Shed_Net';document.getElementById('bpsec-secret').value='hunter2'")
        await pg.evaluate("bpSecSave()"); await pg.wait_for_timeout(300)
        sec = await pg.evaluate("DB.jobs.find(j=>j.id==='j1').security")
        ok(len(sec)==2 and sec[0]['secret']=='4821#' and sec[1]['user']=='Shed_Net', f'{t}: saved {sec}')
        txt = await pg.evaluate("document.getElementById('jd-security-section').innerText")
        ok('4821' not in txt and 'hunter2' not in txt, f'{t}: secrets masked')
        ok('Shed_Net' in txt and 'Front door' in txt, f'{t}: labels shown')
        await pg.evaluate("document.querySelector('[data-sec-val]').click()")
        ok('4821#' in await pg.evaluate("document.querySelector('[data-sec-val]').textContent"), f'{t}: tap reveals')
        # no horizontal overflow
        ok(await pg.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"), f'{t}: no horizontal scroll')
        # isolation: other job has none
        await pg.evaluate("openJobDetail('j2')"); await pg.wait_for_timeout(300)
        ok('4821' not in await pg.evaluate("document.getElementById('s-job-detail').innerText"), f'{t}: other job isolated')
        # duplicate does not copy codes
        await pg.evaluate("duplicateJob('j1')"); await pg.wait_for_timeout(300)
        cp = await pg.evaluate("DB.jobs.find(j=>/Copy/.test(j.name))")
        ok(cp and not cp.get('security'), f'{t}: duplicate must not copy security')
        # edit + delete
        await pg.evaluate("openJobDetail('j1')"); await pg.wait_for_timeout(300)
        await pg.evaluate("bpSecEdit('j1', DB.jobs.find(j=>j.id==='j1').security[0].id)"); await pg.wait_for_timeout(200)
        await pg.evaluate("document.getElementById('bpsec-secret').value='9999';bpSecSave()"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("DB.jobs.find(j=>j.id==='j1').security[0].secret")=='9999', f'{t}: edit')
        await pg.evaluate("bpSecEdit('j1', DB.jobs.find(j=>j.id==='j1').security[0].id)"); await pg.evaluate("bpSecDelete()")
        ok(await pg.evaluate("DB.jobs.find(j=>j.id==='j1').security.length")==1, f'{t}: delete')
        ok(not errs, f'{t}: page errors {errs}')
        await b.close()
srv = subprocess.Popen([sys.executable,'-m','http.server','8799','--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
try:
    for w,h in [(390,844),(1024,768)]: asyncio.run(run(w,h))
finally: srv.terminate()
print(f'{checks} checks, {len(fails)} failed'); sys.exit(1 if fails else 0)
