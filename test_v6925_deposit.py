"""v6.9.25 — Rentals security deposit: NJ 1.5x rent limit, bank/account/rate, 30-day bank notice + yearly notice,
move-out → deposit to return within 30 days with itemized deductions. iPhone + Mac.
Run from repo root: python3 test_v6925_deposit.py      Exit 0 = all pass."""
import subprocess, time, asyncio, sys, os, re
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.abspath(__file__)); PORT = 8925
BLOCK = ('open-meteo','nominatim','bigdatacloud','ipapi','ipwho','api.github','apple-cloudkit','googleapis','gstatic')
SHELL = "window.BPShell={version:'t',caps:{ai:true}};window.webkit={messageHandlers:{bp:{postMessage:function(){}}}};"
SEED = """() => { var t = new Date().toISOString(), d = new Date(), k = d.getFullYear() + '-' + ('0'+(d.getMonth()+1)).slice(-2);
 var old = new Date(Date.now() - 40*864e5).toISOString().slice(0,10);
 DB.jobs = DB.jobs.filter(function(j){ return !j.rental; }); DB.rooms = DB.rooms.filter(function(r){ return !r.unit; });
 DB.jobs.push({ id:'rp1', name:'12 Peach St', address:'12 Peach St', status:'Active', rental:true, created:t });
 DB.rooms.push({ id:'ru1', name:'Unit 2', jobId:'rp1', type:'Other', kind:'room', unit:true, created:t, tenant:{ name:'Anna Lee', phone:'2015550100', email:'anna@x.com', moveIn: old }, rent:2000, dueDay:1, deposit:'', rentPays:[{ id:'p1', month:k, amount:2000, date:k+'-01', method:'Zelle' }], inventory:[] });
 window.__old = old; }"""
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
    await pg.route('sms:*', lambda r: r.abort()); await pg.route('mailto:*', lambda r: r.abort())
    await pg.goto('http://localhost:%d/%s' % (PORT, url)); await pg.wait_for_timeout(4000)
    ok(await pg.evaluate("APP_VERSION") == '6.9.25', name + ': on v6.9.25')
    await pg.evaluate(SEED); await pg.evaluate("bpRentOpen('ru1')"); await pg.wait_for_timeout(300)
    t = await pg.inner_text('#bp-rent')
    ok('No deposit recorded. NJ max is 1.5× rent = $3,000.00' in t, name + ': empty deposit shows NJ max')
    # over limit warning in sheet
    await pg.click('#bp-rent .rt-h [data-a="dep"]'); await pg.wait_for_timeout(200)
    ok(await pg.input_value('.bp20-ov [data-f="received"]') == await pg.evaluate("__old"), name + ': received date defaults to move-in')
    await pg.fill('.bp20-ov [data-f="amount"]', '3500'); await pg.dispatch_event('.bp20-ov [data-f="amount"]', 'input')
    ok('Over the NJ limit' in await pg.inner_text('.bp20-ov [data-f="limitmsg"]'), name + ': warns over 1.5× rent')
    await pg.fill('.bp20-ov [data-f="amount"]', '3000'); await pg.dispatch_event('.bp20-ov [data-f="amount"]', 'input')
    ok(await pg.inner_text('.bp20-ov [data-f="limitmsg"]') == '', name + ': 1.5× rent exactly is fine')
    await pg.fill('.bp20-ov [data-f="bank"]', 'TD Bank'); await pg.fill('.bp20-ov [data-f="bankAddr"]', '1 Main St, Bergenfield, NJ')
    await pg.fill('.bp20-ov [data-f="acct"]', '44120099871'); await pg.fill('.bp20-ov [data-f="rate"]', '0.5')
    await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(300)
    u = await pg.evaluate("DB.rooms.find(function(r){ return r.id==='ru1'; })")
    ok(u['deposit'] == 3000 and u['dep']['bank'] == 'TD Bank' and u['dep']['acct'] == '44120099871', name + ': deposit, bank, account saved')
    t = await pg.inner_text('#bp-rent')
    ok('$3,000.00' in t and 'Acct •••• 9871' in t and '44120099871' not in t, name + ': account masked on screen')
    ok('Bank notice overdue' in t, name + ': received 40 days ago, no notice → overdue (red)')
    ok('Deposit' in await pg.evaluate("(function(){ bpRentOpen(); return document.getElementById('bp-rent').innerText; })()"), name + ': unit flagged on the Rentals list')
    await pg.evaluate("bpRentOpen('ru1')"); await pg.wait_for_timeout(200)
    # notice
    await pg.click('#bp-rent .rt-h [data-a="depnotice"]'); await pg.wait_for_timeout(200)
    pre = await pg.inner_text('.bp20-ov pre')
    ok('SECURITY DEPOSIT NOTICE' in pre and 'TD Bank, 1 Main St, Bergenfield, NJ' in pre and '44120099871' in pre and '0.5%' in pre and '$3,000.00' in pre, name + ': notice has bank, address, account, rate, amount')
    await pg.screenshot(path='/tmp/claude-0/s/dep-notice-%s.png' % short)
    try: await pg.click('.bp20-ov [data-sd="email"]', timeout=3000)
    except Exception: pass
    await pg.wait_for_timeout(300)
    n = await pg.evaluate("DB.rooms.find(function(r){ return r.id==='ru1'; }).dep.notices")
    ok(len(n) == 1 and n[0]['how'] == 'email' and n[0]['kind'] == 'bank notice', name + ': notice logged')
    t = await pg.inner_text('#bp-rent')
    ok('Notice sent' in t and 'overdue' not in t, name + ': now green "Notice sent"')
    await pg.evaluate("document.querySelector('#bp-rent .rt-body').scrollTop = 0")
    await pg.screenshot(path='/tmp/claude-0/s/dep-unit-%s.png' % short)
    # yearly notice due after a year
    await pg.evaluate("var u = DB.rooms.find(function(r){ return r.id==='ru1'; }); u.dep.notices[0].date = '2025-01-01'; bpRentOpen('ru1')"); await pg.wait_for_timeout(200)
    ok('Yearly interest notice due' in await pg.inner_text('#bp-rent'), name + ': yearly notice due after 12 months')
    # move out → return
    await pg.click('#bp-rent [data-a="tenant"]'); await pg.wait_for_timeout(200)
    await pg.click('.bp20-ov .bp20-rm'); await pg.wait_for_timeout(300)
    u = await pg.evaluate("DB.rooms.find(function(r){ return r.id==='ru1'; })")
    ok(len(u['depReturns']) == 1 and u['depReturns'][0]['amount'] == 3000 and u['depReturns'][0]['tenant'] == 'Anna Lee' and not u['deposit'], name + ': move-out creates a deposit to return')
    t = await pg.inner_text('#bp-rent')
    ok('Return deposit · Anna Lee' in t and 'Due by' in t, name + ': return shows with 30-day due date')
    await pg.click('#bp-rent [data-a="depret"]'); await pg.wait_for_timeout(200)
    await pg.fill('.bp20-ov [data-f="forward"]', '9 Elm St, Teaneck NJ'); await pg.dispatch_event('.bp20-ov [data-f="forward"]', 'change')
    await pg.fill('.bp20-ov [data-f="interest"]', '12.40'); await pg.dispatch_event('.bp20-ov [data-f="interest"]', 'change')
    await pg.fill('.bp20-ov [data-f="ddesc"]', 'Broken bedroom door'); await pg.fill('.bp20-ov [data-f="damt"]', '250')
    await pg.click('.bp20-ov [data-dadd]'); await pg.wait_for_timeout(200)
    ok('Refund $2,762.40' in await pg.inner_text('.bp20-ov'), name + ': refund = deposit + interest − deductions')
    txt = await pg.evaluate("bpDepReturnText(DB.rooms.find(function(r){ return r.id==='ru1'; }), DB.rooms.find(function(r){ return r.id==='ru1'; }).depReturns[0])")
    ok('Broken bedroom door: $250.00' in txt and 'Refund to you: $2,762.40' in txt and '9 Elm St' in txt, name + ': itemized list text')
    await pg.screenshot(path='/tmp/claude-0/s/dep-return-%s.png' % short)
    await pg.click('.bp20-ov .bp20-go'); await pg.wait_for_timeout(300)
    r = await pg.evaluate("DB.rooms.find(function(r){ return r.id==='ru1'; }).depReturns[0]")
    ok(r['returned'] and r['returned']['refund'] == 2762.4, name + ': marked returned')
    ok('Return deposit' not in await pg.inner_text('#bp-rent'), name + ': return card gone')
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
