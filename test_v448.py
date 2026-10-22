"""BuildersPro v4.48 (contact card top fields: Contact name, Company name, Email, Cell).
Run from repo root: python3 test_v448.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs=[{id:'j1',name:'Smith Kitchen',status:'Active'}];
DB.contractors=[{id:'c1',name:'Joe Rossi',jobId:'j1',trade:'Plumbing',value:5000,status:'Active'}];
DB.contacts=[{id:'k1',type:'Contractor',name:'Joe Rossi',company:'Rossi Plumbing LLC',phone:'2015550101',email:'joe@rossi.com',address:'',notes:'',skills:['Plumbing'],rating:'',jobId:''}];
DB.expenses=[];DB.invoices=[];DB.payments=[];save();renderAll();})()"""
async def run(w, h, theme):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8791/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h} {theme}'
        ok(await pg.evaluate("APP_VERSION==='4.48'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("document.documentElement.setAttribute('data-theme','%s')" % theme)
        await pg.evaluate(SEED); await pg.evaluate("bpSubOpen('k1')"); await pg.wait_for_timeout(300)
        labels = await pg.evaluate("[...document.querySelectorAll('#bp-sub-card .bp-sc-lbl')].map(e=>e.textContent.trim())")
        ok(labels[:4] == ['Contact name','Company name','Email','Cell'], f'{t}: top four labels {labels[:4]}')
        ok('Phone' not in labels and 'Contractor name' not in labels and 'Business name' not in labels, f'{t}: old labels gone {labels}')
        ys = await pg.evaluate("['bp-sc-name','bp-sc-company','bp-sc-email','bp-sc-phone'].map(i=>document.getElementById(i).getBoundingClientRect().top)")
        ok(ys == sorted(ys), f'{t}: order name, company, email, cell {ys}')
        sk = await pg.evaluate("document.getElementById('bp-sc-skills').getBoundingClientRect().top")
        ok(ys[3] < sk, f'{t}: four fields come before skills')
        vals = await pg.evaluate("['bp-sc-name','bp-sc-company','bp-sc-email','bp-sc-phone'].map(i=>document.getElementById(i).value)")
        ok(vals == ['Joe Rossi','Rossi Plumbing LLC','joe@rossi.com','(201)-555-0101'], f'{t}: values {vals}')
        ok(await pg.evaluate("document.getElementById('bp-sc-phone').type")=='tel' and await pg.evaluate("document.getElementById('bp-sc-email').type")=='email', f'{t}: input types')
        ok(await pg.evaluate("document.querySelectorAll('#bp-sub-card a.bp-sc-act').length")==3, f'{t}: call, text, email buttons')
        ok(await pg.evaluate("!!document.getElementById('bp-sc-address')&&!!document.getElementById('bp-sc-notes')"), f'{t}: address and notes kept')
        # edit + save round trip
        await pg.fill('#bp-sc-email', 'new@rossi.com'); await pg.fill('#bp-sc-phone', '9735550142')
        await pg.evaluate("bpSubSave()"); await pg.wait_for_timeout(200)
        r = await pg.evaluate("(x=>[x.email,x.phone,x.company])(DB.contacts.find(x=>x.id==='k1'))")
        ok(r == ['new@rossi.com','(973)-555-0142','Rossi Plumbing LLC'], f'{t}: saved {r}')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await br_close(b)
async def br_close(b): await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8791','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        for th in ('dark','light'):
            await run(390, 844, th); await run(834, 1194, th)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
