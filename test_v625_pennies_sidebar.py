"""v6.2.5 — totals to the penny everywhere (field app + Mac), and the Mac side menu scrolls to the bottom.
Seeds money with cents, opens every money screen, and reads every dollar figure on screen:
no figure may be rounded to the dollar, show one decimal ($12.3), or float junk ($0.30000000004).
Run from repo root: python3 test_v625_pennies_sidebar.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, re
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8904
BLOCK = ('open-meteo', 'nominatim', 'bigdatacloud', 'ipapi', 'ipwho', 'api.github', 'apple-cloudkit', 'googleapis', 'gstatic')
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)

SEED = """() => {
  var t = new Date().toISOString(), d = t.slice(0, 10);
  DB.jobs = [{ id:'j1', name:'N. Peach St', client:'Shelden', address:'1536 N. Peach St', clientEmail:'a@b.c', clientPhone:'2015550123', contract:45000, status:'Active', startDate:'2026-08-19', updatedAt:t }];
  DB.rooms = [{ id:'r1', jobId:'j1', name:'Kitchen', type:'Kitchen', contractValue:1500.75, updatedAt:t }];
  DB.punchlist = [{ id:'p1', jobId:'j1', roomId:'r1', text:'Vent', value:10.25, done:false, updatedAt:t }];
  DB.payments = [{ id:'pay1', jobId:'j1', amount:856.47, date:d, method:'Check', updatedAt:t }];
  DB.invoices = [{ id:'i1', jobId:'j1', desc:'Deposit', amount:1000.05, status:'Paid', date:d, updatedAt:t }];
  DB.expenses = [{ id:'e1', jobId:'j1', desc:'PEX', amount:12.3, category:'Materials', date:d, updatedAt:t }, { id:'e2', jobId:'j1', desc:'Fittings', amount:0.1, category:'Materials', date:d, updatedAt:t }, { id:'e3', jobId:'j1', desc:'Tape', amount:0.2, category:'Materials', date:d, updatedAt:t }];
  DB.contractors = [{ id:'c1', jobId:'j1', name:'Ever', trade:'Plumbing', value:2500.5, updatedAt:t }];
  DB.permits = [{ id:'pm1', jobId:'j1', trade:'Plumbing', status:'Applied', cost:99.99, updatedAt:t }];
  try { bpSave(); } catch(e){ try { saveDB(); } catch(e2){} }
  try { renderAll(); } catch(e){}
}"""
SCAN = """() => {
  var out = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), n;
  while ((n = w.nextNode())) {
    var p = n.parentElement; if (!p || p.closest('script,style,option')) continue;
    if (!p.offsetParent && getComputedStyle(p).position !== 'fixed') continue;
    var m = n.nodeValue.match(/[-−]?\\$\\s?[\\d,]+(\\.\\d+)?/g); if (m) out = out.concat(m);
  }
  return out;
}"""
CENTS = ['856.47', '1,000.05', '12.30', '2,500.50', '99.99', '10.25', '1,500.75', '44,143.53', '0.30', '12.60']

def bad(amounts):
    out = []
    for a in amounts:
        m = re.search(r'\.(\d+)$', a)
        if m and len(m.group(1)) != 2: out.append(a)          # $12.3 or $0.300000004
    for whole, cents in (('856', '856.47'), ('44,144', '44,143.53'), ('2,501', '2,500.50'), ('100', '99.99'), ('1,501', '1,500.75'), ('1,000', '1,000.05')):
        out += [a for a in amounts if re.search(r'\$\s?' + re.escape(whole) + r'$', a) and whole != '1,000']
    return out

async def run(b, name, page, vp, steps):
    print('\n' + name)
    ctx = await b.new_context(viewport=vp, has_touch=page == 'index.html', is_mobile=(name == 'iPhone'))
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: asyncio.ensure_future(d.dismiss()))
    await pg.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, page)); await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('bp-lock') && document.getElementById('bp-lock').remove(); window.bpICloudSync = undefined;")
    ok(tuple(map(int, (await pg.evaluate("APP_VERSION")).split('.'))) >= (6, 2, 5), name + ': on v6.2.5 or newer')
    await pg.evaluate(SEED); await pg.wait_for_timeout(400)
    seen = []
    for label, js in steps:
        try: await pg.evaluate(js); await pg.wait_for_timeout(500)
        except Exception as e: ok(False, '%s: could not open %s (%s)' % (name, label, str(e)[:70])); continue
        am = await pg.evaluate(SCAN); seen += am
        b_ = bad(am)
        ok(not b_, '%s — %s: every dollar figure to the penny %s' % (name, label, b_[:5]))
        if os.environ.get('SHOW'): print('     ', label, sorted(set(am)))
    joined = ' '.join(seen)
    for c in ('1,000.05', '12.60', '2,500.50'):
        ok(c in joined, '%s: $%s shows somewhere' % (name, c))
    if page == 'desktop.html':
        await pg.evaluate("showView('dashboard')"); await pg.wait_for_timeout(300)
        for vh in (900, 640):
            await pg.set_viewport_size({'width': 1440, 'height': vh}); await pg.wait_for_timeout(400)
            await pg.evaluate("document.querySelector('aside.sidebar').scrollTop = 99999"); await pg.wait_for_timeout(200)
            r = await pg.evaluate("""() => { var s = document.querySelector('aside.sidebar'), items = s.querySelectorAll('button.ni'), last = items[items.length - 1].getBoundingClientRect();
              return { lastBottom: Math.round(last.bottom), winH: innerHeight, sideBottom: Math.round(s.getBoundingClientRect().bottom), text: items[items.length - 1].textContent.trim() }; }""")
            ok(r['lastBottom'] <= r['winH'] and r['sideBottom'] <= r['winH'] + 1, 'Mac (%dpx tall window): side menu scrolls down to "%s", fully on screen %s' % (vh, r['text'], r))
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()

FIELD = [('Home', "showScreen('s-home')"), ('Jobs', "showScreen('s-jobs')"), ('Job page', "openJobDetail('j1')"),
         ('Job page money', "openJobDetail('j1'); try{ bpJobAccToggle('finance'); }catch(e){}"),
         ('Space page', "openRoomDetail('r1')"), ('Spaces', "closeRoomDetail(); showScreen('s-rooms')"),
         ('Money', "showScreen('s-finance')")] + [('Money: ' + t, "showScreen('s-finance'); try{ setFinanceTab('%s'); }catch(e){}" % t) for t in ('overview', 'invoices', 'expenses', 'contractors', 'permits', 'payments', 'budget')]
MAC = [('Home', "showView('dashboard')"), ('Jobs', "showView('jobs')"), ('Job page', "openJobDetail('j1')"), ('Money', "showView('finance')"),
       ('Space', "openRoomDetail('r1')")]

async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await run(b, 'iPhone', 'index.html', {'width': 390, 'height': 844}, FIELD)
            await run(b, 'Mac', 'desktop.html', {'width': 1440, 'height': 900}, MAC)
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failures' % (checks, len(fails)))
    for f in fails: print('  - ' + f)
    sys.exit(1 if fails else 0)
asyncio.run(main())
