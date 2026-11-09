"""v6.9.22 — Rentals: lease (dates, late fee, terms, file), utilities with account numbers (masked),
emergency contact, residents, rent statement for next month (from the 25th; text or email).
Run from repo root: python3 test_v6922_rentals_more.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, re
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8922
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};"
PDF = os.path.join('/tmp/claude-0/s', 'lease.pdf'); os.makedirs('/tmp/claude-0/s', exist_ok=True)
open(PDF, 'wb').write(b'%PDF-1.4\n' + b'%' + b'x'*400 + b'\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n')
SEED = """() => { var t = new Date().toISOString(), d = new Date(), k = d.getFullYear() + '-' + ('0'+(d.getMonth()+1)).slice(-2);
 DB.jobs = DB.jobs.filter(function(j){ return !j.rental; }); DB.rooms = DB.rooms.filter(function(r){ return !r.unit; });
 DB.jobs.push({ id:'rp1', name:'12 Peach St', address:'12 Peach St', city:'Bergenfield', state:'NJ', status:'Active', rental:true, created:t });
 DB.rooms.push({ id:'ru1', name:'Unit 2', jobId:'rp1', type:'Other', kind:'room', unit:true, created:t, tenant:{ name:'Anna Lee', phone:'2015550100', email:'anna@x.com', moveIn: k + '-01' }, rent:2100, dueDay:1, deposit:3150, rentPays:[{ id:'p1', month:k, amount:2100, date:k+'-01', method:'Zelle' }], inventory:[] });
 try { saveDB(); } catch(e){ try { save(); } catch(e2){} } }"""
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
    ok(await pg.evaluate("APP_VERSION") in ('6.9.22','6.9.23'), name + ': on v6.9.22+')
    await pg.evaluate(SEED); await pg.evaluate("bpRentOpen('ru1')"); await pg.wait_for_timeout(300)
    # tenant: residents + emergency
    await pg.click('#bp-rent [data-a="tenant"]'); await pg.wait_for_timeout(200)
    await pg.fill('.bp20-ov [data-f="residents"]', '3'); await pg.fill('.bp20-ov [data-f="ecName"]', 'mark lee')
    await pg.fill('.bp20-ov [data-f="ecRel"]', 'Brother'); await pg.fill('.bp20-ov [data-f="ecPhone"]', '201-555-0199')
    await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(300)
    u = await pg.evaluate("DB.rooms.find(function(r){ return r.id==='ru1'; })")
    ok(u['residents'] == 3 and u['tenant']['ecName'] == 'Mark Lee' and re.sub(r'\D', '', u['tenant']['ecPhone']) == '2015550199', name + ': residents + emergency contact saved ' + str([u.get('residents'), u['tenant']]))
    t = await pg.inner_text('#bp-rent')
    ok('3 residents' in t and 'Emergency: Mark Lee (Brother)' in t, name + ': shown on the tenant card')
    # lease
    await pg.click('#bp-rent .rt-h [data-a="lease"]'); await pg.wait_for_timeout(200)
    ok(await pg.input_value('.bp20-ov [data-f="start"]') == u['tenant']['moveIn'], name + ': lease start defaults to move-in')
    await pg.fill('.bp20-ov [data-f="end"]', '2027-02-28'); await pg.fill('.bp20-ov [data-f="lateFee"]', '50'); await pg.fill('.bp20-ov [data-f="grace"]', '5')
    await pg.fill('.bp20-ov [data-f="terms"]', 'No pets. Tenant shovels front walk.')
    await pg.set_input_files('.bp20-ov [data-f="file"]', PDF); await pg.wait_for_timeout(800)
    ok('Ready' in await pg.inner_text('.bp20-ov [data-f="filemsg"]'), name + ': lease file read')
    await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(300)
    L = await pg.evaluate("DB.rooms.find(function(r){ return r.id==='ru1'; }).lease")
    doc = await pg.evaluate("(DB.documents||[]).find(function(d){ return d.id === DB.rooms.find(function(r){ return r.id==='ru1'; }).lease.docId; })")
    ok(L['end'] == '2027-02-28' and L['lateFee'] == 50 and L['grace'] == 5 and 'No pets' in L['terms'], name + ': lease terms saved')
    ok(doc and doc['category'] == 'Lease' and doc['roomId'] == 'ru1' and doc['fileSrc'].startswith('data:'), name + ': lease file kept in Documents for the unit')
    t = await pg.inner_text('#bp-rent')
    ok('Signed lease' in t and 'Late fee $50.00 after 5 days' in t and 'Lease to 2/28/2027' in t, name + ': lease shown with terms and end date')
    # utilities
    await pg.click('#bp-rent [data-a="util"][data-k="electric"]'); await pg.wait_for_timeout(200)
    await pg.fill('.bp20-ov [data-f="provider"]', 'PSE&G'); await pg.fill('.bp20-ov [data-f="account"]', '6612 3345 9921')
    await pg.click('.bp20-ov [data-f="paidBy"] button[data-v="tenant"]'); await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(200)
    await pg.click('#bp-rent [data-a="util"][data-k="water"]'); await pg.wait_for_timeout(200)
    await pg.fill('.bp20-ov [data-f="provider"]', 'Veolia'); await pg.fill('.bp20-ov [data-f="account"]', '778812')
    await pg.click('.bp20-ov [data-f="paidBy"] button[data-v="me"]'); await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(200)
    ut = await pg.evaluate("DB.rooms.find(function(r){ return r.id==='ru1'; }).utilities")
    ok(ut['electric']['account'] == '6612 3345 9921' and ut['water']['paidBy'] == 'me', name + ': water/electric with account # and who pays')
    t = await pg.inner_text('#bp-rent')
    ok('Acct •••• 9921' in t and '6612 3345 9921' not in t and 'I pay' in t, name + ': account numbers masked on screen (last 4)')
    # statement
    await pg.evaluate("document.querySelector('#bp-rent .rt-body').scrollTop = 0")
    await pg.click('#bp-rent [data-a="stmt"]'); await pg.wait_for_timeout(200)
    await pg.fill('.bp20-ov [data-f="payInfo"]', 'Zelle to 201-555-0000'); await pg.dispatch_event('.bp20-ov [data-f="payInfo"]', 'input')
    pre = await pg.inner_text('.bp20-ov [data-f="preview"]')
    nxt = await pg.evaluate("(function(){ var d=new Date(); d=new Date(d.getFullYear(), d.getMonth()+1, 1); return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d.getMonth()] + ' ' + d.getFullYear(); })()")
    ok(('RENT STATEMENT — ' + nxt) in pre and 'Anna Lee' in pre and 'Total due by' in pre and '$2,100.00' in pre, name + ': statement is for next month (' + nxt + ')')
    ok('late fee of $50.00' in pre and 'Zelle to 201-555-0000' in pre and 'STM Pro Build' in pre, name + ': statement has late fee, how to pay, from')
    await pg.screenshot(path='/tmp/claude-0/s/rent-stmt-%s.png' % short)
    await pg.route('sms:*', lambda r: r.abort()); await pg.route('mailto:*', lambda r: r.abort())
    try: await pg.click('.bp20-ov [data-st="email"]', timeout=3000)
    except Exception: pass
    await pg.wait_for_timeout(300)
    sent = await pg.evaluate("DB.rooms.find(function(r){ return r.id==='ru1'; }).stmtSent")
    ok(sent and list(sent.values())[0]['how'] == 'email', name + ': marked sent by email')
    ok(await pg.evaluate("DB.jobs.find(function(j){ return j.id==='rp1'; }).payInfo") == 'Zelle to 201-555-0000', name + ': how-to-pay remembered on the property')
    # 25th banner: fake the date
    await pg.evaluate("var u = DB.rooms.find(function(r){ return r.id==='ru1'; }); u.stmtSent = {}; var _D = Date; window.Date = function(a,b,c,d,e,f,g){ if (arguments.length) return new (Function.prototype.bind.apply(_D, [null].concat([].slice.call(arguments)))); var x = new _D(); return new _D(x.getFullYear(), x.getMonth(), 26, 10); }; Date.prototype = _D.prototype; Date.now = _D.now; Date.UTC = _D.UTC; Date.parse = _D.parse; bpRentOpen()")
    await pg.wait_for_timeout(300)
    t = await pg.inner_text('#bp-rent')
    ok('statements ready' in t and '1 to send' in t, name + ': from the 25th, "statements ready" shows on Rentals')
    await pg.click('#bp-rent [data-a="stmts"]'); await pg.wait_for_timeout(200)
    ok(await pg.locator('.bp20-ov [data-st="text"]').count() == 1 and await pg.locator('.bp20-ov [data-st="email"]').count() == 1, name + ': each tenant has Text and Email')
    await pg.screenshot(path='/tmp/claude-0/s/rent-stmts-%s.png' % short)
    await pg.evaluate("document.querySelectorAll('.bp20-ov').forEach(function(o){ o.remove(); }); bpRentOpen('ru1'); document.querySelector('#bp-rent .rt-body').scrollTop = 0")
    await pg.wait_for_timeout(200)
    await pg.screenshot(path='/tmp/claude-0/s/rent-unit2-%s.png' % short, full_page=False)
    html = await pg.inner_html('#bp-rent')
    ok(not re.search('[\U0001F300-\U0001FAFF☀-➿]', html), name + ': no emoji')
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
