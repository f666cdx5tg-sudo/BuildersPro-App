"""BuildersPro v4.53 (Add/Edit Contractor sheets: Contact name, Company name, Email, Cell, synced to the address book).
Run from repo root: python3 test_v449.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs=[{id:'j1',name:'N. Peach St',status:'Active'},{id:'j2',name:'Smith Kitchen',status:'Active'}];
DB.contractors=[{id:'c1',name:'Ali/Alycraft LLc',jobId:'j1',trade:'Plumbing',value:8500,phone:'2015550199',status:'Active',scope:'All new roughing'},
{id:'c2',name:'Joe Rossi',jobId:'j2',trade:'Tile',value:900,status:'Active'}];
DB.contacts=[{id:'k1',type:'Contractor',name:'Joe Rossi',company:'Rossi Tile Inc',phone:'9735550142',email:'joe@rossi.com',address:'',notes:'',skills:['Tile'],rating:'up',jobId:''}];
DB.expenses=[];DB.invoices=[];DB.payments=[];save();renderAll();})()"""
async def run(w, h, theme):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8790/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h} {theme}'
        ok(await pg.evaluate("APP_VERSION==='4.53'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("document.documentElement.setAttribute('data-theme','%s')" % theme)
        await pg.evaluate(SEED)
        # ---- EDIT sheet
        await pg.evaluate("openEditContractor('c1')"); await pg.wait_for_timeout(300)
        labels = await pg.evaluate("[...document.querySelectorAll('#edit-con-modal div')].filter(d=>d.children.length===0&&d.style.textTransform==='uppercase').map(d=>d.textContent.trim())")
        ok(labels[:4] == ['Contact name','Company name','Email','Cell'], f'{t}: edit labels {labels[:4]}')
        ok(await pg.evaluate("!document.getElementById('ec-name')"), f'{t}: old single Name field gone')
        v = await pg.evaluate("['ec-contact','ec-company','ec-email','ec-phone'].map(i=>document.getElementById(i).value)")
        ok(v == ['', 'Ali/Alycraft LLc', '', '(201)-555-0199'], f'{t}: legacy name goes to Company {v}')
        ys = await pg.evaluate("['ec-contact','ec-company','ec-email','ec-phone','ec-job'].map(i=>document.getElementById(i).getBoundingClientRect().top)")
        ok(ys == sorted(ys), f'{t}: order contact, company, email, cell, job {ys}')
        await pg.fill('#ec-contact', 'ali khan'); await pg.fill('#ec-email', 'ali@alycraft.com')
        await pg.evaluate("saveEditContractor('c1')"); await pg.wait_for_timeout(250)
        c = await pg.evaluate("DB.contractors.find(x=>x.id==='c1')")
        ok(c['name']=='Ali/Alycraft LLc' and c['contact']=='ali khan' and c['company']=='Ali/Alycraft LLc' and c['email']=='ali@alycraft.com', f'{t}: contract saved {c}')
        bk = await pg.evaluate("DB.contacts.find(x=>x.name==='ali khan')")
        ok(bk and bk['company']=='Ali/Alycraft LLc' and bk['email']=='ali@alycraft.com' and bk['phone']=='(201)-555-0199' and 'Plumbing' in bk['skills'], f'{t}: book entry created {bk}')
        # reopen -> values stick, no duplicate book entry
        await pg.evaluate("openEditContractor('c1')"); await pg.wait_for_timeout(200)
        v = await pg.evaluate("['ec-contact','ec-company','ec-email'].map(i=>document.getElementById(i).value)")
        ok(v == ['ali khan','Ali/Alycraft LLc','ali@alycraft.com'], f'{t}: reopen {v}')
        await pg.evaluate("saveEditContractor('c1')"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("DB.contacts.filter(x=>x.type==='Contractor').length")==2, f'{t}: no duplicate on re-save')
        # edit a legacy contract whose person is already in the book -> pulls company/email from the book
        await pg.evaluate("openEditContractor('c2')"); await pg.wait_for_timeout(200)
        v = await pg.evaluate("['ec-contact','ec-company','ec-email'].map(i=>document.getElementById(i).value)")
        ok(v == ['Joe Rossi','Rossi Tile Inc','joe@rossi.com'], f'{t}: legacy contract filled from book {v}')
        # clear both names -> blocked
        await pg.fill('#ec-contact', ''); await pg.fill('#ec-company', '')
        await pg.evaluate("saveEditContractor('c2')"); await pg.wait_for_timeout(150)
        ok(await pg.evaluate("!!document.getElementById('edit-con-modal')"), f'{t}: needs a name')
        await pg.fill('#ec-company', 'Rossi Tile Inc'); await pg.evaluate("saveEditContractor('c2')"); await pg.wait_for_timeout(250)
        c2 = await pg.evaluate("DB.contractors.find(x=>x.id==='c2')")
        ok(c2['name']=='Rossi Tile Inc' and c2['contact']=='', f'{t}: company-only contract {c2}')
        ok(await pg.evaluate("DB.contacts.filter(x=>x.type==='Contractor').length")==2, f'{t}: still 2 book entries after rename')
        ok(await pg.evaluate("DB.contacts.find(x=>x.id==='k1').rating")=='up', f'{t}: rating survives')
        # ---- ADD sheet
        await pg.evaluate("populateFinanceSelects();openSheet('sheet-add-contractor')"); await pg.wait_for_timeout(300)
        lab = await pg.evaluate("[...document.querySelectorAll('#sheet-add-contractor .field-label')].slice(0,5).map(e=>e.textContent.trim())")
        ok(lab == ['Contact name','Company name','Email','Cell','Job'], f'{t}: add labels {lab}')
        ok(await pg.evaluate("document.querySelectorAll('#sheet-add-contractor #con-phone').length")==1, f'{t}: one Cell field')
        # picking an address-book name fills the rest
        await pg.fill('#con-contact', 'Joe Rossi'); await pg.evaluate("bpSubFillAdd()")
        v = await pg.evaluate("['con-contact','con-company','con-email','con-phone','con-trade'].map(i=>document.getElementById(i).value)")
        ok(v == ['Joe Rossi','Rossi Tile Inc','joe@rossi.com','(973)-555-0142','Tile'], f'{t}: autofill from book {v}')
        await pg.select_option('#con-job', 'j1'); await pg.fill('#con-value', '4200')
        await pg.evaluate("saveContractor()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("DB.contractors.filter(x=>x.company==='Rossi Tile Inc').length")==2, f'{t}: second job contract for same sub')
        ok(await pg.evaluate("DB.contacts.filter(x=>x.type==='Contractor').length")==2, f'{t}: add did not duplicate the book entry')
        ok(await pg.evaluate("document.getElementById('con-contact').value==''&&document.getElementById('con-email').value==''"), f'{t}: sheet cleared after save')
        # company-only add
        await pg.evaluate("populateFinanceSelects();openSheet('sheet-add-contractor')")
        await pg.fill('#con-company', 'Brooklyn Electric Co'); await pg.fill('#con-email', 'info@bke.com'); await pg.fill('#con-phone', '7185550100')
        await pg.evaluate("saveContractor()"); await pg.wait_for_timeout(300)
        bk = await pg.evaluate("DB.contacts.find(x=>x.name==='Brooklyn Electric Co')")
        ok(bk and bk['email']=='info@bke.com' and bk['phone']=='(718)-555-0100', f'{t}: company-only book entry {bk}')
        # nothing entered -> blocked
        await pg.evaluate("populateFinanceSelects();openSheet('sheet-add-contractor')"); n = await pg.evaluate("DB.contractors.length")
        await pg.evaluate("saveContractor()"); await pg.wait_for_timeout(150)
        ok(await pg.evaluate("DB.contractors.length")==n, f'{t}: empty save blocked')
        # card: contract value by job shows both Rossi contracts under the person
        await pg.evaluate("closeSheet('sheet-add-contractor')")
        await pg.evaluate("bpSubOpen('k1')"); await pg.wait_for_timeout(250)
        txt = await pg.evaluate("document.getElementById('bp-sub-card').innerText")
        ok('Smith Kitchen' in txt and 'N. Peach St' in txt and '$900' in txt and '$4,200' in txt and '$5,100' in txt, f'{t}: per-job values {txt[:400]!r}')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8790','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        for th in ('dark','light'):
            await run(390, 844, th); await run(834, 1194, th)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
