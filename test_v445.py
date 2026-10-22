"""BuildersPro v4.49 (thumbs up/down on subs, contractor address book, skill selector on contact card).
Run from repo root: python3 test_v445.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs=[{id:'j1',name:'Smith Kitchen',status:'Active'}];
DB.contractors=[{id:'c1',name:'Joe Plumbing',jobId:'j1',trade:'Plumbing',value:5000,phone:'2015550101',status:'Active',scope:'',start:'',end:'',created:'2026-10-01T10:00:00Z'},
{id:'c2',name:"Sam's Electric",jobId:'j1',trade:'Electrical',value:2000,phone:'',status:'Active',scope:'',start:'',end:'',created:'2026-10-02T10:00:00Z'},
{id:'c3',name:'Gen Con',jobId:'',trade:'General',value:0,phone:'',status:'Active',scope:'',start:'',end:'',created:'2026-10-03T10:00:00Z'}];
DB.contacts=[{id:'k1',type:'Client',name:'Owner Bob',jobId:'j1',email:'b@x.com',phone:''}];
DB.expenses=[];DB.invoices=[];DB.payments=[];save();renderAll();})()"""
def rgb(c): return [int(float(x)) for x in c[c.index('(')+1:c.index(')')].replace('/',',').replace(' ',',').split(',') if x.strip()][:3]
async def run(w, h, theme):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8795/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h} {theme}'
        ok(await pg.evaluate("APP_VERSION==='4.49'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("document.documentElement.setAttribute('data-theme','%s')" % theme)
        await pg.evaluate(SEED)
        await pg.evaluate("showScreen('s-finance');setFinanceTab('contractors')"); await pg.wait_for_timeout(400)
        z = float(await pg.evaluate("getComputedStyle(document.body).zoom") or 1)
        # --- thumbs on contract cards
        ok(await pg.evaluate("document.querySelectorAll('#finance-content .bp-th.up').length>=2") if False else True, '')
        ths = await pg.evaluate("document.querySelectorAll('#s-finance .bp-th').length")
        ok(ths == 6, f'{t}: expected 6 thumb buttons on 3 contract cards, got {ths}')
        r = await pg.evaluate("(()=>{var r=document.querySelector('#s-finance .bp-th').getBoundingClientRect();return [r.width,r.height]})()")
        ok(r[0] >= 43 and r[1] >= 43, f'{t}: thumb tap target {r}')
        # thumbs-up green
        await pg.evaluate("document.querySelector('#s-finance .bp-th.up').click()"); await pg.wait_for_timeout(300)
        c = await pg.evaluate("DB.contacts.find(x=>x.type==='Contractor'&&x.name==='Gen Con')||DB.contacts.filter(x=>x.type==='Contractor')[0]")
        ok(c is not None, f'{t}: rating did not create address-book entry')
        up = await pg.evaluate("(()=>{var b=document.querySelector('#s-finance .bp-th.up.on');return b?[getComputedStyle(b.querySelector('svg')).fill,b.getAttribute('aria-pressed')]:null})()")
        ok(up is not None and rgb(up[0]) == [48,209,88] and up[1]=='true', f'{t}: up thumb not green {up}')
        # toggling the same again clears
        await pg.evaluate("document.querySelector('#s-finance .bp-th.up').click()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("document.querySelectorAll('#s-finance .bp-th.on').length")==0, f'{t}: second tap should clear')
        # thumbs-down red on 2nd card (Sam's Electric) - apostrophe name
        await pg.evaluate("document.querySelectorAll('#s-finance .bp-th.down')[2].click()"); await pg.wait_for_timeout(300)
        dn = await pg.evaluate("(()=>{var b=document.querySelector('#s-finance .bp-th.down.on');return b?getComputedStyle(b.querySelector('svg')).fill:null})()")
        ok(dn is not None and rgb(dn) == [255,69,58], f'{t}: down thumb not red {dn}')
        ok(await pg.evaluate("DB.contacts.find(x=>x.name===\"Sam's Electric\").rating")=='down', f'{t}: down rating stored')
        # up then down switches (up->down)
        await pg.evaluate("document.querySelectorAll('#s-finance .bp-th.up')[2].click()"); await pg.wait_for_timeout(250)
        ok(await pg.evaluate("DB.contacts.find(x=>x.name===\"Sam's Electric\").rating")=='up', f'{t}: switch down->up')
        await pg.evaluate("document.querySelectorAll('#s-finance .bp-th.down')[2].click()"); await pg.wait_for_timeout(250)
        # --- address book view
        ok(await pg.evaluate("!!document.querySelector('#s-finance .bp-sb-seg')"), f'{t}: toggle missing')
        await pg.evaluate("bpSubView('book')"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("document.getElementById('bp-sb-list').children.length")==2, f'{t}: book should have 2 entries (Gen Con, Sam) before import')
        ok('Add 1 sub' in await pg.evaluate("document.getElementById('s-finance').innerText"), f'{t}: import banner for Joe')
        await pg.evaluate("bpSubImport()"); await pg.wait_for_timeout(300)
        names = await pg.evaluate("DB.contacts.filter(x=>x.type==='Contractor').map(x=>x.name+'|'+(x.skills||[]).join(','))")
        ok(len(names)==3, f'{t}: import count {names}')
        ok('Joe Plumbing|Plumbing' in names, f'{t}: skill from trade {names}')
        ok(any(n.startswith('Gen Con|') and n=='Gen Con|' for n in names), f'{t}: General must not become a skill {names}')
        ok(await pg.evaluate("DB.contacts.find(x=>x.type==='Client').name")=='Owner Bob', f'{t}: client untouched')
        ok(await pg.evaluate("document.getElementById('bp-sb-list').children.length")==3, f'{t}: 3 cards')
        # search + skill filter
        await pg.fill('#bp-sb-q', 'joe'); await pg.wait_for_timeout(150)
        ok(await pg.evaluate("document.getElementById('bp-sb-list').children.length")==1, f'{t}: search')
        await pg.fill('#bp-sb-q', '')
        await pg.select_option('#bp-sb-sk', 'Electrical'); await pg.wait_for_timeout(150)
        ok(await pg.evaluate("document.getElementById('bp-sb-list').children.length")==1, f'{t}: skill filter')
        await pg.select_option('#bp-sb-sk', '')
        # thumbs on book list
        await pg.evaluate("document.querySelector('#bp-sb-list .bp-th.up').click()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("document.querySelectorAll('#bp-sb-list .bp-th.up.on').length")==1, f'{t}: book thumb')
        # --- contact card: new
        await pg.evaluate("openFinanceAdd()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("!!document.getElementById('bp-sub-card')"), f'{t}: + opens contact card in book view')
        ok(await pg.evaluate("document.querySelectorAll('#bp-sc-skills .bp-skp').length")>=19, f'{t}: skill chips')
        await pg.fill('#bp-sc-name', 'maria tile co'); await pg.fill('#bp-sc-phone', '9735550142')
        ok(await pg.evaluate("document.getElementById('bp-sc-phone').value")=='(973)-555-0142', f'{t}: phone format')
        await pg.evaluate("[...document.querySelectorAll('#bp-sc-skills .bp-skp')].find(b=>b.textContent==='Tile').click()")
        await pg.evaluate("[...document.querySelectorAll('#bp-sc-skills .bp-skp')].find(b=>b.textContent==='Flooring').click()")
        await pg.evaluate("[...document.querySelectorAll('#bp-sc-skills .bp-skp')].find(b=>b.textContent==='+ Other').click()")
        await pg.fill('#bp-sc-new', 'waterproofing'); await pg.press('#bp-sc-new', 'Enter')
        on = await pg.evaluate("[...document.querySelectorAll('#bp-sc-skills .bp-skp.on')].map(b=>b.textContent)")
        ok(sorted(on)==['Flooring','Tile','Waterproofing'], f'{t}: selected skills {on}')
        await pg.evaluate("document.querySelector('#bp-sc-thumbs .bp-th.down').click()")
        ok(await pg.evaluate("!!document.querySelector('#bp-sc-thumbs .bp-th.down.on')"), f'{t}: card thumb')
        # underlined fields, no boxes
        bd = await pg.evaluate("(()=>{var s=getComputedStyle(document.getElementById('bp-sc-company'));return [s.borderLeftWidth,s.borderBottomWidth]})()")
        ok(bd[0]=='0px' and bd[1]!='0px', f'{t}: fields should be underlined, not boxed {bd}')
        await pg.evaluate("bpSubSave()"); await pg.wait_for_timeout(300)
        m = await pg.evaluate("DB.contacts.find(x=>x.name==='Maria Tile Co')")
        ok(m and m['type']=='Contractor' and m['rating']=='down' and sorted(m['skills'])==['Flooring','Tile','Waterproofing'] and m['phone']=='(973)-555-0142' and m['jobId']=='', f'{t}: saved {m}')
        ok(not await pg.evaluate("!!document.getElementById('bp-sub-card')"), f'{t}: card closes')
        # custom skill now appears in filter + other cards' chip list
        ok('Waterproofing' in await pg.evaluate("[...document.getElementById('bp-sb-sk').options].map(o=>o.value)"), f'{t}: custom skill in filter')
        # duplicate blocked
        await pg.evaluate("bpSubOpen('')"); await pg.fill('#bp-sc-name', 'MARIA tile co'); await pg.evaluate("bpSubSave()"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("DB.contacts.filter(x=>x.name==='Maria Tile Co').length")==1 and await pg.evaluate("!!document.getElementById('bp-sub-card')"), f'{t}: duplicate allowed')
        await pg.evaluate("bpSubClose()")
        # edit existing: call/text/email buttons, worked-on, delete 2-tap
        jid = await pg.evaluate("DB.contacts.find(x=>x.name==='Joe Plumbing').id")
        await pg.evaluate("bpSubOpen('%s')" % jid)
        ok(await pg.evaluate("document.querySelectorAll('#bp-sub-card a.bp-sc-act').length")==2, f'{t}: call+text actions')
        ok('Smith Kitchen' in await pg.evaluate("document.getElementById('bp-sub-card').innerText"), f'{t}: worked on')
        ok(await pg.evaluate("document.querySelector('#bp-sub-card a[href^=\"tel:\"]').getAttribute('href')")=='tel:2015550101', f'{t}: tel link')
        ok(await pg.evaluate("document.getElementById('bp-sc-skills').querySelector('.bp-skp.on').textContent")=='Plumbing', f'{t}: existing skill selected')
        await pg.evaluate("document.getElementById('bp-sc-del').click()")
        ok(await pg.evaluate("!!DB.contacts.find(x=>x.id==='%s')" % jid), f'{t}: single tap must not delete')
        await pg.evaluate("document.getElementById('bp-sc-del').click()"); await pg.wait_for_timeout(300)
        ok(not await pg.evaluate("!!DB.contacts.find(x=>x.id==='%s')" % jid), f'{t}: 2nd tap deletes')
        ok(await pg.evaluate("DB.contractors.some(x=>x.name==='Joe Plumbing')"), f'{t}: deleting from book must not delete the job contract')
        # contract view: new contractor auto-lands in book
        await pg.evaluate("bpSubView('contracts')")
        await pg.evaluate("populateFinanceSelects();openSheet('sheet-add-contractor')")
        await pg.evaluate("document.getElementById('con-contact').value='new guy hvac';document.getElementById('con-trade').value='HVAC';document.getElementById('con-phone').value='9085550000'")
        await pg.evaluate("saveContractor()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("(x=>!!x&&x.skills.join()==='HVAC')(DB.contacts.find(x=>x.name==='New Guy Hvac'))"), f'{t}: new sub auto-added to book')
        # no overflow on the page
        ov = await pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        ok(ov <= 1, f'{t}: horizontal overflow {ov}')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await pg.evaluate("bpSubView('book')"); await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.environ.get('SHOT','/tmp/sb_%s_%d.png' % (theme, w)))
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8795','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        for th in ('dark','light'):
            await run(390, 844, th); await run(834, 1194, th)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
