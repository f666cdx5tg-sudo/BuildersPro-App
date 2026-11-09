"""v6.9.20 — Verbal contract on the job card (Stan chose: verbal = done / green on any job).
Add on "Signed contract" → Signed or Verbal; Verbal records date / amount / with / how / scope; row turns
green "Contract (verbal)"; Start no longer asks; tap the row to change or remove; signed copy still takes over;
optional text confirmation. iPhone field app + Mac Command Center.
Run from repo root: python3 test_v6920_verbal_contract.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8920
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};"
SEED = """() => { var t = new Date().toISOString();
 DB.jobs = [{ id:'j1', name:'Shedwick', client:'Anna Lee', address:'12 Peach St', clientEmail:'a@x.com', clientPhone:'2015550100', contractValue:12500, status:'Active', updatedAt:t }];
 DB.documents = []; DB.contacts = DB.contacts || [];
 try { saveDB(); } catch(e){ try { save(); } catch(e2){} } }"""
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def run(b, name, url, **kw):
    print('\n' + name); mac = 'desktop' in url
    ctx = await b.new_context(**kw); await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    dlg = []; pg.on('dialog', lambda d: (dlg.append(d.message), asyncio.ensure_future(d.accept())))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(4000)
    ok(tuple(map(int, (await pg.evaluate("APP_VERSION")).split('.'))) >= (6, 9, 20), name + ': on v6.9.20 or newer')
    await pg.evaluate(SEED)
    rows = await pg.evaluate("bspChecklist('j1').map(function(r){ return [r.label, r.done]; })")
    ok(['Signed contract', False] in rows, name + ': no contract yet = open (red)')
    await pg.evaluate("bspAddSignedContract('j1')"); await pg.wait_for_timeout(300)
    ok(await pg.locator('.bp20-ov [data-k="signed"]').count() == 1 and await pg.locator('.bp20-ov [data-k="verbal"]').count() == 1, name + ': Add asks Signed or Verbal')
    await pg.click('.bp20-ov [data-k="verbal"]'); await pg.wait_for_timeout(300)
    ok(await pg.input_value('.bp20-ov [data-f="amount"]') == '12500.00', name + ': amount starts at the job contract value')
    ok(await pg.input_value('.bp20-ov [data-f="with"]') == 'Anna Lee', name + ': with = the client')
    await pg.click('.bp20-ov [data-f="how"] button[data-v="phone"]')
    await pg.fill('.bp20-ov [data-f="scope"]', 'Full bath gut and rebuild')
    await pg.screenshot(path='/tmp/claude-0/s/verbal-%s.png' % name.split()[0])
    await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(400)
    v = await pg.evaluate("DB.jobs[0].verbalContract")
    ok(v and v['amount'] == 12500 and v['how'] == 'phone' and v['scope'] == 'Full bath gut and rebuild', name + ': verbal agreement saved ' + str(v and {k: v[k] for k in ('amount', 'how', 'with')}))
    rows = await pg.evaluate("bspChecklist('j1').map(function(r){ return [r.label, r.done, r.value]; })")
    vr = [r for r in rows if r[0] == 'Contract (verbal)']
    ok(vr and vr[0][1] is True and '$12,500.00' in vr[0][2], name + ': row is green "Contract (verbal)" ' + str(vr))
    await pg.evaluate("DB.jobs[0].startDate = ''; try { toggleJobStarted('j1') } catch(e){}"); await pg.wait_for_timeout(300)
    ok(not any('no signed contract' in d for d in dlg), name + ': starting the job no longer asks about a contract')
    # signed copy takes over
    await pg.evaluate("DB.documents.push({ id:'d1', jobId:'j1', name:'Signed contract', category:'Contract', fileSrc:'data:image/png;base64,AA', created:new Date().toISOString() })")
    rows = await pg.evaluate("bspChecklist('j1').map(function(r){ return [r.label, r.done]; })")
    ok(['Signed contract', True] in rows, name + ': a signed copy filed later takes over')
    await pg.evaluate("DB.documents = []")
    # text confirmation
    await pg.evaluate("bspVerbalContract('j1')"); await pg.wait_for_timeout(300)
    ok(await pg.locator('.bp20-ov .bp20-tx').count() == 1, name + ': offers Save & text confirmation')
    await pg.evaluate("window.__nav = []; var _h = Object.getOwnPropertyDescriptor(Location.prototype, 'href');")
    await pg.route('sms:*', lambda r: r.abort())
    try:
        await pg.click('.bp20-ov .bp20-tx', timeout=3000)
    except Exception: pass
    await pg.wait_for_timeout(300)
    txt = await pg.evaluate("window.__bpLastVerbalText || ''")
    ok('Price: $12,500.00' in txt and 'Full bath gut' in txt and 'reply YES' in txt, name + ': confirmation text has price, scope, ask to confirm')
    # remove
    await pg.evaluate("document.querySelectorAll('.bp20-ov').forEach(function(o){ o.remove(); }); bspVerbalContract('j1')"); await pg.wait_for_timeout(300)
    await pg.click('.bp20-ov .bp20-rm'); await pg.wait_for_timeout(300)
    ok(not await pg.evaluate("!!DB.jobs[0].verbalContract"), name + ': remove takes it off')
    ok(not errs, name + ': no script errors ' + str(errs[:2]))
    await ctx.close()
async def main():
    srv = subprocess.Popen(['python3','-m','http.server',str(PORT),'--directory',REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            await run(b, 'iPhone field app', 'index.html', viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
            await run(b, 'Mac Command Center', 'desktop.html', viewport={'width': 1440, 'height': 900})
            await b.close()
    finally:
        srv.terminate()
    print('\n%d checks, %d failed' % (checks, len(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
