"""v6.9.21 — Rentals: property (rental job) → units (spaces) with tenant, move-in, rent ledger,
repairs (punch items in the unit) incl. "Repair from text" matching by cell/name, and an inventory of
appliances, windows, built-ins. iPhone field app + Mac Command Center.
Run from repo root: python3 test_v6921_rentals.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8921
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};"
os.makedirs('/tmp/claude-0/s', exist_ok=True)
fails = []; checks = 0
def ok(c, m):
    global checks; checks += 1
    print(('  PASS ' if c else '  FAIL ') + m)
    if not c: fails.append(m)
async def run(b, name, url, **kw):
    print('\n' + name); short = name.split()[0]
    ctx = await b.new_context(**kw); await ctx.add_init_script(SHELL)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    await pg.route('**/*', lambda r: r.abort() if any(x in r.request.url for x in BLOCK) else r.continue_())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(4000)
    ok(await pg.evaluate("APP_VERSION") >= '6.9.21', name + ': on v6.9.21+')
    await pg.evaluate("DB.jobs = DB.jobs.filter(function(j){ return !j.rental; })")
    ok(await pg.locator('#nav-rentals').count() == 1, name + ': Rentals in the menu')
    await pg.evaluate("bpRentOpen()"); await pg.wait_for_timeout(300)
    ok('No rentals yet' in await pg.inner_text('#bp-rent'), name + ': empty state')
    # property
    await pg.click('#bp-rent [data-a="prop"]'); await pg.wait_for_timeout(200)
    await pg.fill('.bp20-ov [data-f="name"]', '12 peach st'); await pg.fill('.bp20-ov [data-f="city"]', 'bergenfield')
    await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(300)
    p = await pg.evaluate("DB.jobs.filter(function(j){ return j.rental; })")
    ok(len(p) == 1 and p[0]['name'] == '12 Peach St', name + ': property saved as a rental job')
    # unit sheet opens automatically
    ok(await pg.input_value('.bp20-ov [data-f="name"]') == 'Unit 1', name + ': unit sheet opens, named Unit 1')
    await pg.fill('.bp20-ov [data-f="name"]', 'Unit 2'); await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(300)
    # tenant sheet opens
    await pg.fill('.bp20-ov [data-f="name"]', 'anna lee'); await pg.fill('.bp20-ov [data-f="phone"]', '(201) 555-0100')
    await pg.fill('.bp20-ov [data-f="moveIn"]', '2026-03-01'); await pg.fill('.bp20-ov [data-f="rent"]', '2100')
    await pg.fill('.bp20-ov [data-f="dueDay"]', '1'); await pg.fill('.bp20-ov [data-f="deposit"]', '3150')
    await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(300)
    u = await pg.evaluate("DB.rooms.find(function(r){ return r.unit; })")
    ok(u['tenant']['name'] == 'Anna Lee' and u['tenant']['moveIn'] == '2026-03-01' and u['rent'] == 2100 and u['deposit'] == 3150, name + ': tenant, move-in, rent, deposit saved')
    ok(u['jobId'] == p[0]['id'], name + ': unit is a space of the property')
    t = await pg.inner_text('#bp-rent')
    ok('Anna Lee' in t and 'Moved in 3/1/2026' in t and '$2,100.00/mo' in t, name + ': unit page shows tenant, move-in, rent')
    ok('Late' in t, name + ': unpaid months since move-in show as late (red)')
    # pay all months through this month
    await pg.evaluate("""() => { var u = DB.rooms.find(function(r){ return r.unit; }); var d = new Date(2026, 2, 1), now = new Date();
      while (d <= now) { u.rentPays.push({ id: 'p' + d.getMonth(), month: d.getFullYear() + '-' + ('0' + (d.getMonth()+1)).slice(-2), amount: 2100, date: '2026-01-01', method: 'Zelle' }); d = new Date(d.getFullYear(), d.getMonth()+1, 1); } }""")
    await pg.evaluate("bpRentOpen(DB.rooms.find(function(r){ return r.unit; }).id)"); await pg.wait_for_timeout(200)
    t = await pg.inner_text('#bp-rent')
    ok('Paid ' in t and 'Late' not in t, name + ': all paid → green Paid')
    # remove this month's payment via the sheet, then log it through the UI
    cur = await pg.evaluate("(function(){ var d=new Date(); return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2); })()")
    await pg.evaluate("var u = DB.rooms.find(function(r){ return r.unit; }); u.rentPays = u.rentPays.filter(function(x){ return x.month !== '%s'; }); bpRentOpen(u.id)" % cur)
    await pg.wait_for_timeout(200)
    ok('Late' in await pg.inner_text('#bp-rent'), name + ': this month unpaid after due day = late')
    await pg.click('#bp-rent [data-a="pay"]'); await pg.wait_for_timeout(200)
    ok(await pg.input_value('.bp20-ov [data-f="month"]') == cur and await pg.input_value('.bp20-ov [data-f="amount"]') == '2100.00', name + ': Log payment picks the unpaid month and full rent')
    await pg.click('.bp20-ov [data-f="method"] button[data-v="Check"]'); await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(300)
    last = await pg.evaluate("DB.rooms.find(function(r){ return r.unit; }).rentPays.slice(-1)[0]")
    ok(last['month'] == cur and last['amount'] == 2100 and last['method'] == 'Check', name + ': payment logged ' + str(last['method']))
    ok('Late' not in await pg.inner_text('#bp-rent'), name + ': back to paid')
    # repair typed
    await pg.click('#bp-rent [data-a="repair"]'); await pg.wait_for_timeout(200)
    await pg.fill('.bp20-ov [data-f="title"]', 'smoke detector chirping'); await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(300)
    r = await pg.evaluate("DB.punchlist.filter(function(p){ return p.repair; })")
    ok(len(r) == 1 and r[0]['text'] == 'Smoke detector chirping' and r[0]['roomId'] == u['id'] and r[0]['jobId'] == p[0]['id'] and not r[0]['done'], name + ': repair is an open punch item in the unit')
    # repair from text — matched by cell number, from the main list
    await pg.click('#bp-rent [data-a="back"]'); await pg.wait_for_timeout(200)
    await pg.click('#bp-rent [data-a="fromtext"]'); await pg.wait_for_timeout(200)
    await pg.fill('.bp20-ov [data-f="msg"]', 'Hi Stan, the kitchen sink is leaking under the cabinet. Can someone come Tuesday? - 201.555.0100')
    await pg.dispatch_event('.bp20-ov [data-f="msg"]', 'input'); await pg.wait_for_timeout(200)
    ok(await pg.input_value('.bp20-ov [data-f="unit"]') == u['id'], name + ': text matched to Anna by cell number')
    ttl = await pg.input_value('.bp20-ov [data-f="title"]')
    ok(ttl == 'The kitchen sink is leaking under the cabinet', name + ': repair title pulled from the text: ' + ttl)
    await pg.screenshot(path='/tmp/claude-0/s/rent-text-%s.png' % short)
    await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(300)
    r = await pg.evaluate("DB.punchlist.filter(function(p){ return p.repair; })")
    ok(len(r) == 2 and 'Tenant text' in r[-1]['extraNotes'] and r[-1]['reportedBy'] == 'Anna Lee', name + ': repair from text saved with the original message')
    ok(await pg.evaluate("bpRentMatchUnit('this is anna, toilet running')") is not None, name + ': matches by first name too')
    # inventory
    for k, nm in (('appliance', 'Water heater'), ('window', 'Bedroom 1 — left'), ('builtin', 'Kitchen cabinets')):
        await pg.click('#bp-rent .rt-h [data-a="inv"][data-k="%s"]' % k); await pg.wait_for_timeout(200)
        await pg.fill('.bp20-ov [data-f="name"]', nm); await pg.fill('.bp20-ov [data-f="brand"]', 'Brand')
        await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(200)
    inv = await pg.evaluate("DB.rooms.find(function(r){ return r.unit; }).inventory.map(function(x){ return x.kind + ':' + x.name; })")
    ok(inv == ['appliance:Water heater', 'window:Bedroom 1 — left', 'builtin:Kitchen cabinets'], name + ': appliances, windows, built-ins listed ' + str(inv))
    t = await pg.inner_text('#bp-rent')
    ok('APPLIANCES · 1' in t.upper() and 'WINDOWS · 1' in t.upper() and 'BUILT-INS · 1' in t.upper(), name + ': inventory groups show counts')
    await pg.evaluate("document.querySelector('#bp-rent .rt-body').scrollTop = 0")
    await pg.screenshot(path='/tmp/claude-0/s/rent-unit-%s.png' % short)
    # toggle repair done
    await pg.click('#bp-rent [data-a="toggle"] >> nth=0'); await pg.wait_for_timeout(200)
    ok(await pg.evaluate("DB.punchlist.filter(function(p){ return p.repair && p.done; }).length") == 1, name + ': tap a repair to mark it done')
    # list view summary
    await pg.click('#bp-rent [data-a="back"]'); await pg.wait_for_timeout(200)
    t = await pg.inner_text('#bp-rent')
    ok('$2,100.00' in t and 'Unit 2 · Anna Lee' in t and '1 repair' in t, name + ': list shows unit, tenant, rent, open repairs')
    await pg.screenshot(path='/tmp/claude-0/s/rent-list-%s.png' % short)
    # emoji check on the screen
    html = await pg.inner_html('#bp-rent')
    import re
    ok(not re.search('[\U0001F300-\U0001FAFF☀-➿]', html), name + ': no emoji')
    # move out keeps history
    await pg.evaluate("bpRentOpen(DB.rooms.find(function(r){ return r.unit; }).id)"); await pg.wait_for_timeout(200)
    await pg.click('#bp-rent [data-a="tenant"]'); await pg.wait_for_timeout(200)
    await pg.click('.bp20-ov .bp20-rm'); await pg.wait_for_timeout(300)
    u2 = await pg.evaluate("DB.rooms.find(function(r){ return r.unit; })")
    ok(not u2['tenant'].get('name') and len(u2['pastTenants']) == 1 and u2['pastTenants'][0]['tenant']['name'] == 'Anna Lee', name + ': move out → vacant, history kept')
    await pg.evaluate("bpRentClose()")
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
