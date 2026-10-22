"""BuildersPro v4.52 (contractors + phone book are one list; Tools heading in the side menu).
Run from repo root: python3 test_v450.py. Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__))
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    if not c: fails.append(m); print('  FAIL', m)
SEED = """(()=>{DB.jobs=[{id:'j1',name:'N. Peach St',status:'Active'},{id:'j2',name:'Smith Kitchen',status:'Active'}];
DB.contractors=[{id:'c1',name:'Rossi Plumbing LLC',contact:'Joe Rossi',company:'Rossi Plumbing LLC',jobId:'j1',trade:'Plumbing',value:8500,phone:'2015550199',status:'Active',scope:'All new roughing',start:'2026-10-01',end:'2026-11-01'},
{id:'c2',name:'Rossi Plumbing LLC',contact:'Joe Rossi',company:'Rossi Plumbing LLC',jobId:'j2',trade:'Plumbing',value:3000,status:'Pending'},
{id:'c3',name:'Brooklyn Electric',jobId:'j1',trade:'Electrical',value:2000,status:'Active'}];
DB.payments=[{id:'p1',contractorId:'c1',amount:2000,date:'2026-10-05',method:'Check'}];
DB.contacts=[{id:'k1',type:'Contractor',name:'Joe Rossi',company:'Rossi Plumbing LLC',phone:'2015550199',email:'joe@rossi.com',address:'',notes:'',skills:['Plumbing'],rating:'up',jobId:''},
{id:'k2',type:'Contractor',name:'Pat Painter',company:'',phone:'',email:'',address:'',notes:'',skills:['Painting'],rating:'',jobId:''}];
DB.expenses=[];DB.invoices=[];save();renderAll();})()"""
async def run(w, h, theme):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': w, 'height': h}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8789/index.html'); await pg.wait_for_timeout(2500)
        t = f'{w}x{h} {theme}'
        ok(await pg.evaluate("APP_VERSION==='4.52'"), f'{t}: version')
        await pg.evaluate("document.getElementById('bp-lock')?.remove()")
        await pg.evaluate("document.documentElement.setAttribute('data-theme','%s')" % theme)
        # ---- drawer: Tools heading
        order = await pg.evaluate("[...document.querySelectorAll('#bp-drawer > *')].map(e=>e.id||(e.className.indexOf('bp-drawer-h')>-1?'HEAD:'+e.textContent.trim():e.className.indexOf('sep')>-1?'sep':e.tagName))")
        ok('HEAD:Tools' in order, f'{t}: Tools heading present {order}')
        i = order.index('HEAD:Tools') if 'HEAD:Tools' in order else -1
        ok(order[i+1:i+3] == ['nav-level','nav-colormatch'], f'{t}: Level and Paint match directly under Tools {order[i:i+4]}')
        ok(order.index('nav-s-calendar') < i and order.index('bp-sync-btn') < i, f'{t}: Tools group after the general buttons')
        ok('Paint match' in await pg.evaluate("document.getElementById('nav-colormatch').textContent"), f'{t}: renamed Paint match')
        hc = await pg.evaluate("getComputedStyle(document.querySelector('.bp-drawer-h')).textTransform")
        ok(hc == 'uppercase', f'{t}: heading style {hc}')
        # ---- unified list
        await pg.evaluate(SEED)
        await pg.evaluate("showScreen('s-finance');setFinanceTab('contractors')"); await pg.wait_for_timeout(400)
        ok(await pg.evaluate("document.querySelectorAll('#s-finance .bp-sb-seg').length")==0, f'{t}: toggle gone')
        cards = await pg.evaluate("[...document.querySelectorAll('#bp-sb-list .bp-ub')].map(c=>c.querySelector('div div div').textContent)")
        ok(len(cards)==3, f'{t}: 3 cards (Joe, Pat, Brooklyn) {cards}')
        ok(cards == sorted(cards, key=str.lower), f'{t}: alphabetical {cards}')
        joe = await pg.evaluate("[...document.querySelectorAll('#bp-sb-list .bp-ub')].find(c=>c.innerText.includes('Joe Rossi')).innerText")
        ok('$8,500' in joe and '$3,000' in joe and '$11,500' in joe and 'All jobs' in joe, f'{t}: Joe card has both jobs + total {joe!r}')
        ok('N. Peach St' in joe and 'Smith Kitchen' in joe, f'{t}: job names')
        ok('Paid $2,000' in joe and 'Left $6,500' in joe, f'{t}: paid/left per job')
        ok('All new roughing' in joe and 'Check' in joe, f'{t}: scope + payment history kept')
        ok('(201)-555-0199' in joe and 'Plumbing' in joe, f'{t}: cell + skills on card')
        pat = await pg.evaluate("[...document.querySelectorAll('#bp-sb-list .bp-ub')].find(c=>c.innerText.includes('Pat Painter')).innerText")
        ok('No job contracts yet' in pat, f'{t}: phone-book-only person shows')
        ok('Total Sub Costs: $13,500' in await pg.evaluate("document.getElementById('bp-sb-list').innerText"), f'{t}: total')
        ok(await pg.evaluate("document.querySelectorAll('#bp-sb-list .bp-th').length")==6, f'{t}: thumbs on every card')
        # contract buttons work
        ok(await pg.evaluate("document.querySelectorAll('#bp-sb-list button[onclick*=\"openLogPayment\"]').length")==3, f'{t}: + Payment per contract')
        await pg.evaluate("document.querySelector('#bp-sb-list button[onclick*=\"openEditContractor(\\'c3\"]').click()"); await pg.wait_for_timeout(250)
        ok(await pg.evaluate("!!document.getElementById('edit-con-modal')"), f'{t}: Edit opens')
        await pg.evaluate("document.getElementById('edit-con-modal').remove()")
        # tap card header -> contact card
        await pg.evaluate("[...document.querySelectorAll('#bp-sb-list .bp-ub')][1].children[0].click()"); await pg.wait_for_timeout(250)
        ok(await pg.evaluate("!!document.getElementById('bp-sub-card')"), f'{t}: header opens contact card')
        ok('$8,500' in await pg.evaluate("document.getElementById('bp-sub-card').innerText"), f'{t}: card shows contract values')
        await pg.evaluate("bpSubClose()")
        # thumbs
        await pg.evaluate("document.querySelector('#bp-sb-list .bp-th.down').click()"); await pg.wait_for_timeout(250)
        ok(await pg.evaluate("document.querySelectorAll('#bp-sb-list .bp-th.down.on').length")==1, f'{t}: thumb down')
        # search + skill filters across contacts AND contracts
        await pg.fill('#bp-sb-q', 'peach'); await pg.wait_for_timeout(150)
        ok(await pg.evaluate("document.querySelectorAll('#bp-sb-list .bp-ub').length")==0, f'{t}: job names are not searched (no match)')
        await pg.fill('#bp-sb-q', 'rossi'); await pg.wait_for_timeout(150)
        ok(await pg.evaluate("document.querySelectorAll('#bp-sb-list .bp-ub').length")==1, f'{t}: search by company')
        await pg.fill('#bp-sb-q', '')
        await pg.select_option('#bp-sb-sk', 'Painting'); await pg.wait_for_timeout(150)
        ok(await pg.evaluate("document.querySelectorAll('#bp-sb-list .bp-ub').length")==1, f'{t}: skill filter')
        await pg.select_option('#bp-sb-sk', '')
        # job filter (All Jobs select) -> only that job's contracts and only subs on it
        await pg.evaluate("document.getElementById('finance-job-filter') && 0")
        ok(await pg.evaluate("typeof bpSubUnifiedHtml==='function'"), f'{t}: unified builder')
        html = await pg.evaluate("bpSubUnifiedHtml('j2')")
        ok('$3,000' in html and '$8,500' not in html and 'Brooklyn' not in html and 'Pat Painter' not in html, f'{t}: job filter hides other jobs/subs')
        await pg.evaluate("renderFinance()")
        # ---- add to a job prefill
        await pg.evaluate("[...document.querySelectorAll('#bp-sb-list .bp-ub')].find(c=>c.innerText.includes('Pat Painter')).querySelector('button[onclick*=\"bpSubAddJob\"]').click()"); await pg.wait_for_timeout(300)
        v = await pg.evaluate("['con-contact','con-company','con-trade','con-value'].map(i=>document.getElementById(i).value)")
        ok(v == ['Pat Painter','','Painting',''], f'{t}: add-to-job prefill {v}')
        await pg.select_option('#con-job', 'j2'); await pg.fill('#con-value', '1800')
        await pg.evaluate("saveContractor()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("DB.contacts.filter(x=>x.type==='Contractor').length")==3, f'{t}: no duplicate person (Joe, Pat, Brooklyn)')
        pat = await pg.evaluate("[...document.querySelectorAll('#bp-sb-list .bp-ub')].find(c=>c.innerText.includes('Pat Painter')).innerText")
        ok('$1,800' in pat and 'Smith Kitchen' in pat, f'{t}: new contract nested under Pat {pat!r}')
        # ---- contact-only add (no job, no value) saves only to the phone book
        await pg.evaluate("populateFinanceSelects();openSheet('sheet-add-contractor')")
        await pg.fill('#con-contact', 'Dana Drywall'); await pg.fill('#con-phone', '9735551212')
        n = await pg.evaluate("DB.contractors.length")
        await pg.evaluate("saveContractor()"); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("DB.contractors.length")==n, f'{t}: contact-only add makes no empty contract')
        ok(await pg.evaluate("!!DB.contacts.find(x=>x.name==='Dana Drywall')"), f'{t}: contact-only add reaches the book')
        ok('Dana Drywall' in await pg.evaluate("document.getElementById('bp-sb-list').innerText"), f'{t}: and shows in the list')
        # every contract is claimed exactly once
        ids = await pg.evaluate("[...document.querySelectorAll('#bp-sb-list button[onclick*=\"openLogPayment\"]')].map(b=>b.getAttribute('onclick'))")
        ok(len(ids)==len(set(ids)) and len(ids)==4, f'{t}: no contract listed twice {len(ids)}')
        ov = await pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        ok(ov <= 1, f'{t}: horizontal overflow {ov}')
        ok(len(errs)==0, f'{t}: errors {errs[:3]}')
        await pg.evaluate("renderFinance()"); await pg.wait_for_timeout(200)
        await pg.screenshot(path='/tmp/u450_%s_%d.png' % (theme, w))
        await b.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server','8789','--directory',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        for th in ('dark','light'):
            await run(390, 844, th); await run(834, 1194, th)
    finally: srv.terminate()
    print(f'{checks-len(fails)}/{checks} passed'); sys.exit(1 if fails else 0)
asyncio.run(main())
