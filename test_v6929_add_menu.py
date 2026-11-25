"""v6.9.29 — fewer taps: on Home and the Money overview the dock's blue + opens an Add menu
(Expense, Pay a sub, Change order, Punch item, Photo, Invoice) with the On Site job filled in.
Other screens keep their own +. Mac Command Center: version only.
Run from repo root: python3 test_v6929_add_menu.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, re
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8929
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic','jsdelivr')
SEED = """() => { var t = new Date().toISOString();
 DB.jobs = [{id:'jA',name:'N. Peach Street Full Gut Renovation',status:'Active',client:'HRLM2 Philly LLC',address:'1536 N Peach St',contract:85000,created:t},
            {id:'jB',name:'Oak Ave Bathroom',status:'Active',client:'Other',address:'12 Oak Ave',contract:40000,created:t}];
 DB.contractors = [{id:'cP',name:'Ace Plumbing',jobId:'jA',trade:'Plumbing',value:12500,status:'Active',created:t},
                   {id:'cE',name:'Bright Electric',jobId:'jA',trade:'Electrical',value:9800.75,status:'Active',created:t},
                   {id:'cB',name:'Oak Tile Co',jobId:'jB',trade:'Tile',value:10000,status:'Active',created:t}];
 DB.payments = [{id:'p1',contractorId:'cP',jobId:'jA',amount:5000,date:t.slice(0,10),created:t}];
 try { save(); } catch(e) {} }"""
EMOJI = re.compile('[\U0001F300-\U0001FAFF☀-➿]')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)

async def page(b, url, **kw):
    ctx = await b.new_context(**kw); pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: asyncio.ensure_future(d.dismiss()))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(3500)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove()")
    return ctx, pg, errs

async def menu_items(pg):
    return await pg.evaluate("[...document.querySelectorAll('#bp-addm button .nm')].map(e=>e.textContent)")

async def tap_add(pg):
    await pg.evaluate("document.getElementById('bp-dock-add').click()"); await pg.wait_for_timeout(300)

async def pick(pg, label):
    await pg.locator('#bp-addm button', has_text=label).first.click(); await pg.wait_for_timeout(600)

async def sel_text(pg, id):
    return await pg.evaluate("()=>{var s=document.getElementById('%s');return s?(s.options[s.selectedIndex]||{}).text:null}" % id)

async def field(b, theme):
    name = 'iPhone ' + theme; print('\n' + name)
    ctx, pg, errs = await page(b, 'index.html', viewport={'width':390,'height':844})
    ok(await pg.evaluate("APP_VERSION") == '6.9.29', name + ': on v6.9.29')
    await pg.evaluate(SEED)
    await pg.evaluate("()=>{document.documentElement.setAttribute('data-theme','%s');bpSetActiveJob('jA',true);showScreen('s-home')}" % theme)
    await pg.wait_for_timeout(700)
    ok(not await pg.evaluate("document.getElementById('bp-dock-add').hidden"), name + ': + shows on Home')
    await tap_add(pg)
    items = await menu_items(pg)
    ok(items == ['Expense','Pay a sub','Change order','Punch item','Photo','Invoice'], name + ': menu lists the six choices %s' % items)
    hd = await pg.inner_text('#bp-addm .hd')
    ok('N. Peach Street Full Gut Renovation' in hd, name + ': menu names the On Site job')
    ok(not EMOJI.search(await pg.inner_text('#bp-addm')), name + ': no emoji in the menu')
    ok(await pg.evaluate("document.querySelectorAll('#bp-addm svg').length") >= 6, name + ': line icons on every choice')
    sz = await pg.evaluate("[...document.querySelectorAll('#bp-dock button')].filter(b=>!b.hidden).map(b=>{var r=b.getBoundingClientRect();return Math.round(r.width)+'x'+Math.round(r.height)})")
    ok(len(set(sz)) == 1 and sz[0] in ('48x48','42x42'), name + ': dock buttons stay round and even while open %s' % sz)
    ok(await pg.evaluate("getComputedStyle(document.getElementById('bp-dock')).opacity") == '1', name + ': dock stays up while the menu is open')
    # Expense
    await pick(pg, 'Expense')
    ok(await pg.evaluate("!!document.querySelector('#sheet-add-expense.open, .sheet-overlay.open #sheet-add-expense') || (document.getElementById('sheet-add-expense')||{}).classList.contains('open')") or await sel_text(pg, 'exp-job') is not None, name + ': Expense opens the expense form')
    ok(await sel_text(pg, 'exp-job') == 'N. Peach Street Full Gut Renovation', name + ': expense form has the On Site job')
    ok(not await pg.evaluate("!!document.getElementById('bp-addm')"), name + ': menu closes after a pick')
    await pg.evaluate("()=>{document.querySelectorAll('.sheet-overlay.open').forEach(o=>o.classList.remove('open'));['co-modal','log-payment-modal'].forEach(i=>{var e=document.getElementById(i);if(e)e.remove()});showScreen('s-home')}"); await pg.wait_for_timeout(400)
    # Pay a sub
    await tap_add(pg); await pick(pg, 'Pay a sub')
    t = await pg.inner_text('#bp-addm')
    ok('Ace Plumbing' in t and 'Bright Electric' in t and 'Oak Tile Co' not in t, name + ': Pay a sub lists only this job\'s subs')
    ok('$7,500.00 left' in t and '$9,800.75 left' in t, name + ': shows what each sub is still owed, to the penny')
    await pick(pg, 'Ace Plumbing')
    ok('Ace Plumbing' in (await pg.evaluate("(document.getElementById('log-payment-modal')||{}).innerText||''")), name + ': tapping a sub opens Log Payment for that sub')
    await pg.evaluate("document.getElementById('log-payment-modal') && document.getElementById('log-payment-modal').remove()")
    # Back arrow inside Pay a sub
    await pg.evaluate("showScreen('s-home')"); await pg.wait_for_timeout(300)
    await tap_add(pg); await pick(pg, 'Pay a sub'); await pick(pg, 'Pay a sub')
    ok(len(await menu_items(pg)) == 6, name + ': back arrow returns to the six choices')
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(200)
    ok(not await pg.evaluate("!!document.getElementById('bp-addm')"), name + ': Escape closes the menu')
    # Change order / Invoice / Punch
    await tap_add(pg); await pick(pg, 'Change order')
    ok(await sel_text(pg, 'co-job') == 'N. Peach Street Full Gut Renovation', name + ': change order form has the On Site job')
    await pg.evaluate("()=>{document.querySelectorAll('.sheet-overlay.open').forEach(o=>o.classList.remove('open'));['co-modal','log-payment-modal'].forEach(i=>{var e=document.getElementById(i);if(e)e.remove()});showScreen('s-home')}"); await pg.wait_for_timeout(400)
    await tap_add(pg); await pick(pg, 'Invoice')
    ok(await sel_text(pg, 'inv-job') == 'N. Peach Street Full Gut Renovation', name + ': invoice form has the On Site job')
    await pg.evaluate("()=>{document.querySelectorAll('.sheet-overlay.open').forEach(o=>o.classList.remove('open'));['co-modal','log-payment-modal'].forEach(i=>{var e=document.getElementById(i);if(e)e.remove()});showScreen('s-home')}"); await pg.wait_for_timeout(400)
    await tap_add(pg); await pick(pg, 'Punch item')
    ok(await pg.evaluate("document.querySelector('.screen.active').id") == 's-punch', name + ': Punch item goes to the punch list')
    await pg.evaluate("()=>{document.querySelectorAll('.sheet-overlay.open').forEach(o=>o.classList.remove('open'));['co-modal','log-payment-modal'].forEach(i=>{var e=document.getElementById(i);if(e)e.remove()})}")
    # Money overview gets the menu; Expenses tab keeps its own +
    await pg.evaluate("()=>{showScreen('s-finance');setFinanceTab('overview')}"); await pg.wait_for_timeout(700)
    ok(not await pg.evaluate("document.getElementById('bp-dock-add').hidden"), name + ': + shows on Money overview')
    await tap_add(pg)
    ok(len(await menu_items(pg)) == 6, name + ': + on Money overview opens the menu')
    await pg.keyboard.press('Escape')
    await pg.evaluate("setFinanceTab('expenses')"); await pg.wait_for_timeout(1400)
    await tap_add(pg)
    ok(not await pg.evaluate("!!document.getElementById('bp-addm')") and await sel_text(pg, 'exp-job') is not None, name + ': on the Expenses tab + still opens a new expense directly')
    await pg.evaluate("()=>{document.querySelectorAll('.sheet-overlay.open').forEach(o=>o.classList.remove('open'));['co-modal','log-payment-modal'].forEach(i=>{var e=document.getElementById(i);if(e)e.remove()})}")
    # No job On Site
    await pg.evaluate("()=>{bpSetActiveJob('',true);showScreen('s-home')}"); await pg.wait_for_timeout(700)
    await tap_add(pg)
    ok('Pick a job on the form' in await pg.inner_text('#bp-addm .hd'), name + ': with no job On Site the menu says to pick the job on the form')
    await pick(pg, 'Pay a sub')
    ok('Oak Tile Co' in await pg.inner_text('#bp-addm'), name + ': with no job On Site, Pay a sub lists every sub')
    await pg.keyboard.press('Escape')
    # Screen change closes it
    await pg.evaluate("showScreen('s-home')"); await pg.wait_for_timeout(300); await tap_add(pg)
    await pg.evaluate("showScreen('s-jobs')"); await pg.wait_for_timeout(300)
    ok(not await pg.evaluate("!!document.getElementById('bp-addm')"), name + ': changing screens closes the menu')
    ok(not errs, name + ': no page errors %s' % errs[:2])
    await ctx.close()

async def mac(b):
    name = 'Mac Command Center'; print('\n' + name)
    ctx, pg, errs = await page(b, 'desktop.html', viewport={'width':1440,'height':900})
    ok(await pg.evaluate("APP_VERSION") == '6.9.29', name + ': on v6.9.29')
    ok(not errs, name + ': no page errors %s' % errs[:2])
    await ctx.close()

async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT)], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        async with async_playwright() as p:
            exe = os.environ.get('CHROME')
            b = await p.chromium.launch(**({'executable_path': exe} if exe else {}), args=['--no-sandbox'])
            for th in ('dark', 'light'): await field(b, th)
            await mac(b)
            await b.close()
    finally:
        srv.terminate()
    v = subprocess.run(['bash', os.path.join(REPO, 'check_versions.sh')], capture_output=True, text=True, cwd=REPO)
    ok(v.returncode == 0, 'all three apps carry one version: ' + v.stdout.strip())
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
