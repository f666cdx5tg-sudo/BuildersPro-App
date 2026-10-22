"""BuildersPro v4.50 (contact card: contractor name + business name, contract value per job).
Run from repo root: python3 test_v447.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs=[{id:'j1',name:'Smith Kitchen',status:'Active'},{id:'j2',name:'N. Peach St',status:'Active'}];
DB.contractors=[{id:'c1',name:'Joe Rossi',jobId:'j1',trade:'Plumbing',value:5000,status:'Active'},
{id:'c2',name:'Rossi Plumbing LLC',jobId:'j2',trade:'Plumbing',value:12000,status:'Pending'},
{id:'c3',name:'Someone Else',jobId:'j1',trade:'Tile',value:900,status:'Active'}];
DB.payments=[{id:'p1',contractorId:'c1',amount:2000,date:'2026-10-01'},{id:'p2',contractorId:'c1',amount:500,date:'2026-10-05'},{id:'p3',contractorId:'c2',amount:12000,date:'2026-10-09'}];
DB.contacts=[{id:'k1',type:'Contractor',name:'Joe Rossi',company:'Rossi Plumbing LLC',phone:'',email:'',address:'',notes:'',skills:['Plumbing'],rating:'',jobId:''}];
DB.expenses=[];DB.invoices=[];save();renderAll();})()"""
async def run(w, h, theme):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8793/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h} {theme}'
        ok(await pg.evaluate("APP_VERSION==='4.50'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("document.documentElement.setAttribute('data-theme','%s')" % theme)
        await pg.evaluate(SEED)
        await pg.evaluate("showScreen('s-finance');setFinanceTab('contractors')"); await pg.wait_for_timeout(300)
        # only Someone Else is missing from the book (Joe Rossi + Rossi Plumbing LLC both match the one card)
        ok(await pg.evaluate("document.querySelectorAll('#bp-sb-list .bp-ub').length")==2, f'{t}: Joe + Rossi Plumbing LLC contracts share ONE card, plus Someone Else')
        await pg.evaluate("bpSubOpen('k1')"); await pg.wait_for_timeout(200)
        txt = await pg.evaluate("document.getElementById('bp-sub-card').innerText")
        ok('CONTACT NAME' in txt.upper() and 'COMPANY NAME' in txt.upper(), f'{t}: labels')
        ok(await pg.evaluate("document.getElementById('bp-sc-name').value")=='Joe Rossi' and await pg.evaluate("document.getElementById('bp-sc-company').value")=='Rossi Plumbing LLC', f'{t}: values')
        order = await pg.evaluate("(()=>{var a=document.getElementById('bp-sc-name').getBoundingClientRect().top,b=document.getElementById('bp-sc-company').getBoundingClientRect().top,c=document.getElementById('bp-sc-phone').getBoundingClientRect().top;return a<b&&b<c})()")
        ok(order, f'{t}: business name sits right under name')
        ok('CONTRACT VALUE BY JOB' in txt.upper(), f'{t}: jobs section')
        ok('Smith Kitchen' in txt and 'N. Peach St' in txt, f'{t}: both jobs listed')
        ok('$5,000' in txt and '$12,000' in txt and 'Someone Else' not in txt and '$900' not in txt, f'{t}: values {txt!r}')
        ok('Paid $2,500' in txt and 'Left $2,500' in txt, f'{t}: job 1 paid/left')
        ok('Paid $12,000' in txt and 'Left $0' in txt, f'{t}: job 2 paid/left')
        ok('All jobs' in txt and '$17,000' in txt and 'Paid $14,500' in txt and 'Left $2,500' in txt, f'{t}: totals')
        lc = await pg.evaluate("(()=>{var x=[...document.querySelectorAll('#bp-sub-card span')].find(e=>/^Left \\$2,500/.test(e.textContent)&&e.children.length==0);return x?getComputedStyle(x).color:null})()")
        ok(lc=='rgb(255, 159, 10)', f'{t}: money still owed is orange {lc}')
        # card with no contracts
        await pg.evaluate("bpSubClose();DB.contacts.push({id:'k2',type:'Contractor',name:'Lone Wolf',skills:[]});bpSubOpen('k2')")
        ok('No job contracts yet' in await pg.evaluate("document.getElementById('bp-sub-card').innerText"), f'{t}: empty jobs state')
        await pg.screenshot(path='/tmp/vc_%s_%d.png' % (theme, w))
        # save business name
        await pg.evaluate("bpSubClose();bpSubOpen('k1')")
        await pg.fill('#bp-sc-company', 'rossi plumbing & heating'); await pg.evaluate("bpSubSave()"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate("DB.contacts.find(x=>x.id==='k1').company")=='rossi plumbing & heating', f'{t}: business saved')
        # rating from the 'Rossi Plumbing LLC' contract no longer matches renamed business, but Joe Rossi contract still does
        await pg.evaluate("renderFinance()"); await pg.wait_for_timeout(200)
        # contract sheet: datalist with names + business names, no dup entries
        await pg.evaluate("populateFinanceSelects();openSheet('sheet-add-contractor')")
        opts = await pg.evaluate("[...document.querySelectorAll('#dl-subs option')].map(o=>o.value)")
        ok('Joe Rossi' in opts and 'rossi plumbing & heating' in opts, f'{t}: datalist {opts}')
        ok(await pg.evaluate("document.getElementById('con-contact').getAttribute('list')")=='dl-subs', f'{t}: input uses datalist')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8793','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        for th in ('dark','light'):
            await run(390, 844, th); await run(834, 1194, th)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
